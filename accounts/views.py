# hello
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
from .models import Profile, Skill
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