from django.test import TestCase
from django.core.urlresolvers import reverse
import aristotle_mdr.tests.utils as utils

from django.test.utils import setup_test_environment
setup_test_environment()

class UserHomePages(utils.LoggedInViewPages,TestCase):
    def setUp(self):
        super(UserHomePages, self).setUp()

    def check_generic_pages(self):
        response = self.client.get(reverse('aristotle:userHome',))
        self.assertEqual(response.status_code,200)
        response = self.client.get(reverse('aristotle:userEdit',))
        self.assertEqual(response.status_code,200)
        response = self.client.get(reverse('aristotle:userInbox',))
        self.assertEqual(response.status_code,200)
        response = self.client.get(reverse('aristotle:userInbox',args=['all']))
        self.assertEqual(response.status_code,200)
        response = self.client.get(reverse('aristotle:userFavourites',))
        self.assertEqual(response.status_code,200)
        response = self.client.get(reverse('aristotle:userWorkgroups',))
        self.assertEqual(response.status_code,200)

        new_email = 'my_new@email.com'
        response = self.client.get(reverse('aristotle:userEdit'),{'email': new_email})
        self.assertEqual(response.status_code,200)
        # TODO: check this saves correctly

    def test_viewer_can_access_homepages(self):
        self.login_viewer()
        self.check_generic_pages()

        # A viewer, has no registrar permissions:
        response = self.client.get(reverse('aristotle:userRegistrarTools',))
        self.assertEqual(response.status_code,403)
        response = self.client.get(reverse('aristotle:userReadyForReview',))
        self.assertEqual(response.status_code,403)

        # A view is not a superuser
        response = self.client.get(reverse('aristotle:userAdminTools',))
        self.assertEqual(response.status_code,403)
        self.logout()

    def test_registrar_can_access_tools(self):
        self.login_registrar()
        self.check_generic_pages()

        self.assertTrue(self.registrar.profile.is_registrar)
        response = self.client.get(reverse('aristotle:userRegistrarTools',))
        self.assertEqual(response.status_code,200)
        response = self.client.get(reverse('aristotle:userReadyForReview',))
        self.assertEqual(response.status_code,200)

    def test_superuser_can_access_tools(self):
        self.login_superuser()
        self.check_generic_pages()

        self.assertTrue(self.su.profile.is_registrar)
        response = self.client.get(reverse('aristotle:userRegistrarTools',))
        self.assertEqual(response.status_code,200)
        response = self.client.get(reverse('aristotle:userReadyForReview',))
        self.assertEqual(response.status_code,200)

        self.assertTrue(self.su.is_superuser)
        response = self.client.get(reverse('aristotle:userAdminTools',))
        self.assertEqual(response.status_code,200)
        self.logout()
