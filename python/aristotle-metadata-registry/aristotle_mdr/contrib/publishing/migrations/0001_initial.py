# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2018-11-07 04:49
from __future__ import unicode_literals

import aristotle_mdr.fields
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import model_utils.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('aristotle_mdr', '0046_auto_20181107_0433'),
    ]

    operations = [
        migrations.CreateModel(
            name='VersionPublicationRecord',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('public_user_publication_date', models.DateTimeField(blank=True, default=None, help_text='Date from which public users can view version histories for this item.', null=True, verbose_name='Public version history start date')),
                ('authenticated_user_publication_date', models.DateTimeField(blank=True, default=None, help_text='Date from which logged in users can view version histories for this item.', null=True, verbose_name='Logged-in version history start date')),
                ('concept', aristotle_mdr.fields.ConceptOneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='versionpublicationrecord', to='aristotle_mdr._concept')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
