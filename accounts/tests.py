# tests are AI gen, please add more as needed or delete these.

from datetime import timedelta
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.urls import reverse
from django.utils import timezone
from .models import Profile, Skill, PrivateMessage



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

    def test_has_upcoming_sessions_ignores_cancelled_sessions(self):
        from skillsessions.models import Session
        skill = Skill.objects.create(owner=self.user, name='Guitar')
        Session.objects.create(
            skill=skill,
            host=self.user,
            title='Cancelled Future Session',
            location='Room 1',
            date_time=timezone.now() + timedelta(days=1),
            duration_minutes=60,
            capacity=5,
            is_cancelled=True,
            cancelled_at=timezone.now(),
        )
        self.assertFalse(skill.has_upcoming_sessions())


class ProfileViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123')

    def test_profile_view_requires_login(self):
        response = self.client.get(reverse('profile_view'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('?next=', response.url)

    def test_profile_view_auto_creates_profile(self):
        self.client.login(username='testuser', password='testpass123')
        self.assertFalse(Profile.objects.filter(user=self.user).exists())
        response = self.client.get(reverse('profile_view'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Profile.objects.filter(user=self.user).exists())

    def test_profile_edit_save_bio(self):
        self.client.login(username='testuser', password='testpass123')
        Profile.objects.create(user=self.user)
        response = self.client.post(reverse('profile_edit'), {
            'action': 'save_bio',
            'bio': 'Hello world',
        })
        self.assertEqual(response.status_code, 302)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.bio, 'Hello world')

    def test_profile_edit_add_skill(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('profile_edit'), {
            'action': 'add_skill',
            'name': 'Python',
            'description': 'Web development',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Skill.objects.filter(owner=self.user, name='Python').exists())

    def test_profile_edit_add_duplicate_skill_rejected(self):
        self.client.login(username='testuser', password='testpass123')
        Skill.objects.create(owner=self.user, name='Python')
        response = self.client.post(reverse('profile_edit'), {
            'action': 'add_skill',
            'name': 'Python',
            'description': 'Again',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Skill.objects.filter(owner=self.user, name='Python').count(), 1)

    def test_profile_edit_remove_skill(self):
        self.client.login(username='testuser', password='testpass123')
        skill = Skill.objects.create(owner=self.user, name='Python')
        response = self.client.post(reverse('profile_edit'), {
            'action': 'remove_skill',
            'skill_id': skill.id,
        })
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Skill.objects.filter(id=skill.id).exists())

    def test_profile_edit_remove_skill_with_active_sessions_blocked(self):
        from skillsessions.models import Session
        self.client.login(username='testuser', password='testpass123')
        skill = Skill.objects.create(owner=self.user, name='Python')
        Session.objects.create(
            skill=skill, host=self.user, title='Test',
            location='Room 1', date_time=timezone.now() + timedelta(days=1),
            duration_minutes=60, capacity=5,
        )
        response = self.client.post(reverse('profile_edit'), {
            'action': 'remove_skill',
            'skill_id': skill.id,
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Skill.objects.filter(id=skill.id).exists())

    def test_profile_edit_cannot_remove_other_users_skill(self):
        self.client.login(username='testuser', password='testpass123')
        other_user = User.objects.create_user(username='other', password='testpass123')
        skill = Skill.objects.create(owner=other_user, name='Python')
        response = self.client.post(reverse('profile_edit'), {
            'action': 'remove_skill',
            'skill_id': skill.id,
        })
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Skill.objects.filter(id=skill.id).exists())

    def test_profile_detail_shows_other_user(self):
        self.client.login(username='testuser', password='testpass123')
        other_user = User.objects.create_user(username='other', password='testpass123')
        Profile.objects.create(user=other_user, bio='Other bio')
        response = self.client.get(reverse('profile_detail', args=[other_user.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Other bio')

    def test_profile_detail_requires_login(self):
        other_user = User.objects.create_user(username='other', password='testpass123')
        response = self.client.get(reverse('profile_detail', args=[other_user.id]))
        self.assertEqual(response.status_code, 302)
        self.assertIn('?next=', response.url)


class InboxRenderingTest(TestCase):
    """Regression tests: inbox context key must not shadow django.contrib.messages."""

    def setUp(self):
        self.client = Client()
        self.alice = User.objects.create_user(username='alice', password='testpass123')
        self.bob = User.objects.create_user(username='bob', password='testpass123')

    def test_inbox_renders_without_crash_when_empty(self):
        self.client.login(username='alice', password='testpass123')
        response = self.client.get(reverse('inbox'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'My Messages')

    def test_inbox_renders_private_messages(self):
        PrivateMessage.objects.create(
            sender=self.bob, receiver=self.alice, content='Hello Alice'
        )
        self.client.login(username='alice', password='testpass123')
        response = self.client.get(reverse('inbox'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Hello Alice')
        self.assertContains(response, 'bob')

    def test_inbox_does_not_shadow_flash_messages(self):
        """
        The real test of the shadowing bug: a flash enqueued on a prior
        request must still render on /inbox/. If the view's context key is
        'messages', it overrides django.contrib.messages and the flash text
        never reaches the template.
        """
        PrivateMessage.objects.create(
            sender=self.bob, receiver=self.alice, content='some private msg'
        )
        self.client.login(username='alice', password='testpass123')
        # Enqueue a flash by triggering the profile_edit save_bio path
        self.client.post(
            reverse('profile_edit'),
            {'action': 'save_bio', 'bio': 'new bio text'},
        )
        # Next request should render the pending flash
        response = self.client.get(reverse('inbox'))
        self.assertEqual(response.status_code, 200)
        # If 'messages' was shadowed, base.html iterates PrivateMessage
        # objects instead of real flash messages, so 'Profile updated.'
        # never appears in the rendered page.
        self.assertContains(response, 'Profile updated.')

    def test_inbox_shows_unread_thread_badge(self):
        PrivateMessage.objects.create(
            sender=self.bob, receiver=self.alice, content='Unread hello'
        )
        self.client.login(username='alice', password='testpass123')
        response = self.client.get(reverse('inbox'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '1 new')


class MessageReadStateTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.alice = User.objects.create_user(username='alice', password='testpass123')
        self.bob = User.objects.create_user(username='bob', password='testpass123')

    def test_opening_chat_marks_incoming_messages_as_read(self):
        message = PrivateMessage.objects.create(
            sender=self.bob,
            receiver=self.alice,
            content='Hello Alice',
        )
        self.client.login(username='alice', password='testpass123')
        response = self.client.get(reverse('chat_detail', args=[self.bob.id]))
        self.assertEqual(response.status_code, 200)
        message.refresh_from_db()
        self.assertTrue(message.is_read)

    def test_sending_message_does_not_mark_outgoing_as_read(self):
        self.client.login(username='alice', password='testpass123')
        self.client.post(reverse('chat_detail', args=[self.bob.id]), {
            'content': 'Hi Bob',
        })
        message = PrivateMessage.objects.get(sender=self.alice, receiver=self.bob)
        self.assertFalse(message.is_read)


class NavbarNotificationTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.host = User.objects.create_user(username='host', password='testpass123')
        self.requester = User.objects.create_user(username='requester', password='testpass123')
        self.other = User.objects.create_user(username='other', password='testpass123')
        skill = Skill.objects.create(owner=self.host, name='Python')
        from .models import SessionRequest
        SessionRequest.objects.create(
            requester=self.requester,
            skill=skill,
            proposed_title='Need Help',
            proposed_location='Room 101',
            proposed_date_time=timezone.now() + timedelta(days=1),
            proposed_duration_minutes=60,
            proposed_capacity=1,
        )
        PrivateMessage.objects.create(
            sender=self.other,
            receiver=self.host,
            content='New message',
        )

    def test_navbar_shows_pending_request_and_unread_message_counts(self):
        self.client.login(username='host', password='testpass123')
        response = self.client.get(reverse('profile_view'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['navbar_pending_request_count'], 1)
        self.assertEqual(response.context['navbar_unread_message_count'], 1)
        self.assertContains(response, 'Requests')
        self.assertContains(response, 'My Messages')
