# hello
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Max
from django.contrib.auth.models import User
from .models import Profile, Skill, PrivateMessage
from .forms import ProfileForm, SkillForm
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

        if action == 'save_bio': # update bio, profile only
            profile_form = ProfileForm(request.POST, instance=profile)
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
    return render(request, 'accounts/profile_detail.html', {
        'profile_user': profile_user,
        'profile': profile,
        'skills': skills,
    })

@login_required
def profile_search(request):
    query = request.GET.get('q') # get the text entered into the search bar
    if query:
        # search by username, first name, or last name using Q module
        results = User.objects.filter(
            # dynamically generate Q objects
            # {field}__icontains
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)
        ).distinct() # get only one
    else:
        results = User.objects.none() # return none instead of crashing

    return render(request, 'accounts/search_results.html', {
        'results': results,
        'query': query
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

    return render(request, 'accounts/inbox.html', {'messages': latest_messages})

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