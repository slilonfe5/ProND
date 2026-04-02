# TODO - delete session as host

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.http import HttpResponseForbidden
from accounts.models import Skill
from .models import Session, SessionMembership, SessionMessage
from .forms import SessionForm, SessionMessageForm, SessionMessageEditForm


@login_required
def session_list(request): # main page - list session upcoming in chronological order
    sessions = Session.objects.filter(
        date_time__gte=timezone.now(),
        is_cancelled=False
    ).order_by('date_time').select_related('skill', 'host')
    return render(request, 'sessions/session_list.html', {
        'sessions': sessions,
    })


@login_required
def session_create(request): # create own session page - select own skill from dropdown, fill in attributes. requires 1+ skill to exist with Profile (add ability to create on the spot?)
    user_skills = Skill.objects.filter(owner=request.user)
    if not user_skills.exists():
        messages.warning(request, 'You must add a Skill before creating a Session.')
        return redirect('profile_edit')

    if request.method == 'POST':
        form = SessionForm(request.POST)
        form.fields['skill'].queryset = user_skills
        if form.is_valid():
            session = form.save(commit=False)
            session.host = request.user
            session.save()
            messages.success(request, f'Session "{session.title}" created.')
            return redirect('session_detail', pk=session.pk)
    else:
        form = SessionForm()
        form.fields['skill'].queryset = user_skills

    return render(request, 'sessions/session_create.html', {'form': form})


@login_required
def session_detail(request, pk): # view session details. conditional buttons based on host/member/joinable
    session = get_object_or_404(
        Session.objects.select_related('skill', 'host'),
        pk=pk
    )
    memberships = session.memberships.select_related('user')
    session_messages = session.messages.select_related('author')
    membership_count = memberships.count()

    is_host = request.user == session.host
    is_member = memberships.filter(user=request.user).exists()
    is_full = membership_count >= session.capacity
    is_past = session.date_time < timezone.now()
    can_access_chat = session.user_can_access_chat(request.user)

    message_form = None
    if can_access_chat:
        message_form = SessionMessageForm()
        if not session.user_can_post_announcement(request.user):
            message_form.fields['is_announcement'].widget = message_form.fields['is_announcement'].hidden_widget()

    return render(request, 'sessions/session_detail.html', {
        'session': session,
        'memberships': memberships,
        'session_messages': session_messages,
        'membership_count': membership_count,
        'is_host': is_host,
        'is_member': is_member,
        'is_full': is_full,
        'is_past': is_past,
        'can_access_chat': can_access_chat,
        'message_form': message_form,
    })


@login_required
def session_join(request, pk): # POST only - join session if not host, not already joined, not full, current
    session = get_object_or_404(Session, pk=pk)

    if request.method != 'POST':
        return redirect('session_detail', pk=pk)

    if request.user == session.host:
        messages.error(request, 'You cannot join your own session.')
        return redirect('session_detail', pk=pk)

    if session.date_time < timezone.now():
        messages.error(request, 'This session has already passed.')
        return redirect('session_detail', pk=pk)

    with transaction.atomic():
        membership_count = session.memberships.count()
        if membership_count >= session.capacity:
            messages.error(request, 'This session is full.')
            return redirect('session_detail', pk=pk)

        if session.memberships.filter(user=request.user).exists():
            messages.info(request, 'You are already a member of this session.')
            return redirect('session_detail', pk=pk)

        SessionMembership.objects.create(session=session, user=request.user)

    messages.success(request, f'You joined "{session.title}".')
    return redirect('session_detail', pk=pk)


@login_required
def session_leave(request, pk): # POST only - leave session as member
    session = get_object_or_404(Session, pk=pk)

    if request.method != 'POST':
        return redirect('session_detail', pk=pk)

    membership = session.memberships.filter(user=request.user).first()
    if membership:
        membership.delete()
        messages.success(request, f'You left "{session.title}".')
    else:
        messages.info(request, 'You are not a member of this session.')

    return redirect('session_detail', pk=pk)


@login_required
def session_message_create(request, pk):
    session = get_object_or_404(Session.objects.select_related('host'), pk=pk)

    if request.method != 'POST':
        return redirect('session_detail', pk=pk)

    if not session.user_can_access_chat(request.user):
        messages.error(request, 'Join this session before using the chat.')
        return redirect('session_detail', pk=pk)

    form = SessionMessageForm(request.POST)
    if not session.user_can_post_announcement(request.user):
        form.data = form.data.copy()
        form.data['is_announcement'] = ''

    if form.is_valid():
        session_message = form.save(commit=False)
        session_message.session = session
        session_message.author = request.user
        session_message.save()
        if session_message.is_announcement:
            messages.success(request, 'Announcement posted.')
        else:
            messages.success(request, 'Message sent.')
    else:
        errors = ' '.join(form.errors.get('content', [])) or 'Please enter a valid message.'
        messages.error(request, errors)

    return redirect('session_detail', pk=pk)


@login_required
def session_message_edit(request, pk, message_id):
    session_message = get_object_or_404(
        SessionMessage.objects.select_related('session', 'session__host', 'author'),
        pk=message_id,
        session_id=pk,
    )

    if not session_message.user_can_manage(request.user):
        return HttpResponseForbidden('You can only edit your own messages.')

    if request.method == 'POST':
        form = SessionMessageEditForm(request.POST, instance=session_message)
        if not session_message.session.user_can_post_announcement(request.user):
            form.data = form.data.copy()
            form.data['is_announcement'] = ''

        if form.is_valid():
            form.save()
            messages.success(request, 'Message updated.')
            return redirect('session_detail', pk=pk)
    else:
        form = SessionMessageEditForm(instance=session_message)
        if not session_message.session.user_can_post_announcement(request.user):
            form.fields['is_announcement'].widget = form.fields['is_announcement'].hidden_widget()

    return render(request, 'sessions/session_message_edit.html', {
        'session': session_message.session,
        'session_message': session_message,
        'form': form,
    })


@login_required
def session_message_delete(request, pk, message_id):
    session_message = get_object_or_404(
        SessionMessage.objects.select_related('session', 'author'),
        pk=message_id,
        session_id=pk,
    )

    if not session_message.user_can_manage(request.user):
        return HttpResponseForbidden('You can only delete your own messages.')

    if request.method == 'POST':
        session_message.delete()
        messages.success(request, 'Message deleted.')

    return redirect('session_detail', pk=pk)

@login_required
def cancel_session(request, session_id):
    session = get_object_or_404(Session, id=session_id)

    if session.creator != request.user:
        return HttpResponseForbidden("You cannot cancel this session.")

    session.is_cancelled = True
    session.cancelled_at = timezone.now()
    session.save()

    return redirect("session_detail", session_id=session.id)
