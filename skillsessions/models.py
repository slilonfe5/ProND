from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.formats import date_format
from accounts.models import Skill


class Session(models.Model): # session model - meeting for skill, fk to Skill and User/host + descriptor attributes
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name='sessions')
    host = models.ForeignKey(User, on_delete=models.CASCADE, related_name='hosted_sessions')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=200)
    date_time = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(validators=[MinValueValidator(5)])
    capacity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_cancelled = models.BooleanField(default=False)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    is_private = models.BooleanField(default=False)

    def clean(self):
        if self.skill_id and self.host_id and self.skill.owner != self.host:
            raise ValidationError("You can only create sessions for your own skills.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        if self.skill_id:
            return f"{self.title} ({self.skill.name})"
        return self.title

    def user_can_access_chat(self, user):
        if not user.is_authenticated:
            return False
        if user == self.host:
            return True
        return self.memberships.filter(user=user).exists()

    def user_can_post_announcement(self, user):
        return user.is_authenticated and user == self.host


class SessionMembership(models.Model): # model for tracking which users are attending which sessions. fk to Session and User, unique constraint to prevent dupes
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='session_memberships')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta: # unique constraint for no dupes
        constraints = [
            models.UniqueConstraint(fields=['session', 'user'], name='unique_session_membership')
        ]

    def __str__(self):
        return f"{self.user.username} in {self.session.title}"


class SessionMessage(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='messages')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='session_messages')
    content = models.TextField(max_length=1000)
    is_announcement = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['created_at', 'id']

    def clean(self):
        if self.session_id and self.author_id and not self.session.user_can_access_chat(self.author):
            raise ValidationError("Only session participants can send messages.")

        if self.is_announcement and self.session_id and self.author_id and self.session.host_id != self.author_id:
            raise ValidationError("Only the host can post announcements.")

    def save(self, *args, **kwargs):
        if self.pk:
            self.updated_at = timezone.now()
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def was_edited(self):
        return self.updated_at > self.created_at

    @property
    def display_created_at(self):
        return date_format(timezone.localtime(self.created_at), "M j, g:i A")

    @property
    def display_updated_at(self):
        return date_format(timezone.localtime(self.updated_at), "M j, g:i A")

    def user_can_manage(self, user):
        return user.is_authenticated and user == self.author

    def __str__(self):
        return f"{self.author.username} in {self.session.title}"
