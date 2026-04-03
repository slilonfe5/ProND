from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Profile(models.Model): # Profile model - contains user info + bio, 1:1 relation with django User
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile') #1:1 relation with User model, cascade delete if user deleted
    bio = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}"


class Skill(models.Model): # Skill model - contains your "skills" that are associated with sessions, many skills per user, unique name per user
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='skills') # fk to *User* model - could go to Profile and cascade?
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta: # unique constraint per user - no dupes
        constraints = [
            models.UniqueConstraint(fields=['owner', 'name'], name='unique_skill_per_user')
        ]

    def has_upcoming_sessions(self): # boolean check if skill has upcoming sessions - can block deletion if True
        return self.sessions.filter(date_time__gte=timezone.now()).exists()

    def __str__(self):
        return f"{self.name}"

class PrivateMessage(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages') # ptr to sender
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages') # ptr to receiver
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"From {self.sender} to {self.receiver}"