from django.test import TestCase, tag, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core import mail
from unittest.mock import patch, MagicMock

import aristotle_mdr.tests.utils as utils

from aristotle_mdr.utils import setup_aristotle_test_environment

setup_aristotle_test_environment()


@tag('usermanage')
class UserManagementPages(utils.LoggedInViewPages, TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.signup_data = {
            'email': 'test@example.com',
            'full_name': 'test',
            'short_name': 't',
            'password': '1234',
            'password_confirm': '1234'
        }

        super().setUp()

    def get_url_from_email(self, email_content):
        start = email_content.find('/account/')
        end = email_content.find('\n', start)

        accept_url = email_content[start:end]
        return accept_url

    def test_user_cannot_view_userlist(self):
        self.login_viewer()
        response = self.client.get(reverse('aristotle-user:registry_user_list',))
        self.assertEqual(response.status_code, 403)

    def test_su_can_view_userlist(self):
        self.login_superuser()
        response = self.client.get(reverse('aristotle-user:registry_user_list',))
        self.assertEqual(response.status_code, 200)


    def test_user_cannot_deactivate_user(self):
        self.login_viewer()
        response = self.client.get(reverse('aristotle-user:deactivate_user', args=[self.viewer.pk]))
        self.assertEqual(response.status_code, 403)

        response = self.client.post(reverse('aristotle-user:deactivate_user', args=[self.viewer.pk]))
        self.assertEqual(response.status_code, 403)

    def test_su_can_deactivate_user(self):
        self.login_superuser()
        self.assertTrue(self.viewer.is_active == True)
        response = self.client.get(reverse('aristotle-user:deactivate_user', args=[self.viewer.pk]))
        self.assertEqual(response.status_code, 200)

        self.assertTrue(self.viewer.is_active == True)
        response = self.client.post(reverse('aristotle-user:deactivate_user', args=[self.viewer.pk]))
        self.assertEqual(response.status_code, 302)

        self.viewer = get_user_model().objects.get(pk=self.viewer.pk)
        self.assertTrue(self.viewer.is_active == False)

    def test_user_cannot_reactivate_user(self):
        self.login_ramanager()
        self.viewer.is_active = False
        self.viewer.save()

        response = self.client.get(reverse('aristotle-user:reactivate_user', args=[self.viewer.pk]))
        self.assertEqual(response.status_code, 403)

        response = self.client.post(reverse('aristotle-user:reactivate_user', args=[self.viewer.pk]))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(self.viewer.is_active == False)

    def test_su_can_reactivate_user(self):
        self.login_superuser()
        self.viewer.is_active = False
        self.viewer.save()

        response = self.client.get(reverse('aristotle-user:reactivate_user', args=[self.viewer.pk]))
        self.assertEqual(response.status_code, 200)

        self.assertTrue(self.viewer.is_active == False)
        response = self.client.post(reverse('aristotle-user:reactivate_user', args=[self.viewer.pk]))
        self.assertEqual(response.status_code, 302)

        self.viewer = get_user_model().objects.get(pk=self.viewer.pk)
        self.assertTrue(self.viewer.is_active == True)

    def test_send_invitation(self):

        self.login_superuser()

        response = self.client.get(reverse('aristotle-user:registry_invitations_create'))
        self.assertEqual(response.status_code, 200)

        # Test mail outbox empty
        self.assertEqual(len(mail.outbox), 0)

        data = {
            'email_list': 'wow@example.com\nmetoo@example.com'
        }

        post_response = self.client.post(reverse('aristotle-user:registry_invitations_create'), data)
        self.assertEqual(post_response.status_code, 302)

        # Test that invitations were sent
        self.assertEqual(len(mail.outbox), 2)
        self.assertTrue(mail.outbox[0].subject.startswith('You\'ve been invited'))

    def test_accept_invitation(self):

        self.login_superuser()
        self.assertEqual(len(mail.outbox), 0)

        data = {
            'email_list': 'test@example.com'
        }

        post_response = self.client.post(reverse('aristotle-user:registry_invitations_create'), data)
        self.assertEqual(post_response.status_code, 302)

        # Test that invitations were sent
        self.assertEqual(len(mail.outbox), 1)

        self.logout()
        message = mail.outbox[0].body

        accept_url = self.get_url_from_email(message)

        accept_response = self.client.get(accept_url)

        self.assertEqual(accept_response.status_code, 200)

        formfields = accept_response.context['form'].fields.keys()
        removed_fields = ['username', 'first_name', 'last_name']
        added_fields = ['short_name', 'full_name']

        for field in removed_fields:
            self.assertFalse(field in formfields)

        for field in added_fields:
            self.assertTrue(field in formfields)

        accept_data = {
            'email': 'test@example.com',
            'full_name': 'Test User',
            'short_name': 'Test',
            'password': 'verynice',
            'password_confirm': 'verynice'
        }

        response = self.client.post(accept_url, accept_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'aristotle_mdr/friendly_login.html')
        self.assertTrue('welcome' in response.context.keys())

        new_user = get_user_model().objects.get(email='test@example.com')
        self.assertTrue(new_user.is_active)
        self.assertTrue(new_user.password)
        self.assertEqual(new_user.short_name, 'Test')
        self.assertEqual(new_user.full_name, 'Test User')

    def test_self_registration_page(self):

        self.login_superuser()
        response = self.client.get(reverse('aristotle-user:signup_register'))
        self.assertRedirects(response, reverse('aristotle_mdr:userHome'))

        self.logout()
        self.assertEqual(len(mail.outbox), 0)

        # With a signup message
        mock_settings = MagicMock(return_value={'registry': {'SELF_SIGNUP': {'enabled': True, 'message': 'Welcome You Can Signup Here'}}})
        with patch('aristotle_mdr.contrib.user_management.views.fetch_aristotle_settings', mock_settings):
            with patch('aristotle_mdr.context_processors.fetch_aristotle_settings', mock_settings):
                response = self.client.get(reverse('aristotle-user:signup_register'))
                self.assertEqual(response.status_code, 200)
                self.assertTrue('Welcome You Can Signup Here' in str(response.content))

        # With signup disabled
        mock_settings = MagicMock(return_value={'registry': {'SELF_SIGNUP': {'enabled': False}}})
        with patch('aristotle_mdr.contrib.user_management.views.fetch_aristotle_settings', mock_settings):
            response = self.client.get(reverse('aristotle-user:signup_register'))
            self.assertEqual(response.status_code, 200)
            self.assertFalse('form' in response.context)
            self.assertTrue('error_message' in response.context)

        # With signup enabled
        mock_settings = MagicMock(return_value={'registry': {'SELF_SIGNUP': {'enabled': True}}})
        with patch('aristotle_mdr.contrib.user_management.views.fetch_aristotle_settings', mock_settings):
            response = self.client.get(reverse('aristotle-user:signup_register'))
            self.assertEqual(response.status_code, 200)
            self.assertTrue('form' in response.context)

            # Post correct info
            post_response = self.client.post(reverse('aristotle-user:signup_register'), self.signup_data)
            self.assertEqual(post_response.status_code, 200)
            self.assertTrue(post_response.context['message'].startswith('Success'))
            user = get_user_model().objects.get(email='test@example.com')
            self.assertEqual(user.is_active, False)
            self.assertEqual(user.full_name, 'test')
            self.assertEqual(user.short_name, 't')

            # Post with wrong confirm password
            bad_data = self.signup_data.copy()
            bad_data.update({'password_confirm': 'extrasecure'})
            post_response = self.client.post(reverse('aristotle-user:signup_register'), bad_data)
            self.assertTrue(post_response.status_code, 200)
            self.assertEqual(post_response.context['form'].non_field_errors(), ['Your password entries must match'])

        self.assertEqual(len(mail.outbox), 1)

    @tag('runthis')
    def test_self_registration_page_information_leak(self):
        # Test wether the page reveals that a user already exists

        existing_user = self.user_model.objects.create_user(
            'existing@example.com',
            'verysecure'
        )

        existing_data = self.signup_data.copy()
        existing_data.update({'email': 'existing@example.com'})

        # With signup enabled
        mock_settings = MagicMock(return_value={'registry': {'SELF_SIGNUP': {'enabled': True}}})
        with patch('aristotle_mdr.contrib.user_management.views.fetch_aristotle_settings', mock_settings):

            post_response = self.client.post(reverse('aristotle-user:signup_register'), existing_data)
            self.assertEqual(post_response.status_code, 200)
            self.assertFalse('form' in post_response.context)


    def test_self_registration_email_whitelist(self):

        # With email whilelist set
        mock_settings = MagicMock(return_value={'registry': {'SELF_SIGNUP': {'enabled': True, 'emails': ['.gov.au', 'hellokitty.com']}}})
        with patch('aristotle_mdr.contrib.user_management.views.fetch_aristotle_settings', mock_settings):
            bad_data = self.signup_data.copy()
            bad_data.update({'email': 'notallowed@example.com'})
            post_response = self.client.post(reverse('aristotle-user:signup_register'), bad_data)
            self.assertTrue(post_response.status_code, 200)
            self.assertEqual(post_response.context['form'].errors['email'], ['Email is not at an allowed url'])

            bad_data.update({'email': 'someguy@example.gov.au'})
            post_response = self.client.post(reverse('aristotle-user:signup_register'), bad_data)
            self.assertTrue(post_response.status_code, 200)
            self.assertTrue(post_response.context['message'].startswith('Success'))

            bad_data.update({'email': 'someguy@hellokitty.com'})
            post_response = self.client.post(reverse('aristotle-user:signup_register'), bad_data)
            self.assertTrue(post_response.status_code, 200)
            self.assertTrue(post_response.context['message'].startswith('Success'))


        self.assertEqual(len(mail.outbox), 2)

    def test_accept_registration_email(self):

        self.logout()
        self.assertEqual(len(mail.outbox), 0)

        # Test entering correct data, following link in email
        mock_settings = MagicMock(
            return_value={'registry': {'SELF_SIGNUP': {'enabled': True}}, 'SITE_NAME': 'Testing Registry'}
        )
        with patch('aristotle_mdr.contrib.user_management.views.fetch_aristotle_settings', mock_settings):

            post_response = self.client.post(reverse('aristotle-user:signup_register'), self.signup_data)
            self.assertTrue(post_response.status_code, 200)
            self.assertTrue(post_response.context['message'].startswith('Success'))
            self.assertEqual(len(mail.outbox), 1)

            message = mail.outbox[0].body
            accept_url = self.get_url_from_email(message)

            response = self.client.get(accept_url, follow=True)

            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, 'aristotle_mdr/friendly_login.html')
            self.assertTrue('welcome' in response.context.keys())

        new_user = get_user_model().objects.get(email='test@example.com')
        self.assertTrue(new_user.is_active)
        self.assertTrue(new_user.password)
        self.assertEqual(new_user.short_name, 't')
        self.assertEqual(new_user.full_name, 'test')

        # Check notify emails
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[1].to, ['super@example.com'])
        self.assertTrue('Testing Registry' in mail.outbox[1].subject)


    def test_self_register_activate_error_handling(self):

        mock_settings = MagicMock(return_value={'registry': {'SELF_SIGNUP': {'enabled': False}}})
        with patch('aristotle_mdr.contrib.user_management.views.fetch_aristotle_settings', mock_settings):
            # Test trying to activate with signup disabled
            response = self.client.get(reverse('aristotle-user:signup_activate', args=['0', '3-4']))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context['error_message'], 'Self Signup is not enabled')

        mock_settings = MagicMock(return_value={'registry': {'SELF_SIGNUP': {'enabled': True}}})
        with patch('aristotle_mdr.contrib.user_management.views.fetch_aristotle_settings', mock_settings):

            bad_data = self.signup_data.copy()
            bad_data.update({'email': 'bestuser@example.com'})
            post_response = self.client.post(reverse('aristotle-user:signup_register'), bad_data)
            self.assertTrue(post_response.status_code, 200)
            self.assertTrue(post_response.context['message'].startswith('Success'))
            self.assertEqual(len(mail.outbox), 1)

            message = mail.outbox[0].body
            accept_url = self.get_url_from_email(message)

            # Test trying to activate with an invalid code
            response = self.client.get(reverse('aristotle-user:signup_activate', args=['0', '3-4']))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context['error_message'], 'Account could not be activated')

            # Test trying to activate an already active account
            user = get_user_model().objects.get(email='bestuser@example.com')
            self.assertEqual(user.is_active, False)
            user.is_active = True
            user.save()

            response = self.client.get(accept_url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context['error_message'], 'Account could not be activated')


    def test_resend_activation(self):

        user_model = get_user_model()

        inactive_user = user_model.objects.create(
            email='inactive@example.com',
            password='1234',
            is_active=False
        )

        active_user = user_model.objects.create(
            email='active@example.com',
            password='1234',
            is_active=True
        )

        response = self.client.get(reverse('aristotle-user:signup_resend'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['title'], 'Resend Activation')

        # Try to resend to account that doesnt exist
        response = self.client.post(
            reverse('aristotle-user:signup_resend'),
            {'email': 'i_dont_even_exist@example.com'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context['form'].non_field_errors(),
            ['Activation email could not be sent']
        )

        # Try to resend to already active user
        response = self.client.post(
            reverse('aristotle-user:signup_resend'),
            {'email': 'active@example.com'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context['form'].non_field_errors(),
            ['Activation email could not be sent']
        )

        # Resend to an inactive user
        response = self.client.post(
            reverse('aristotle-user:signup_resend'),
            {'email': 'inactive@example.com'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['message'].startswith('Success'))

        self.assertEqual(len(mail.outbox), 1)

