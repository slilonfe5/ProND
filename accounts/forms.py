from django import forms
from .models import Profile, Skill, SessionRequest


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['bio', 'photo']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'photo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }


class SessionRequestForm(forms.ModelForm):
    class Meta:
        model = SessionRequest
        fields = [
            'proposed_title', 'proposed_description', 'proposed_location',
            'proposed_date_time', 'proposed_duration_minutes', 'proposed_capacity',
            'message',
        ]
        widgets = {
            'proposed_title': forms.TextInput(attrs={'class': 'form-control'}),
            'proposed_description': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'proposed_location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Room 101, Zoom link, etc.'}),
            'proposed_date_time': forms.DateTimeInput(
                attrs={'type': 'datetime-local', 'class': 'form-control'},
                format='%Y-%m-%dT%H:%M',
            ),
            'proposed_duration_minutes': forms.NumberInput(attrs={'class': 'form-control', 'min': '5'}),
            'proposed_capacity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'message': forms.Textarea(attrs={'rows': 2, 'class': 'form-control', 'placeholder': 'Optional note to the skill owner...'}),
        }
        labels = {
            'proposed_title': 'Session Title',
            'proposed_description': 'Description (optional)',
            'proposed_location': 'Location',
            'proposed_date_time': 'Date & Time',
            'proposed_duration_minutes': 'Duration (minutes)',
            'proposed_capacity': 'Capacity',
            'message': 'Message to owner (optional)',
        }


class SkillForm(forms.ModelForm): # form for editing your skills, put name + description
    class Meta:
        model = Skill
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }
