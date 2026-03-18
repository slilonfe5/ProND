from django.test import TestCase
from django.contrib.auth.models import User
from django.db import IntegrityError
from .models import Profile, Skill


class ProfileModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')

    def test_create_profile(self):
        profile = Profile.objects.create(user=self.user)
        self.assertEqual(profile.user, self.user)
        self.assertEqual(profile.bio, '')
        self.assertIsNotNone(profile.created_at)
        self.assertIsNotNone(profile.updated_at)

    def test_profile_str(self):
        profile = Profile.objects.create(user=self.user)
        self.assertEqual(str(profile), 'testuser')

    def test_one_profile_per_user(self):
        Profile.objects.create(user=self.user)
        with self.assertRaises(IntegrityError):
            Profile.objects.create(user=self.user)


class SkillModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.other_user = User.objects.create_user(username='otheruser', password='testpass123')

    def test_create_skill(self):
        skill = Skill.objects.create(owner=self.user, name='Python', description='Web dev')
        self.assertEqual(skill.owner, self.user)
        self.assertEqual(skill.name, 'Python')
        self.assertIsNotNone(skill.created_at)

    def test_skill_str(self):
        skill = Skill.objects.create(owner=self.user, name='Python')
        self.assertEqual(str(skill), 'Python')

    def test_duplicate_skill_name_same_user_rejected(self):
        Skill.objects.create(owner=self.user, name='Python')
        with self.assertRaises(IntegrityError):
            Skill.objects.create(owner=self.user, name='Python')

    def test_different_skill_name_same_user_allowed(self):
        Skill.objects.create(owner=self.user, name='Python')
        Skill.objects.create(owner=self.user, name='Django')
        self.assertEqual(Skill.objects.filter(owner=self.user).count(), 2)

    def test_same_skill_name_different_users_allowed(self):
        Skill.objects.create(owner=self.user, name='Python')
        Skill.objects.create(owner=self.other_user, name='Python')
        self.assertEqual(Skill.objects.filter(name='Python').count(), 2)
