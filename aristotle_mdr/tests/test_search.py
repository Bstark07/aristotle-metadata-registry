from django.test import TestCase

import aristotle_mdr.models as models
import aristotle_mdr.perms as perms
import aristotle_mdr.tests.utils as utils
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test.utils import override_settings

from django.test.utils import setup_test_environment
setup_test_environment()

class TestSearch(utils.LoggedInViewPages,TestCase):
    def tearDown(self):
        call_command('clear_index', interactive=False, verbosity=0)

    def setUp(self):
        super(TestSearch, self).setUp()
        import haystack
        haystack.connections.reload('default')

        self.ra = models.RegistrationAuthority.objects.create(name="Kelly Act")
        self.ra1 = models.RegistrationAuthority.objects.create(name="Superhuman Registration Act") # Anti-registration!
        self.registrar = User.objects.create_user('stryker','william.styker@weaponx.mil','mutantsMustDie')
        self.ra.giveRoleToUser('registrar',self.registrar)
        self.assertTrue(perms.user_is_registrar(self.registrar,self.ra))
        xmen = "professorX cyclops iceman angel beast phoenix wolverine storm nightcrawler"

        self.xmen_wg = models.Workgroup.objects.create(name="X Men")
        self.xmen_wg.registrationAuthorities.add(self.ra)
        self.xmen_wg.save()

        self.item_xmen = [
            models.ObjectClass.objects.create(name=t,description="known xman",workgroup=self.xmen_wg,readyToReview=True)\
            for t in xmen.split() ]
        for item in self.item_xmen:
            self.ra.register(item,models.STATES.standard,self.registrar)
            self.assertTrue(item.is_public())


        avengers = "thor spiderman ironman hulk captainAmerica"

        self.avengers_wg = models.Workgroup.objects.create(name="Avengers")
        self.avengers_wg.registrationAuthorities.add(self.ra1)
        self.item_avengers = [
            models.ObjectClass.objects.create(name=t,workgroup=self.avengers_wg)
            for t in avengers.split() ]

    def test_empty_search(self):
        self.logout()
        response = self.client.get(reverse('aristotle:search')+"?q=")
        self.assertEqual(response.status_code,200)
        self.assertEqual(len(response.context['page'].object_list),0)

    @override_settings(HAYSTACK_SEARCH_RESULTS_PER_PAGE = 20) # Supress paginating.
    def test_public_search(self):
        self.logout()
        response = self.client.get(reverse('aristotle:search')+"?q=xman")
        self.assertEqual(response.status_code,200)
        self.assertEqual(len(response.context['page'].object_list),len(self.item_xmen))
        for i in response.context['page'].object_list:
            self.assertTrue(i.object.is_public())

    @override_settings(HAYSTACK_SEARCH_RESULTS_PER_PAGE = 2) # Supress paginating.
    def test_public_search_paginating(self):
        self.logout()
        response = self.client.get(reverse('aristotle:search')+"?q=xman")
        self.assertEqual(response.status_code,200)
        # Add one as we a half empty page counts as an extra page
        self.assertEqual(response.context['page'].paginator.num_pages,int(len(self.item_xmen)//2+1))
        response = self.client.get(reverse('aristotle:search')+"?q=xman&page=100") # deliberatly overshoot
        self.assertEqual(response.status_code,404)

    def test_registrar_search(self):
        self.logout()
        response = self.client.post(reverse('django.contrib.auth.views.login'),
                    {'username': 'stryker', 'password': 'mutantsMustDie'})

        self.assertEqual(response.status_code,302) # logged in
        self.assertTrue(perms.user_is_registrar(self.registrar,self.ra))

        dp = models.ObjectClass.objects.create(name="deadpool",
                    description="not really an xman, no matter how much he tries",
                    workgroup=self.xmen_wg,readyToReview=False)
        dp = models.ObjectClass.objects.get(pk=dp.pk) # Un-cache
        self.assertFalse(perms.user_can_view(self.registrar,dp))
        self.assertFalse(dp.is_public())

        response = self.client.get(reverse('aristotle:search')+"?q=xman")

        self.assertFalse(dp in [x.object for x in response.context['page'].object_list])
        for i in response.context['page'].object_list:
            self.assertTrue(perms.user_can_view(self.registrar,i.object))

        response = self.client.get(reverse('aristotle:search')+"?q=deadpool")
        self.assertEqual(len(response.context['page'].object_list),0)

        dp.readyToReview = True
        dp.save()
        dp = models.ObjectClass.objects.get(pk=dp.pk) # Un-cache
        self.assertTrue(perms.user_can_view(self.registrar,dp))

        # Stryker should be able to find items that are "ready for review" in his RA only.
        response = self.client.get(reverse('aristotle:search')+"?q=deadpool")
        self.assertEqual(len(response.context['page'].object_list),1)
        self.assertEqual(response.context['page'].object_list[0].object.item,dp)
        self.assertTrue(perms.user_can_view(self.registrar,response.context['page'].object_list[0].object))

    def test_registrar_search_after_adding_new_ra_to_workgroup(self):
        self.logout()
        response = self.client.post(reverse('django.contrib.auth.views.login'),
                    {'username': 'stryker', 'password': 'mutantsMustDie'})

        steve_rogers = models.ObjectClass.objects.get(name="captainAmerica")
        self.assertFalse(perms.user_can_view(self.registrar,steve_rogers))
        steve_rogers.readyToReview = True
        steve_rogers.save()
        self.assertFalse(perms.user_can_view(self.registrar,steve_rogers))

        response = self.client.get(reverse('aristotle:search')+"?q=captainAmerica")
        self.assertEqual(len(response.context['page'].object_list),0)

        # Adding the registrars Authorities to the managing authorities of the workgroup
        # should grant them access to see item in that workgroup now.
        self.avengers_wg.registrationAuthorities.add(self.ra)
        self.avengers_wg.save()

        self.assertTrue(perms.user_can_view(self.registrar,steve_rogers))

        response = self.client.get(reverse('aristotle:search')+"?q=captainAmerica")
        self.assertEqual(len(response.context['page'].object_list),1)
        self.assertEqual(response.context['page'].object_list[0].object.item,steve_rogers)
        self.assertTrue(perms.user_can_view(self.registrar,response.context['page'].object_list[0].object))

    def test_workgroup_member_search(self):
        self.logout()
        self.viewer = User.objects.create_user('charles.xavier','charles@schoolforgiftedyoungsters.edu','equalRightsForAll')
        self.weaponx_wg = models.Workgroup.objects.create(name="WeaponX")

        response = self.client.post(reverse('django.contrib.auth.views.login'),
                    {'username': 'charles.xavier', 'password': 'equalRightsForAll'})

        self.assertEqual(response.status_code,302) # logged in

        #Charles is not in any workgroups
        self.assertFalse(perms.user_in_workgroup(self.viewer,self.xmen_wg))
        self.assertFalse(perms.user_in_workgroup(self.viewer,self.weaponx_wg))

        #Create Deadpool in Weapon X workgroup
        dp = models.ObjectClass.objects.create(name="deadpool",
                    description="not really an xman, no matter how much he tries",
                    workgroup=self.weaponx_wg,readyToReview=False)
        dp = models.ObjectClass.objects.get(pk=dp.pk) # Un-cache
        self.assertFalse(perms.user_can_view(self.viewer,dp))
        self.assertFalse(dp.is_public())

        # Charles isn't a viewer of X-men yet, so no results.
        from aristotle_mdr.forms.search import PermissionSearchQuerySet
        psqs = PermissionSearchQuerySet()
        psqs = psqs.auto_query('deadpool').apply_permission_checks(self.viewer)
        self.assertEqual(len(psqs),0)
        #response = self.client.get(reverse('aristotle:search')+"?q=deadpool")
        #self.assertEqual(len(response.context['page'].object_list),0)

        # Make viewer of XMen
        self.xmen_wg.giveRoleToUser('viewer',self.viewer)
        self.assertFalse(perms.user_can_view(self.viewer,dp))

        # Deadpool isn't an Xman yet, still no results.
        psqs = PermissionSearchQuerySet()
        psqs = psqs.auto_query('deadpool').apply_permission_checks(self.viewer)
        self.assertEqual(len(psqs),0)

        dp.workgroup = self.xmen_wg
        dp.save()
        dp = models.ObjectClass.objects.get(pk=dp.pk) # Un-cache

        # Charles is a viewer, Deadpool is in X-men, should have results now.
        psqs = PermissionSearchQuerySet()
        psqs = psqs.auto_query('deadpool').apply_permission_checks(self.viewer)
        self.assertEqual(len(psqs),1)

        response = self.client.get(reverse('aristotle:search')+"?q=deadpool")
        self.assertTrue(perms.user_can_view(self.viewer,dp))
        self.assertEqual(len(response.context['page'].object_list),1)
        self.assertEqual(response.context['page'].object_list[0].object.item,dp)

        # Take away Charles viewing rights and no results again.
        self.xmen_wg.removeRoleFromUser('viewer',self.viewer)
        psqs = PermissionSearchQuerySet()
        psqs = psqs.auto_query('deadpool').apply_permission_checks(self.viewer)
        self.assertEqual(len(psqs),0)

        response = self.client.get(reverse('aristotle:search')+"?q=deadpool")
        self.assertEqual(len(response.context['page'].object_list),0)


class TestTokenSearch(TestCase):
    def setUp(self):
        from django.test import Client

        self.client = Client()
        self.ra = models.RegistrationAuthority.objects.create(name="Kelly Act")
        self.registrar = User.objects.create_user('stryker','william.styker@weaponx.mil','mutantsMustDie')
        self.ra.giveRoleToUser('registrar',self.registrar)
        xmen = "professorX cyclops iceman angel beast phoenix wolverine storm nightcrawler"
        self.xmen_wg = models.Workgroup.objects.create(name="X Men")
        self.xmen_wg.registrationAuthorities.add(self.ra)
        self.xmen_wg.save()

        self.item_xmen = [
            models.ObjectClass.objects.create(name=t,version="0.%d.0"%(v+1),description="known x-man",workgroup=self.xmen_wg,readyToReview=True)
            for v,t in enumerate(xmen.split()) ]
        for item in self.item_xmen:
            self.ra.register(item,models.STATES.standard,self.registrar)
    def test_token_search(self):

        response = self.client.get(reverse('aristotle:search')+"?q=version:0.1.0")
        self.assertEqual(response.status_code,200)
        objs = response.context['page'].object_list
        self.assertEqual(len(objs),1)
        self.assertTrue(objs[0].object.name,"wolverine")
