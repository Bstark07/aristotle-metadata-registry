# -*- coding: utf-8 -*-
# Generated by Harry 0.1a2 on 2018-08-20
from __future__ import unicode_literals

import aristotle_mdr.fields
from django.db import migrations, models

def make_lowercase(apps, schema_editor):
    UserModel = apps.get_model('aristotle_mdr_user_management', 'User')

    for user in UserModel.objects.all():
        if not user.email.islower():
            user.email = user.email.lower()
            user.save()

def lowercase_reverse(apps, schema_editor):
    print('WARNING: This migration cannot be reversed. All user emails will remain lowercase')

class Migration(migrations.Migration):

    dependencies = [
        ('aristotle_mdr_user_management', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(make_lowercase, lowercase_reverse)
    ]
