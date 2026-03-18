from datetime import timedelta
from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone
from accounts.models import Skill
from .models import Session, SessionMembership


class SessionModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='host', password='testpass123')
        self.skill = Skill.objects.create(owner=self.user, name='Python')

    def test_create_session(self):
        session = Session.objects.create(
            skill=self.skill,
            host=self.user,
            title='Python Basics',
            description='Intro to Python',
            location='Room 101',
            date_time=timezone.now() + timedelta(days=1),
            duration=timedelta(hours=1),
            capacity=10,
        )
        self.assertEqual(session.host, self.user)
        self.assertEqual(session.skill, self.skill)
        self.assertIsNotNone(session.created_at)

    def test_session_str(self):
        session = Session.objects.create(
            skill=self.skill,
            host=self.user,
            title='Python Basics',
            location='Room 101',
            date_time=timezone.now() + timedelta(days=1),
            duration=timedelta(hours=1),
            capacity=10,
        )
        self.assertEqual(str(session), 'Python Basics (Python)')

    def test_clean_rejects_mismatched_host_and_skill_owner(self):
        other_user = User.objects.create_user(username='other', password='testpass123')
        session = Session(
            skill=self.skill,
            host=other_user,
            title='Stolen Session',
            location='Room 101',
            date_time=timezone.now() + timedelta(days=1),
            duration=timedelta(hours=1),
            capacity=10,
        )
        with self.assertRaises(ValidationError):
            session.clean()

    def test_clean_accepts_matching_host_and_skill_owner(self):
        session = Session(
            skill=self.skill,
            host=self.user,
            title='Valid Session',
            location='Room 101',
            date_time=timezone.now() + timedelta(days=1),
            duration=timedelta(hours=1),
            capacity=10,
        )
        session.clean()  # should not raise


class SessionMembershipModelTest(TestCase):
    def setUp(self):
        self.host = User.objects.create_user(username='host', password='testpass123')
        self.learner = User.objects.create_user(username='learner', password='testpass123')
        self.skill = Skill.objects.create(owner=self.host, name='Python')
        self.session = Session.objects.create(
            skill=self.skill,
            host=self.host,
            title='Python Basics',
            location='Room 101',
            date_time=timezone.now() + timedelta(days=1),
            duration=timedelta(hours=1),
            capacity=10,
        )

    def test_create_membership(self):
        membership = SessionMembership.objects.create(
            session=self.session,
            user=self.learner,
        )
        self.assertEqual(membership.session, self.session)
        self.assertEqual(membership.user, self.learner)
        self.assertIsNotNone(membership.joined_at)

    def test_membership_str(self):
        membership = SessionMembership.objects.create(
            session=self.session,
            user=self.learner,
        )
        self.assertEqual(str(membership), 'learner in Python Basics')

    def test_duplicate_membership_rejected(self):
        SessionMembership.objects.create(session=self.session, user=self.learner)
        with self.assertRaises(IntegrityError):
            SessionMembership.objects.create(session=self.session, user=self.learner)

    def test_same_user_different_sessions_allowed(self):
        other_session = Session.objects.create(
            skill=self.skill,
            host=self.host,
            title='Python Advanced',
            location='Room 102',
            date_time=timezone.now() + timedelta(days=2),
            duration=timedelta(hours=1),
            capacity=5,
        )
        SessionMembership.objects.create(session=self.session, user=self.learner)
        SessionMembership.objects.create(session=other_session, user=self.learner)
        self.assertEqual(SessionMembership.objects.filter(user=self.learner).count(), 2)
