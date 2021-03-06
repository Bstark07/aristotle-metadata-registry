# -*- coding: utf-8 -*-
# Generated by Django 1.11.17 on 2018-12-06 01:25
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('aristotle_mdr_review_requests', '0003_auto_20181126_1707'),
    ]

    operations = [
        migrations.AlterField(
            model_name='reviewrequest',
            name='registration_date',
            field=models.DateField(blank=True, help_text='date and time you want the metadata to be registered from', null=True, verbose_name='Date registration effective'),
        ),
        migrations.AlterField(
            model_name='reviewrequest',
            name='target_registration_state',
            field=models.IntegerField(blank=True, choices=[(0, 'Not Progressed'), (1, 'Incomplete'), (2, 'Candidate'), (3, 'Recorded'), (4, 'Qualified'), (5, 'Standard'), (6, 'Preferred Standard'), (7, 'Superseded'), (8, 'Retired')], help_text='The state at which a user wishes a metadata item to be endorsed', null=True),
        ),
    ]
