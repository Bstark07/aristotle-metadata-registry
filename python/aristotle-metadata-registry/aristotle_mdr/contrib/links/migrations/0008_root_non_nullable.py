# -*- coding: utf-8 -*-
# Generated by Harry 1.0 on 2018-11-16 00:23
from __future__ import unicode_literals

import aristotle_mdr.fields
from django.db import migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('aristotle_mdr_links', '0007_migrate_root_item'),
    ]

    operations = [
        migrations.AlterField(
            model_name='link',
            name='root_item',
            field=aristotle_mdr.fields.ConceptForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='owned_links', to='aristotle_mdr._concept'),
        )
    ]
