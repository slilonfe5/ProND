from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from .models import Profile, Skill, SessionRequest
from .forms import ProfileForm, SkillForm, SessionRequestForm
from django.db.models import Q, Max
from django.contrib.auth.models import User
from .models import Profile, Skill, PrivateMessage
from .forms import ProfileForm, SkillForm
from skillsessions.models import Session, SessionMembership
def login_page(request):
    if request.user.is_authenticated:
        return redirect('session_list')
    return render(request, "accounts/login.html")

def about_page(request):
    return render(request, 'accounts/about.html')

@login_required
def profile_view(request): # view own profile - get profile info + Skills
    profile, created = Profile.objects.get_or_create(user=request.user)
    skills = Skill.objects.filter(owner=request.user)
    return render(request, 'accounts/profile_view.html', {
        'profile': profile,
        'skills': skills,
    })


@login_required
def profile_edit(request):  # edit own profile - update bio, add/remove skills
    profile, created = Profile.objects.get_or_create(user=request.user)
    skills = Skill.objects.filter(owner=request.user)
    profile_form = ProfileForm(instance=profile)
    skill_form = SkillForm()

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'save_bio':
            profile_form = ProfileForm(request.POST, request.FILES, instance=profile)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, 'Profile updated.')
                return redirect('profile_edit')

        elif action == 'add_skill': # add skill - skill name + description, must be unique per user
            skill_form = SkillForm(request.POST)
            if skill_form.is_valid():
                name = skill_form.cleaned_data['name']
                if Skill.objects.filter(owner=request.user, name=name).exists(): 
                    messages.error(request, f'You already have a skill called "{name}".')
                else:
                    skill = skill_form.save(commit=False)
                    skill.owner = request.user
                    skill.save()
                    messages.success(request, f'Skill "{skill.name}" added.')
                return redirect('profile_edit')

        elif action == 'remove_skill': # remove skill - blocking if upcoming sessions exist for skill. change in future?
            skill_id = request.POST.get('skill_id')
            skill = get_object_or_404(Skill, id=skill_id, owner=request.user)
            if skill.has_upcoming_sessions():
                messages.error(
                    request,
                    f'Cannot remove "{skill.name}" — it has upcoming session(s). '
                    f'Cancel them first.'
                )
            else:
                skill.delete()
                messages.success(request, f'Skill "{skill.name}" removed.')
            return redirect('profile_edit')

    return render(request, 'accounts/profile_edit.html', {
        'profile_form': profile_form,
        'skill_form': skill_form,
        'skills': skills,
    })


@login_required
def profile_detail(request, user_id): # view other profile - pretty basic, read only
    profile_user = get_object_or_404(User, id=user_id)
    profile = Profile.objects.filter(user=profile_user).first()
    skills = Skill.objects.filter(owner=profile_user)
    upcoming_sessions = (
        Session.objects
        .filter(host=profile_user, date_time__gte=timezone.now(), is_cancelled=False)
        .select_related('skill')
        .order_by('date_time')
    )
    skill_rows = []
    if request.user.is_authenticated and request.user != profile_user:
        my_requests = {
            sr.skill_id: sr
            for sr in SessionRequest.objects.filter(requester=request.user, skill__in=skills)
        }
        for skill in skills:
            skill_rows.append({'skill': skill, 'my_request': my_requests.get(skill.id)})
    else:
        for skill in skills:
            skill_rows.append({'skill': skill, 'my_request': None})
    return render(request, 'accounts/profile_detail.html', {
        'profile_user': profile_user,
        'profile': profile,
        'skill_rows': skill_rows,
        'upcoming_sessions': upcoming_sessions,
    })


@login_required
def skill_search(request):
    query = request.GET.get('q', '').strip()
    results = []  # list of dicts: {skill, owner, profile, has_sessions, my_request}

    if query:
        skills = (
            Skill.objects.filter(name__icontains=query)
            .exclude(owner=request.user)  # don't show own skills
            .select_related('owner')
        )
        # fetch current user's pending requests in bulk
        my_requests = {
            sr.skill_id: sr
            for sr in SessionRequest.objects.filter(
                requester=request.user,
                skill__in=skills,
            )
        }
        profiles = {
            p.user_id: p
            for p in Profile.objects.filter(user__in=[s.owner for s in skills])
        }
        for skill in skills:
            results.append({
                'skill': skill,
                'owner': skill.owner,
                'profile': profiles.get(skill.owner_id),
                'has_sessions': skill.has_upcoming_sessions(),
                'my_request': my_requests.get(skill.id),
            })

    return render(request, 'accounts/skill_search.html', {
        'query': query,
        'results': results,
    })

@login_required
def profile_search(request):
    query = request.GET.get('q') # get the text entered into the search bar
    if query:
        # search by username, first name, or last name using Q module
        name_results = User.objects.filter(
            # dynamically generate Q objects
            # {field}__icontains
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)
        ).distinct() # get only one

        skill_results = Skill.objects.filter(
            name__icontains=query
            ).select_related('owner')

        session_results = Session.objects.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query),
            is_cancelled=False
            ).select_related('host', 'skill')
    else:
        name_results = User.objects.none()
        skill_results = Skill.objects.none()
        session_results = Session.objects.none()


    return render(request, 'accounts/search_results.html', {
        'name_results': name_results,
        'skill_results': skill_results,
        'session_results': session_results,
        'query': query
    })


@login_required
def session_request_create(request, skill_id):
    skill = get_object_or_404(Skill, id=skill_id)

    if skill.owner == request.user:
        messages.error(request, "You can't request a session for your own skill.")
        return redirect('skill_search')

    if SessionRequest.objects.filter(requester=request.user, skill=skill).exists():
        messages.error(request, 'You already sent a request for this skill.')
        return redirect('skill_search')

    if request.method == 'POST':
        form = SessionRequestForm(request.POST)
        if form.is_valid():
            sr = form.save(commit=False)
            sr.requester = request.user
            sr.skill = skill
            sr.save()
            messages.success(request, f'Request sent to {skill.owner.get_full_name() or skill.owner.username} for "{skill.name}".')
            return redirect('skill_search')
    else:
        form = SessionRequestForm()

    return render(request, 'accounts/session_request_create.html', {
        'skill': skill,
        'form': form,
    })


@login_required
def session_request_cancel(request, request_id):
    sr = get_object_or_404(SessionRequest, id=request_id, requester=request.user)
    if request.method == 'POST':
        sr.delete()
        messages.success(request, 'Request cancelled.')
    return redirect('skill_search')


@login_required
def session_requests_inbox(request):
    # requests sent to the current user (as skill owner)
    incoming = (
        SessionRequest.objects
        .filter(skill__owner=request.user, status=SessionRequest.STATUS_PENDING)
        .select_related('requester', 'skill')
        .order_by('-created_at')
    )

    if request.method == 'POST':
        sr_id = request.POST.get('request_id')
        action = request.POST.get('action')
        sr = get_object_or_404(SessionRequest, id=sr_id, skill__owner=request.user)
        requester_name = sr.requester.get_full_name() or sr.requester.username
        if action == 'accept':
            session = Session.objects.create(
                skill=sr.skill,
                host=sr.skill.owner,
                title=sr.proposed_title,
                description=sr.proposed_description or '',
                location=sr.proposed_location,
                date_time=sr.proposed_date_time,
                duration_minutes=sr.proposed_duration_minutes,
                capacity=sr.proposed_capacity,
            )
            SessionMembership.objects.create(session=session, user=sr.requester)
            sr.delete()
            messages.success(request, f'Accepted! Session "{session.title}" created and {requester_name} has been added.')
        elif action == 'decline':
            sr.delete()
            messages.success(request, f'Declined request from {requester_name}.')
        return redirect('session_requests_inbox')

    return render(request, 'accounts/session_requests_inbox.html', {
        'incoming': incoming,
    })

@login_required
def inbox(request):
    # find all messages sent or received
    all_messages = PrivateMessage.objects.filter(
        Q(sender=request.user) | Q(receiver=request.user)
    ).order_by('-timestamp')

    # we want to keep only one thread per sender - receiver open
    users_seen = set()
    latest_messages = []

    # sort by timestamp descending to get newest first
    for msg in all_messages.order_by('-timestamp'):

        # determine who "other" is in this context
        if msg.sender == request.user:
            other_user = msg.receiver
        else:
            other_user = msg.sender

        if other_user.id not in users_seen:
            latest_messages.append(msg)
            users_seen.add(other_user.id)

    return render(request, 'accounts/inbox.html', {'threads': latest_messages})

@login_required
def send_message(request, receiver_id):
    receiver = get_object_or_404(User, id=receiver_id)

    if request.method == 'POST':
        content = request.POST.get('content')
        if content:
            # create private message object
            PrivateMessage.objects.create(
                sender=request.user,
                receiver=receiver,
                content=content
            )
            return redirect('chat_detail', receiver_id=receiver_id)

    # get chat history between two users
    chat_history = PrivateMessage.objects.filter(
        (Q(sender=request.user) & Q(receiver=receiver)) |
        (Q(sender=receiver) & Q(receiver = request.user))
    ).order_by('timestamp')

    return render(request, 'accounts/chat_detail.html', {
        'receiver': receiver,
        'chat_history': chat_history
    })

@login_required
def browse_sharers(request):
    sharers = User.objects.all().order_by('username').prefetch_related('skills', 'profile') # Get all users
    return render(request, 'accounts/browse_sharers.html', {'sharers' : sharers})