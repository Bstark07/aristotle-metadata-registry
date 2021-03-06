from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse
from django.db import models, transaction
from django.db.models import Q
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver, Signal
from django.utils import timezone
from django.utils.module_loading import import_string
from django.utils.translation import ugettext_lazy as _

from model_utils.models import TimeStampedModel
from model_utils import Choices, FieldTracker
from aristotle_mdr.contrib.async_signals.utils import fire
import uuid

import reversion  # import revisions

import datetime
from ckeditor_uploader.fields import RichTextUploadingField as RichTextField
from aristotle_mdr import perms
from aristotle_mdr.utils import (
    fetch_aristotle_settings,
    fetch_metadata_apps,
    url_slugify_concept,
    url_slugify_workgroup,
    url_slugify_registration_authoritity,
    url_slugify_organization,
    strip_tags,
)
from aristotle_mdr.utils.text import truncate_words
from aristotle_mdr import comparators

from jsonfield import JSONField
from .fields import (
    ConceptForeignKey,
    ConceptManyToManyField,
    ShortTextField,
    ConvertedConstrainedImageField
)

from .managers import (
    MetadataItemManager, ConceptManager,
    ReviewRequestQuerySet, WorkgroupQuerySet,
    RegistrationAuthorityQuerySet,
    StatusQuerySet
)

import logging
logger = logging.getLogger(__name__)
logger.debug("Logging started for " + __name__)


"""
This is the core modelling for Aristotle mapping ISO/IEC 11179 classes to Python classes/Django models.

Docstrings are copied directly from the ISO/IEC 11179-3 documentation in their original form.
References to the originals is kept where possible using brackets and the dotted section numbers -
Eg. explanatory_comment (8.1.2.2.3.4)
"""


# 11179 States
# When used these MUST be used as IntegerFields to allow status comparison
STATES = Choices(
    (0, 'notprogressed', _('Not Progressed')),
    (1, 'incomplete', _('Incomplete')),
    (2, 'candidate', _('Candidate')),
    (3, 'recorded', _('Recorded')),
    (4, 'qualified', _('Qualified')),
    (5, 'standard', _('Standard')),
    (6, 'preferred', _('Preferred Standard')),
    (7, 'superseded', _('Superseded')),
    (8, 'retired', _('Retired')),
)


VERY_RECENTLY_SECONDS = 15


concept_visibility_updated = Signal(providing_args=["concept"])


class baseAristotleObject(TimeStampedModel):
    uuid = models.UUIDField(
        help_text=_("Universally-unique Identifier. Uses UUID1 as this improves uniqueness and tracking between registries"),
        unique=True, default=uuid.uuid1, editable=False, null=False
    )
    name = ShortTextField(
        help_text=_("The primary name used for human identification purposes.")
    )
    definition = RichTextField(
        _('definition'),
        help_text=_("Representation of a concept by a descriptive statement "
                    "which serves to differentiate it from related concepts. (3.2.39)")
    )
    objects = MetadataItemManager()

    class Meta:
        # So the url_name works for items we can't determine
        verbose_name = "item"
        # Can't be abstract as we need unique app wide IDs.
        abstract = True

    def was_modified_very_recently(self):
        return self.modified >= (
            timezone.now() - datetime.timedelta(seconds=VERY_RECENTLY_SECONDS)
        )

    def was_modified_recently(self):
        return self.modified >= timezone.now() - datetime.timedelta(days=1)

    was_modified_recently.admin_order_field = 'modified'  # type: ignore
    was_modified_recently.boolean = True  # type: ignore
    was_modified_recently.short_description = 'Modified recently?'  # type: ignore

    def description_stub(self):
        from django.utils.html import strip_tags
        d = strip_tags(self.definition)
        if len(d) > 150:
            d = d[0:150] + "..."
        return d

    def __str__(self):
        return "{name}".format(name=self.name)

    # Defined so we can access it during templates.
    @classmethod
    def get_verbose_name(cls):
        return cls._meta.verbose_name.title()

    @classmethod
    def get_verbose_name_plural(cls):
        return cls._meta.verbose_name_plural.title()

    def can_edit(self, user):
        # This should always be overridden
        raise NotImplementedError  # pragma: no cover

    def can_view(self, user):
        # This should always be overridden
        raise NotImplementedError  # pragma: no cover

    @classmethod
    def meta(self):
        # I know what I'm doing, get out the way.
        return self._meta


class unmanagedObject(baseAristotleObject):
    class Meta:
        abstract = True

    def can_edit(self, user):
        return user.is_superuser

    def can_view(self, user):
        return True

    @property
    def item(self):
        return self


class aristotleComponent(models.Model):
    class Meta:
        abstract = True

    ordering_field = 'order'

    def can_edit(self, user):
        return self.parentItem.can_edit(user)

    def can_view(self, user):
        return self.parentItem.can_view(user)


class registryGroup(unmanagedObject):
    managers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="%(class)s_manager_in",
        verbose_name=_('Managers')
    )

    class Meta:
        abstract = True

    def can_edit(self, user):
        return user.is_superuser or self.managers.filter(pk=user.pk).exists()

    @property
    def help_name(self):
        return self._meta.model_name

    def list_roles_for_user(self, user):
        # This should always be overridden
        raise NotImplementedError  # pragma: no cover


class Organization(registryGroup):
    """
    6.3.6 - Organization is a class each instance of which models an organization (3.2.90),
    a unique framework of authority within which individuals (3.2.65) act, or are designated to act,
    towards some purpose.
    """
    template = "aristotle_mdr/organization/organization.html"
    uri = models.URLField(  # 6.3.6.2.5
        blank=True, null=True,
        help_text="uri for Organization"
    )

    def promote_to_registration_authority(self):
        ra = RegistrationAuthority(organization_ptr=self)
        ra.save()
        return ra

    def get_absolute_url(self):
        return url_slugify_organization(self)


RA_ACTIVE_CHOICES = Choices(
    (0, 'active', _('Active & Visible')),
    (1, 'inactive', _('Inactive & Visible')),
    (2, 'hidden', _('Inactive & Hidden'))
)


class RegistrationAuthority(Organization):
    """
    8.1.2.5 - Registration_Authority class

    Registration_Authority is a class each instance of which models a registration authority (3.2.109),
    an organization (3.2.90) responsible for maintaining a register (3.2.104).

    A registration authority may register many administered items (3.2.2) as shown by the Registration
    (8.1.5.1) association class.
    """
    objects = RegistrationAuthorityQuerySet.as_manager()
    template = "aristotle_mdr/organization/registrationAuthority.html"
    active = models.IntegerField(
        choices=RA_ACTIVE_CHOICES,
        default=RA_ACTIVE_CHOICES.active,
        help_text=_('Setting this to Inactive will disable all further registration actions')
    )
    locked_state = models.IntegerField(
        choices=STATES,
        default=STATES.candidate
    )
    public_state = models.IntegerField(
        choices=STATES,
        default=STATES.recorded
    )

    registrars = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='registrar_in',
        verbose_name=_('Registrars')
    )

    # The below text fields allow for brief descriptions of the context of each
    # state for a particular Registration Authority
    # For example:
    # For a particular Registration Authority standard may mean"
    #   "Approved by a simple majority of the standing council of metadata
    #    standardisation"
    # While "Preferred Standard" may mean:
    #   "Approved by a two-thirds majority of the standing council of metadata
    #    standardisation"

    notprogressed = models.TextField(blank=True)
    incomplete = models.TextField(blank=True)
    candidate = models.TextField(blank=True)
    recorded = models.TextField(blank=True)
    qualified = models.TextField(blank=True)
    standard = models.TextField(blank=True)
    preferred = models.TextField(blank=True)
    superseded = models.TextField(blank=True)
    retired = models.TextField(blank=True)

    tracker = FieldTracker()

    class Meta:
        verbose_name_plural = _("Registration Authorities")

    roles = {
        'registrar': _("Registrar"),
        'manager': _("Manager")
    }

    def get_absolute_url(self):
        return url_slugify_registration_authoritity(self)

    def can_view(self, user):
        return True

    @property
    def unlocked_states(self):
        return range(STATES.notprogressed, self.locked_state)

    @property
    def locked_states(self):
        return range(self.locked_state, self.public_state)

    @property
    def public_states(self):
        return range(self.public_state, STATES.retired + 1)

    def statusDescriptions(self):
        descriptions = [
            self.notprogressed,
            self.incomplete,
            self.candidate,
            self.recorded,
            self.qualified,
            self.standard,
            self.preferred,
            self.superseded,
            self.retired
        ]

        unlocked = [
            (i, STATES[i], descriptions[i]) for i in self.unlocked_states
        ]
        locked = [
            (i, STATES[i], descriptions[i]) for i in self.locked_states
        ]
        public = [
            (i, STATES[i], descriptions[i]) for i in self.public_states
        ]

        return (
            ('unlocked', unlocked),
            ('locked', locked),
            ('public', public)
        )

    def register_many(self, items, state, user, *args, **kwargs):
        # Change the registration status of many items
        # the items argument should be a queryset

        revision_message = _("Bulk registration of %i items\n") % (items.count())

        revision_message = revision_message + kwargs.get('changeDetails', "")
        seen_items = {'success': [], 'failed': []}

        with transaction.atomic(), reversion.revisions.create_revision():
            reversion.revisions.set_user(user)
            reversion.revisions.set_comment(revision_message)

            # can use bulk_create here when background reindex is setup
            for child_item in items:
                if perms.user_can_change_status(user, child_item):
                    self._register(
                        child_item, state, user, *args, **kwargs
                    )
                    seen_items['success'].append(child_item.id)
                else:
                    seen_items['failed'].append(child_item.id)

        return seen_items

    def cascaded_register(self, item, state, user, *args, **kwargs):
        if not perms.user_can_change_status(user, item):
            # Return a failure as this item isn't allowed
            return {'success': [], 'failed': [item] + item.registry_cascade_items}

        revision_message = _(
            "Cascade registration of item '%(name)s' (id:%(iid)s)\n"
        ) % {
            'name': item.name,
            'iid': item.id
        }
        revision_message = revision_message + kwargs.get('changeDetails', "")
        seen_items = {'success': [], 'failed': []}

        with transaction.atomic(), reversion.revisions.create_revision():
            reversion.revisions.set_user(user)
            reversion.revisions.set_comment(revision_message)

            for child_item in [item] + item.registry_cascade_items:
                self._register(
                    child_item, state, user, *args, **kwargs
                )
                seen_items['success'] = seen_items['success'] + [child_item]
        return seen_items

    def register(self, item, state, user, *args, **kwargs):
        if not perms.user_can_change_status(user, item):
            # Return a failure as this item isn't allowed
            return {'success': [], 'failed': [item]}

        revision_message = kwargs.get('changeDetails', "")
        with transaction.atomic(), reversion.revisions.create_revision():
            reversion.revisions.set_user(user)
            reversion.revisions.set_comment(revision_message)
            self._register(item, state, user, *args, **kwargs)

        return {'success': [item], 'failed': []}

    def _register(self, item, state, user, *args, **kwargs):
        if self.active is RA_ACTIVE_CHOICES.active:
            changeDetails = kwargs.get('changeDetails', "")
            # If registrationDate is None (like from a form), override it with
            # todays date.
            registrationDate = kwargs.get('registrationDate', None) \
                or timezone.now().date()
            until_date = kwargs.get('until_date', None)

            Status.objects.create(
                concept=item,
                registrationAuthority=self,
                registrationDate=registrationDate,
                state=state,
                changeDetails=changeDetails,
                until_date=until_date
            )

    def list_roles_for_user(self, user):
        roles = []
        if user in self.managers.all():
            roles.append("manager")
        if user in self.registrars.all():
            roles.append("registrar")
        return roles

    def giveRoleToUser(self, role, user):
        if role == 'registrar':
            self.registrars.add(user)
        if role == "manager":
            self.managers.add(user)

    def removeRoleFromUser(self, role, user):
        if role == 'registrar':
            self.registrars.remove(user)
        if role == "manager":
            self.managers.remove(user)

    @property
    def members(self):
        return (self.managers.all() | self.registrars.all()).distinct()

    @property
    def is_active(self):
        return self.active == RA_ACTIVE_CHOICES.active

    @property
    def is_visible(self):
        return not self.active == RA_ACTIVE_CHOICES.hidden


@receiver(post_save, sender=RegistrationAuthority)
def update_registration_authority_states(sender, instance, created, **kwargs):
    if not created:
        if instance.tracker.has_changed('public_state') \
           or instance.tracker.has_changed('locked_state'):
            message = (
                "Registration '{ra}' changed its public or locked status "
                "level, items registered by this authority may have stale "
                "visiblity states and need to be manually updated."
            ).format(ra=instance.name)
            logger.critical(message)


class Workgroup(registryGroup):
    """
    A workgroup is a collection of associated users given control to work on a
    specific piece of work. Usually this work will be the creation of a
    specific collection of objects, such as data elements, for a specific
    topic.

    Workgroup owners may choose to 'archive' a workgroup. All content remains
    visible, but the workgroup is hidden in lists and new items cannot be
    created in that workgroup.
    """
    template = "aristotle_mdr/workgroup.html"
    objects = WorkgroupQuerySet.as_manager()
    archived = models.BooleanField(
        default=False,
        help_text=_("Archived workgroups can no longer have new items or "
                    "discussions created within them."),
        verbose_name=_('Archived'),
    )

    viewers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='viewer_in',
        verbose_name=_('Viewers')
    )
    submitters = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='submitter_in',
        verbose_name=_('Submitters')
    )
    stewards = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='steward_in',
        verbose_name=_('Stewards')
    )

    roles = {
        'submitter': _("Submitter"),
        'viewer': _("Viewer"),
        'steward': _("Steward"),
        'manager': _("Manager")
    }

    tracker = FieldTracker()

    def get_absolute_url(self):
        return url_slugify_workgroup(self)

    @property
    def members(self):
        return (
            self.viewers.all() | self.submitters.all() |
            self.stewards.all() | self.managers.all()
        ).distinct().order_by('full_name')

    def can_view(self, user):
        return self.members.filter(pk=user.pk).exists()

    @property
    def classedItems(self):
        # Convenience class as we can't call functions in templates
        return self.items.select_subclasses()

    def list_roles_for_user(self, user):
        roles = []
        if user in self.managers.all():
            roles.append("manager")
        if user in self.viewers.all():
            roles.append("viewer")
        if user in self.submitters.all():
            roles.append("submitter")
        if user in self.stewards.all():
            roles.append("steward")
        return roles

    def giveRoleToUser(self, role, user):
        if role == "manager":
            self.managers.add(user)
        if role == "viewer":
            self.viewers.add(user)
        if role == "submitter":
            self.submitters.add(user)
        if role == "steward":
            self.stewards.add(user)
        self.save()

    def removeRoleFromUser(self, role, user):
        if role == "manager":
            self.managers.remove(user)
        if role == "viewer":
            self.viewers.remove(user)
        if role == "submitter":
            self.submitters.remove(user)
        if role == "steward":
            self.stewards.remove(user)
        self.save()

    def removeUser(self, user):
        self.viewers.remove(user)
        self.submitters.remove(user)
        self.stewards.remove(user)
        self.managers.remove(user)


class discussionAbstract(TimeStampedModel):
    body = models.TextField()
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True
    )

    class Meta:
        abstract = True

    @property
    def edited(self):
        return self.created != self.modified


class DiscussionPost(discussionAbstract):
    workgroup = models.ForeignKey(Workgroup, related_name='discussions')
    title = models.CharField(max_length=256)
    relatedItems = models.ManyToManyField(
        '_concept',
        blank=True,
        related_name='relatedDiscussions',
    )
    closed = models.BooleanField(default=False)

    class Meta:
        ordering = ['-modified']

    @property
    def active(self):
        return not self.closed

    def get_absolute_url(self):
        return reverse(
            "aristotle:discussionsPost",
            args=[self.pk]
        )


class DiscussionComment(discussionAbstract):
    post = models.ForeignKey(DiscussionPost, related_name='comments')

    class Meta:
        ordering = ['created']


# class ReferenceDocument(models.Model):
#     url = models.URLField()
#     definition = models.TextField()
#     object = models.ForeignKey(managedObject)


class _concept(baseAristotleObject):
    """
    9.1.2.1 - Concept class
    Concept is a class each instance of which models a concept (3.2.18),
    a unit of knowledge created by a unique combination of characteristics (3.2.14).
    A concept is independent of representation.

    This is the base concrete class that ``Status`` items attach to, and to
    which collection objects refer to. It is not marked abstract in the Django
    Meta class, and **must not be inherited from**. It has relatively few
    fields and is a convenience class to link with in relationships.
    """
    objects = ConceptManager()
    template = "aristotle_mdr/concepts/managedContent.html"
    list_details_template = "aristotle_mdr/helpers/concept_list_details.html"

    workgroup = models.ForeignKey(Workgroup, related_name="items", null=True, blank=True)
    submitter = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="created_items",
        null=True, blank=True,
        help_text=_('This is the person who first created an item. Users can always see items they made.'))
    # We will query on these, so want them cached with the items themselves
    # To be usable these must be updated when statuses are changed
    _is_public = models.BooleanField(default=False)
    _is_locked = models.BooleanField(default=False)

    version = models.CharField(max_length=20, blank=True)
    references = RichTextField(blank=True)
    origin_URI = models.URLField(
        blank=True,
        help_text=_("If imported, the original location of the item")
    )
    origin = RichTextField(
        help_text=_("The source (e.g. document, project, discipline or model) for the item (8.1.2.2.3.5)"),
        blank=True
    )
    comments = RichTextField(
        help_text=_("Descriptive comments about the metadata item (8.1.2.2.3.4)"),
        blank=True
    )
    submitting_organisation = ShortTextField(blank=True)
    responsible_organisation = ShortTextField(blank=True)

    superseded_by_items = ConceptManyToManyField(  # 11.5.3.4
        'self',
        through='SupersedeRelationship',
        related_name="superseded_items",
        # blank=True,
        through_fields=('older_item', 'newer_item'),
        symmetrical=False,
        # help_text=_("")
    )

    tracker = FieldTracker()

    comparator = comparators.Comparator
    edit_page_excludes: list = []
    admin_page_excludes: list = []
    registerable = True

    class Meta:
        # So the url_name works for items we can't determine.
        verbose_name = "item"

    @property
    def non_cached_fields_changed(self):
        changed = self.tracker.changed()
        changed.pop('_is_public', False)
        changed.pop('_is_locked', False)
        return len(changed.keys()) > 0

    @property
    def changed_fields(self):
        changed = self.tracker.changed()
        changed.pop('_is_public', False)
        changed.pop('_is_locked', False)
        return changed.keys()

    def can_edit(self, user):
        return _concept.objects.filter(pk=self.pk).editable(user).exists()

    def can_view(self, user):
        return _concept.objects.filter(pk=self.pk).visible(user).exists()

    @property
    def item(self):
        """
        Performs a lookup using ``model_utils.managers.InheritanceManager`` to
        find the subclassed item.
        """
        return _concept.objects.get_subclass(pk=self.pk)

    @property
    def concept(self):
        """
        Returns the parent _concept that an item is built on.
        If the item type is _concept, return itself.
        """
        return getattr(self, '_concept_ptr', self)

    @property
    def short_definition(self):
        stripped = strip_tags(self.definition)
        return truncate_words(stripped, 20)

    @classmethod
    def get_autocomplete_name(self):
        return 'Autocomplete' + "".join(
            self._meta.verbose_name.title().split()
        )

    @staticmethod
    def autocomplete_search_fields(self):
        return ("name__icontains",)

    def get_absolute_url(self):
        return url_slugify_concept(self)

    @property
    def registry_cascade_items(self):
        """
        This returns the items that can be registered along with the this item.
        If a subclass of _concept defines this method, then when an instance
        of that class is registered using a cascading method then that
        instance, all instances returned by this method will all recieve the
        same registration status.

        Reimplementations of this MUST return iterables.
        """
        return []

    @property
    def is_registered(self):
        return self.statuses.count() > 0

    @property
    def is_superseded(self):
        return self.statuses.filter(state=STATES.superseded).count() > 0 and all(
            STATES.superseded == status.state for status in self.statuses.all()
        ) and self.superseded_by_items_relation_set.count() > 0

    @property
    def is_retired(self):
        return all(
            STATES.retired == status.state for status in self.statuses.all()
        ) and self.statuses.count() > 0

    @property
    def favourited_by(self):
        from django.contrib.auth import get_user_model
        user_model = get_user_model()
        return user_model.objects.filter(
            profile__tags__favourites__item=self
        ).distinct()

    def check_is_public(self, when=timezone.now()):
        """
            A concept is public if any registration authority
            has advanced it to a public state in that RA.
        """
        statuses = self.statuses.all()
        statuses = self.current_statuses(qs=statuses, when=when)
        pub_state = True in [
            s.state >= s.registrationAuthority.public_state for s in statuses
        ]

        q = Q()
        extra = False
        extra_q = fetch_aristotle_settings().get('EXTRA_CONCEPT_QUERYSETS', {}).get('public', None)
        if extra_q:
            for func in extra_q:
                q |= import_string(func)()
            extra = self.__class__.objects.filter(pk=self.pk).filter(q).exists()
        return pub_state or extra

    def is_public(self):
        return self._is_public
    is_public.boolean = True  # type: ignore
    is_public.short_description = 'Public'  # type: ignore

    def check_is_locked(self, when=timezone.now()):
        """
        A concept is locked if any registration authority
        has advanced it to a locked state in that RA.
        """
        statuses = self.statuses.all()
        statuses = self.current_statuses(qs=statuses, when=when)
        return True in [
            s.state >= s.registrationAuthority.locked_state for s in statuses
        ]

    def is_locked(self):
        return self._is_locked

    is_locked.boolean = True  # type: ignore
    is_locked.short_description = 'Locked'  # type: ignore

    def recache_states(self):
        self._is_public = self.check_is_public()
        self._is_locked = self.check_is_locked()
        self.save()
        concept_visibility_updated.send(sender=self.__class__, concept=self)

    def current_statuses(self, qs=None, when=timezone.now()):
        if qs is None:
            qs = self.statuses.all()

        return qs.current(when)

    def get_download_items(self):
        """
        When downloading a concept, extra items can be included for download by
        overriding the ``get_download_items`` method on your item. By default
        this returns an empty list, but can be modified to include any number of
        items that inherit from ``_concept``.

        When overriding, each entry in the list must be a two item tuple, with
        the first entry being the python class of the item or items being
        included, and the second being the queryset of items to include.
        """
        return []


class concept(_concept):
    """
    This is an abstract class that all items that should behave like a 11179
    Concept **must inherit from**. This model includes the definitions for many
    long and optional text fields and the self-referential ``superseded_by``
    field. It is not possible to include this model in a ``ForeignKey`` or
    ``ManyToManyField``.
    """
    objects = ConceptManager()

    class Meta:
        abstract = True

    @property
    def help_name(self):
        return self._meta.model_name

    @property
    def item(self):
        """
        Return self, because we already have the correct item.
        """
        return self


class SupersedeRelationship(TimeStampedModel):
    older_item = ConceptForeignKey(
        _concept,
        related_name='superseded_by_items_relation_set',
    )
    newer_item = ConceptForeignKey(
        _concept,
        related_name='superseded_items_relation_set',
    )
    registration_authority = models.ForeignKey(RegistrationAuthority)
    message = models.TextField(blank=True, null=True)
    date_effective = models.DateField(
        _('Date effective'),
        help_text=_("The date the superseding relationship became effective."),
        blank=True, null=True
    )


REVIEW_STATES = Choices(
    (0, 'submitted', _('Submitted')),
    (5, 'cancelled', _('Cancelled')),
    (10, 'accepted', _('Accepted')),
    (15, 'rejected', _('Rejected')),
)


class ReviewRequest(TimeStampedModel):
    objects = ReviewRequestQuerySet.as_manager()
    concepts = models.ManyToManyField(_concept, related_name="review_requests")
    registration_authority = models.ForeignKey(
        RegistrationAuthority,
        help_text=_("The registration authority the requester wishes to endorse the metadata item")
    )
    requester = models.ForeignKey(settings.AUTH_USER_MODEL, help_text=_("The user requesting a review"), related_name='requested_reviews')
    message = models.TextField(blank=True, null=True, help_text=_("An optional message accompanying a request, this will accompany the approved registration status"))
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, help_text=_("The user performing a review"), related_name='reviewed_requests')
    response = models.TextField(blank=True, null=True, help_text=_("An optional message responding to a request"))
    status = models.IntegerField(
        choices=REVIEW_STATES,
        default=REVIEW_STATES.submitted,
        help_text=_('Status of a review')
    )
    state = models.IntegerField(
        choices=STATES,
        help_text=_("The state at which a user wishes a metadata item to be endorsed")
    )
    registration_date = models.DateField(
        _('Date registration effective'),
        help_text=_("date and time you want the metadata to be registered from")
    )
    cascade_registration = models.IntegerField(
        choices=[(0, _('No')), (1, _('Yes'))],
        default=0,
        help_text=_("Update the registration of associated items")
    )

    def get_absolute_url(self):
        return reverse(
            "aristotle:userReviewDetails",
            kwargs={'review_id': self.pk}
        )

    def __str__(self):
        return "Review of {count} items as {state} in {ra} registraion authority".format(
            count=self.concepts.count(),
            state=self.get_state_display(),
            ra=self.registration_authority,
        )


class Status(TimeStampedModel):
    """
    8.1.2.6 - Registration_State class
    A Registration_State is a collection of information about the Registration (8.1.5.1) of an Administered Item (8.1.2.2).
    The attributes of the Registration_State class are summarized here and specified more formally in 8.1.2.6.2.
    """
    objects = StatusQuerySet.as_manager()
    concept = ConceptForeignKey(_concept, related_name="statuses")
    registrationAuthority = models.ForeignKey(RegistrationAuthority)
    changeDetails = models.TextField(blank=True, null=True)
    state = models.IntegerField(
        choices=STATES,
        default=STATES.incomplete,
        help_text=_("Designation (3.2.51) of the status in the registration life-cycle of an Administered_Item")
    )
    # TODO: Below should be changed to 'effective_date' to match ISO IEC
    # 11179-6 (Section 8.1.2.6.2.2)
    registrationDate = models.DateField(
        _('Date registration effective'),
        help_text=_("date and time an Administered_Item became/becomes available to registry users")
    )
    until_date = models.DateField(
        _('Date registration expires'),
        blank=True,
        null=True,
        help_text=_("date and time the Registration of an Administered_Item by a Registration_Authority in a registry is no longer effective")
    )
    tracker = FieldTracker()

    class Meta:
        verbose_name_plural = "Statuses"

    @property
    def state_name(self):
        return STATES[self.state]

    def __str__(self):
        return "{obj} is {stat} for {ra} on {date} - {desc}".format(
            obj=self.concept.name,
            stat=self.state_name,
            ra=self.registrationAuthority,
            desc=self.changeDetails,
            date=self.registrationDate
        )


def recache_concept_states(sender, instance, *args, **kwargs):
    instance.concept.recache_states()


post_save.connect(recache_concept_states, sender=Status)
post_delete.connect(recache_concept_states, sender=Status)


class ObjectClass(concept):
    """
    Set of ideas, abstractions or things in the real world that are
    identified with explicit boundaries and meaning and whose properties and
    behaviour follow the same rules (3.2.88)
    """
    template = "aristotle_mdr/concepts/objectClass.html"

    class Meta:
        verbose_name_plural = "Object Classes"


class Property(concept):
    """
    Quality common to all members of an :model:`aristotle_mdr.ObjectClass`
    (3.2.100)
    """
    template = "aristotle_mdr/concepts/property.html"

    class Meta:
        verbose_name_plural = "Properties"


class Measure(unmanagedObject):
    """
    Measure_Class is a class each instance of which models a measure class (3.2.72),
    a set of equivalent units of measure (3.2.138) that may be shared across multiple
    dimensionalities (3.2.58). Measure_Class allows a grouping of units of measure to
    be specified once, and reused by multiple dimensionalities.

    NB. A measure is not defined as a concept in ISO 11179 (11.4.2.2)
    """
    template = "aristotle_mdr/unmanaged/measure.html"


class UnitOfMeasure(concept):
    """
    actual units in which the associated values are measured
    :model:`aristotle_mdr.ValueDomain` (3.2.138)
    """

    class Meta:
        verbose_name_plural = "Units Of Measure"

    template = "aristotle_mdr/concepts/unitOfMeasure.html"
    list_details_template = "aristotle_mdr/concepts/list_details/unit_of_measure.html"
    measure = models.ForeignKey(Measure, blank=True, null=True)
    symbol = models.CharField(max_length=20, blank=True)


class DataType(concept):
    """
    set of distinct values, characterized by properties of those values and
    by operations on those values (3.1.9)
    """
    template = "aristotle_mdr/concepts/dataType.html"


class ConceptualDomain(concept):
    """
    Concept that expresses its description or valid instance meanings (3.2.21)
    """

    # Implementation note: Since a Conceptual domain "must be either one or
    # both an Enumerated Conceptual or a Described_Conceptual_Domain" there is
    # no reason to model them separately.

    template = "aristotle_mdr/concepts/conceptualDomain.html"
    description = models.TextField(
        _('description'),
        blank=True,
        help_text=_(
            ('Description or specification of a rule, reference, or '
             'range for a set of all value meanings for a Conceptual Domain')
        )
    )
    serialize_weak_entities = [
        ('value_meaning', 'valuemeaning_set'),
    ]


class ValueMeaning(aristotleComponent):
    """
    Value_Meaning is a class each instance of which models a value meaning (3.2.141),
    which provides semantic content of a possible value (11.3.2.3.2).
    """
    class Meta:
        ordering = ['order']

    name = models.CharField(  # 3.2.141
        max_length=255,
        help_text=_('The semantic content of a possible value (3.2.141)')
    )
    definition = models.TextField(
        null=True, blank=True,
        help_text=_('The semantic definition of a possible value')
    )
    conceptual_domain = ConceptForeignKey(
        ConceptualDomain,
        verbose_name='Conceptual Domain'
    )
    order = models.PositiveSmallIntegerField("Position")
    start_date = models.DateField(
        blank=True,
        null=True,
        help_text=_('Date at which the value meaning became valid')
    )
    end_date = models.DateField(
        blank=True,
        null=True,
        help_text=_('Date at which the value meaning ceased to be valid')
    )

    def __str__(self):
        return "%s: %s - %s" % (
            self.conceptual_domain.name,
            self.name,
            self.definition
        )

    @property
    def parentItem(self):
        return self.conceptual_domain

    @property
    def parentItemId(self):
        return self.conceptual_domain_id


class ValueDomain(concept):
    """
    Value_Domain is a class each instance of which models a value domain (3.2.140),
    a set of permissible values (3.2.96) (11.3.2.5).
    """

    # Implementation note: Since a Value domain "must be either one or
    # both an Enumerated Valued or a Described_Value_Domain" there is
    # no reason to model them separately.

    template = "aristotle_mdr/concepts/valueDomain.html"
    list_details_template = "aristotle_mdr/concepts/list_details/value_domain.html"
    comparator = comparators.ValueDomainComparator
    serialize_weak_entities = [
        ('permissible_values', 'permissiblevalue_set'),
        ('supplementary_values', 'supplementaryvalue_set'),
    ]

    data_type = ConceptForeignKey(  # 11.3.2.5.2.1
        DataType,
        blank=True,
        null=True,
        help_text=_('Datatype used in a Value Domain'),
        verbose_name='Data Type'
    )
    format = models.CharField(  # 11.3.2.5.2.1
        max_length=100,
        blank=True,
        null=True,
        help_text=_('template for the structure of the presentation of the value(s)')
    )
    maximum_length = models.PositiveIntegerField(  # 11.3.2.5.2.3
        blank=True,
        null=True,
        help_text=_('maximum number of characters available to represent the Data Element value')
        )
    unit_of_measure = ConceptForeignKey(  # 11.3.2.5.2.3
        UnitOfMeasure,
        blank=True,
        null=True,
        help_text=_('Unit of Measure used in a Value Domain'),
        verbose_name='Unit Of Measure'
    )
    conceptual_domain = ConceptForeignKey(
        ConceptualDomain,
        blank=True,
        null=True,
        help_text=_('The Conceptual Domain that this Value Domain which provides representation.'),
        verbose_name='Conceptual Domain'
    )
    description = models.TextField(
        _('description'),
        blank=True,
        help_text=('Description or specification of a rule, reference, or '
                   'range for a set of all values for a Value Domain.')
    )

    # Below is a dirty, dirty hack that came from re-designing permissible
    # values

    # TODO: Fix references to permissible and supplementary values
    @property
    def permissibleValues(self):
        return self.permissiblevalue_set.all()

    @property
    def supplementaryValues(self):
        return self.supplementaryvalue_set.all()


class AbstractValue(aristotleComponent):
    """
    Implementation note: Not the best name, but there will be times to
    subclass a "value" when its not just a permissible value.
    """

    class Meta:
        abstract = True
        ordering = ['order']
    value = ShortTextField(  # 11.3.2.7.2.1 - Renamed from permitted value for abstracts
        help_text=_("the actual value of the Value")
    )
    meaning = ShortTextField(  # 11.3.2.7.1
        help_text=_("A textual designation of a value, where a relation to a Value meaning doesn't exist")
    )
    value_meaning = models.ForeignKey(  # 11.3.2.7.1
        ValueMeaning,
        blank=True,
        null=True,
        help_text=_('A reference to the value meaning that this designation relates to')
    )
    # Below will generate exactly the same related name as django, but reversion-compare
    # needs an explicit related_name for some actions.
    valueDomain = ConceptForeignKey(
        ValueDomain,
        related_name="%(class)s_set",
        help_text=_("Enumerated Value Domain that this value meaning relates to"),
        verbose_name='Value Domain'
    )
    order = models.PositiveSmallIntegerField("Position")
    start_date = models.DateField(
        blank=True,
        null=True,
        help_text=_('Date at which the value became valid')
    )
    end_date = models.DateField(
        blank=True,
        null=True,
        help_text=_('Date at which the value ceased to be valid')
    )

    def __str__(self):
        return "%s: %s - %s" % (
            self.valueDomain.name,
            self.value,
            self.meaning
        )

    @property
    def parentItem(self):
        return self.valueDomain

    @property
    def parentItemId(self):
        return self.valueDomain_id


class PermissibleValue(AbstractValue):
    """
    Permissible Value is a class each instance of which models a permissible value (3.2.96),
    the designation (3.2.51) of a value meaning (3.2.141).
    """
    pass


class SupplementaryValue(AbstractValue):
    pass


class DataElementConcept(concept):
    """
    Data Element Concept is a class each instance of which models a data element concept (3.2.29).
    A data element concept is a specification of a concept (3.2.18) independent of any particular representation.
    A data element concept can be represented in the form of a data element (3.2.28).

    Concept that is an association of a :model:`aristotle_mdr.Property`
    with an :model:`aristotle_mdr.ObjectClass` (3.2.29) (11.2.2.3)
    """

    # Redefine in this context as we need 'property' for the 11179 terminology.
    property_ = property
    template = "aristotle_mdr/concepts/dataElementConcept.html"
    objectClass = ConceptForeignKey(  # 11.2.3.3
        ObjectClass, blank=True, null=True,
        help_text=_('references an Object_Class that is part of the specification of the Data_Element_Concept'),
        verbose_name='Object Class'
    )
    property = ConceptForeignKey(  # 11.2.3.1
        Property, blank=True, null=True,
        help_text=_('references a Property that is part of the specification of the Data_Element_Concept'),
        verbose_name='Property'
    )
    conceptualDomain = ConceptForeignKey(  # 11.2.3.2
        ConceptualDomain, blank=True, null=True,
        help_text=_('references a Conceptual_Domain that is part of the specification of the Data_Element_Concept'),
        verbose_name='Conceptual Domain'
    )

    @property_
    def registry_cascade_items(self):
        out = []
        if self.objectClass:
            out.append(self.objectClass)
        if self.property:
            out.append(self.property)
        return out

    def get_download_items(self):
        return [
            (ObjectClass, ObjectClass.objects.filter(dataelementconcept=self)),
            (Property, Property.objects.filter(dataelementconcept=self)),
        ]


# Yes this name looks bad - blame 11179:3:2013 for renaming "administered item"
# to "concept".
class DataElement(concept):
    """
    Unit of data that is considered in context to be indivisible (3.2.28)"""

    template = "aristotle_mdr/concepts/dataElement.html"
    list_details_template = "aristotle_mdr/concepts/list_details/data_element.html"

    dataElementConcept = ConceptForeignKey(  # 11.5.3.2
        DataElementConcept,
        verbose_name="Data Element Concept",
        blank=True,
        null=True,
        help_text=_("binds with a Value_Domain that describes a set of possible values that may be recorded in an instance of the Data_Element")
    )
    valueDomain = ConceptForeignKey(  # 11.5.3.1
        ValueDomain,
        verbose_name="Value Domain",
        blank=True,
        null=True,
        help_text=_("binds with a Data_Element_Concept that provides the meaning for the Data_Element")
    )

    @property
    def registry_cascade_items(self):
        out = []
        if self.valueDomain:
            out.append(self.valueDomain)
        if self.dataElementConcept:
            out.append(self.dataElementConcept)
            out += self.dataElementConcept.registry_cascade_items
        return out

    def get_download_items(self):
        return [
            (ObjectClass, ObjectClass.objects.filter(dataelementconcept=self.dataElementConcept)),
            (Property, Property.objects.filter(dataelementconcept=self.dataElementConcept)),
            (DataElementConcept, DataElementConcept.objects.filter(dataelement=self)),
            (ValueDomain, ValueDomain.objects.filter(dataelement=self)),
        ]


class DataElementDerivation(concept):
    r"""
    Application of a derivation rule to one or more
    input :model:`aristotle_mdr.DataElement`\s to derive one or more
    output :model:`aristotle_mdr.DataElement`\s (3.2.33)
    """

    edit_page_excludes = ['inputs', 'derives']

    derives = ConceptManyToManyField(  # 11.5.3.5
        DataElement,
        through='DedDerivesThrough',
        related_name="derived_from",
        blank=True,
        null=True,
        help_text=_("binds with one or more output Data_Elements that are the result of the application of the Data_Element_Derivation.")
    )
    inputs = ConceptManyToManyField(  # 11.5.3.4
        DataElement,
        through='DedInputsThrough',
        related_name="input_to_derivation",
        blank=True,
        help_text=_("binds one or more input Data_Element(s) with a Data_Element_Derivation.")
    )
    derivation_rule = models.TextField(
        blank=True,
        help_text=_("text of a specification of a data element Derivation_Rule")
    )


class DedBaseThrough(models.Model):
    """
    Abstract Class for Data Element Derivation Manay to Many through tables with ordering
    """

    data_element_derivation = models.ForeignKey(DataElementDerivation, on_delete=models.CASCADE)
    data_element = models.ForeignKey(DataElement, on_delete=models.CASCADE)
    order = models.PositiveSmallIntegerField("Position")

    class Meta:
        abstract = True
        ordering = ['order']


class DedDerivesThrough(DedBaseThrough):
    pass


class DedInputsThrough(DedBaseThrough):
    pass


# Create a 1-1 user profile so we don't need to extend user
# Thanks to http://stackoverflow.com/a/965883/764357
class PossumProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        related_name='profile'
    )
    savedActiveWorkgroup = models.ForeignKey(
        Workgroup,
        blank=True,
        null=True
    )
    profilePictureWidth = models.IntegerField(
        blank=True,
        null=True
    )
    profilePictureHeight = models.IntegerField(
        blank=True,
        null=True
    )
    profilePicture = ConvertedConstrainedImageField(
        blank=True,
        null=True,
        height_field='profilePictureHeight',
        width_field='profilePictureWidth',
        max_upload_size=((1024**2) * 10),  # 10 MB
        content_types=['image/jpg', 'image/png', 'image/bmp', 'image/jpeg'],
        js_checker=True
    )

    # Override save for inline creation of objects.
    # http://stackoverflow.com/questions/2813189/django-userprofile-with-unique-foreign-key-in-django-admin
    def save(self, *args, **kwargs):
        try:
            existing = PossumProfile.objects.get(user=self.user)
            self.id = existing.id  # Force update instead of insert.
        except PossumProfile.DoesNotExist:  # pragma: no cover
            pass

        models.Model.save(self, *args, **kwargs)

    @property
    def activeWorkgroup(self):
        return self.savedActiveWorkgroup or None

    @property
    def workgroups(self):
        if self.user.is_superuser:
            return Workgroup.objects.all()
        else:
            return (
                self.user.viewer_in.all() |
                self.user.submitter_in.all() |
                self.user.steward_in.all() |
                self.user.workgroup_manager_in.all()
            ).distinct()

    @property
    def myWorkgroups(self):
        return (
            self.user.viewer_in.all() |
            self.user.submitter_in.all() |
            self.user.steward_in.all() |
            self.user.workgroup_manager_in.all()
        ).filter(archived=False).distinct()

    @property
    def myWorkgroupCount(self):
        # When only a count is required, querying with union is much faster
        vi = self.user.viewer_in.filter(archived=False)
        si = self.user.submitter_in.filter(archived=False)
        sti = self.user.steward_in.filter(archived=False)
        mi = self.user.workgroup_manager_in.filter(archived=False)
        return vi.union(si).union(sti).union(mi).count()

    @property
    def mySandboxContent(self):
        from aristotle_mdr.contrib.reviews.const import REVIEW_STATES
        return _concept.objects.filter(
            Q(
                submitter=self.user,
                statuses__isnull=True
            ) & Q(
                Q(rr_review_requests__isnull=True) | Q(rr_review_requests__status=REVIEW_STATES.revoked)
            )
        )

    @property
    def editable_workgroups(self):
        if self.user.is_superuser:
            return Workgroup.objects.all()
        else:
            return (
                self.user.submitter_in.all() |
                self.user.steward_in.all()
            ).distinct().filter(archived=False)

    @property
    def is_registrar(self):
        return perms.user_is_registrar(self.user)

    @property
    def is_ra_manager(self):
        user = self.user
        if user.is_anonymous():
            return False
        if user.is_superuser:
            return True
        return RegistrationAuthority.objects.filter(managers__pk=user.pk).count() > 0

    @property
    def discussions(self):
        return DiscussionPost.objects.filter(
            workgroup__in=self.myWorkgroups.all()
        )

    @property
    def registrarAuthorities(self):
        "NOTE: This is a list of Authorities the user is a *registrar* in!."
        if self.user.is_superuser:
            return RegistrationAuthority.objects.all()
        else:
            return self.user.registrar_in.all()

    def is_workgroup_manager(self, wg=None):
        return perms.user_is_workgroup_manager(self.user, wg)

    def is_favourite(self, item):
        from aristotle_mdr.contrib.favourites.models import Favourite
        fav = Favourite.objects.filter(
            tag__primary=True,
            tag__profile=self,
            item=item
        )
        return fav.exists()

    def toggleFavourite(self, item):
        from aristotle_mdr.contrib.favourites.models import Favourite, Tag

        if self.is_favourite(item):
            fav = Favourite.objects.filter(
                tag__primary=True,
                tag__profile=self,
                item=item
            )
            fav.delete()
            return False
        else:
            fav_tag, created = Tag.objects.get_or_create(
                profile=self,
                primary=True,
            )
            Favourite.objects.create(
                tag=fav_tag,
                item=item
            )
            return True

    @property
    def favourites(self):
        return _concept.objects.filter(
            favourites__tag__primary=True,
            favourites__tag__profile=self
        ).distinct()

    @property
    def favourite_item_pks(self):
        qs = _concept.objects.filter(
            favourites__tag__primary=True,
            favourites__tag__profile=self
        ).distinct().values_list('id', flat=True)
        return list(qs)

    @property
    def favs_and_tags_count(self):
        count = _concept.objects.filter(
            favourites__tag__profile=self
        ).distinct().count()
        return count

    def profile_picture_url(self):
        if self.profilePicture:
            return self.profilePicture.url
        else:
            return reverse("aristotle_mdr:dynamic_profile_picture", args=[self.user.id])


class SandboxShare(models.Model):
    uuid = models.UUIDField(
        help_text=_("Universally-unique Identifier. Uses UUID1 as this improves uniqueness and tracking between registries"),
        unique=True, default=uuid.uuid1, editable=False, null=False
    )
    profile = models.OneToOneField(
        PossumProfile,
        related_name='share'
    )
    created = models.DateTimeField(
        auto_now=True
    )
    emails = JSONField()


def create_user_profile(sender, instance, created, **kwargs):
    if created:
        profile, created = PossumProfile.objects.get_or_create(user=instance)


post_save.connect(create_user_profile, sender=settings.AUTH_USER_MODEL)


@receiver(post_save)
def concept_saved(sender, instance, **kwargs):
    if not issubclass(sender, _concept):
        return

    if not instance.non_cached_fields_changed:
        # If the only thing that has changed is a cached public/locked status
        # then don't notify.
        return
    if kwargs.get('raw'):
        # Don't run during loaddata
        return
    kwargs['changed_fields'] = instance.changed_fields
    fire("concept_changes.concept_saved", obj=instance, **kwargs)


@receiver(pre_save)
def check_concept_app_label(sender, instance, **kwargs):
    if not issubclass(sender, _concept):
        return
    if instance._meta.app_label not in fetch_metadata_apps():
        raise ImproperlyConfigured(
            "Trying to save item <{instance_name}> when app_label <{app_label}> is not enabled".format(
                app_label=instance._meta.app_label,
                instance_name=instance.name
            )
        )


@receiver(post_save, sender=DiscussionComment)
def new_comment_created(sender, **kwargs):
    comment = kwargs['instance']
    post = comment.post
    if kwargs.get('raw'):
        # Don't run during loaddata
        return
    if not kwargs['created']:
        return  # We don't need to notify a topic poster of an edit.
    if comment.author == post.author:
        return  # We don't need to tell someone they replied to themselves
    fire("concept_changes.new_comment_created", obj=comment)


@receiver(post_save, sender=DiscussionPost)
def new_post_created(sender, **kwargs):
    post = kwargs['instance']
    if kwargs.get('raw'):
        # Don't run during loaddata
        return
    if not kwargs['created']:
        return  # We don't need to notify a topic poster of an edit.
    fire("concept_changes.new_post_created", obj=post, **kwargs)


@receiver(post_save, sender=Status)
def states_changed(sender, instance, *args, **kwargs):
    fire("concept_changes.status_changed", obj=instance, **kwargs)


@receiver(post_save, sender=ReviewRequest)
def review_request_changed(sender, instance, *args, **kwargs):
    if kwargs.get('created'):
        fire("action_signals.review_request_created", obj=instance, **kwargs)
    else:
        fire("action_signals.review_request_updated", obj=instance, **kwargs)


@receiver(post_save, sender=SupersedeRelationship)
def new_superseded_relation(sender, instance, *args, **kwargs):
    if kwargs.get('created'):
        fire("concept_changes.item_superseded", obj=instance, **kwargs)
