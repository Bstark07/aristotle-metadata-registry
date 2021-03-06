# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2018-11-07 04:33
from __future__ import unicode_literals

import aristotle_mdr.fields
from django.db import migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('aristotle_mdr', '0045__concept_superseded_by_items'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dataelementconcept',
            name='conceptualDomain',
            field=aristotle_mdr.fields.ConceptForeignKey(blank=True, help_text='references a Conceptual_Domain that is part of the specification of the Data_Element_Concept', null=True, on_delete=django.db.models.deletion.CASCADE, to='aristotle_mdr.ConceptualDomain', verbose_name='Conceptual Domain'),
        ),
        migrations.AlterField(
            model_name='dataelementconcept',
            name='objectClass',
            field=aristotle_mdr.fields.ConceptForeignKey(blank=True, help_text='references an Object_Class that is part of the specification of the Data_Element_Concept', null=True, on_delete=django.db.models.deletion.CASCADE, to='aristotle_mdr.ObjectClass', verbose_name='Object Class'),
        ),
        migrations.AlterField(
            model_name='dataelementconcept',
            name='property',
            field=aristotle_mdr.fields.ConceptForeignKey(blank=True, help_text='references a Property that is part of the specification of the Data_Element_Concept', null=True, on_delete=django.db.models.deletion.CASCADE, to='aristotle_mdr.Property', verbose_name='Property'),
        ),
        migrations.AlterField(
            model_name='permissiblevalue',
            name='valueDomain',
            field=aristotle_mdr.fields.ConceptForeignKey(help_text='Enumerated Value Domain that this value meaning relates to', on_delete=django.db.models.deletion.CASCADE, related_name='permissiblevalue_set', to='aristotle_mdr.ValueDomain', verbose_name='Value Domain'),
        ),
        migrations.AlterField(
            model_name='supplementaryvalue',
            name='valueDomain',
            field=aristotle_mdr.fields.ConceptForeignKey(help_text='Enumerated Value Domain that this value meaning relates to', on_delete=django.db.models.deletion.CASCADE, related_name='supplementaryvalue_set', to='aristotle_mdr.ValueDomain', verbose_name='Value Domain'),
        ),
        migrations.AlterField(
            model_name='valuedomain',
            name='conceptual_domain',
            field=aristotle_mdr.fields.ConceptForeignKey(blank=True, help_text='The Conceptual Domain that this Value Domain which provides representation.', null=True, on_delete=django.db.models.deletion.CASCADE, to='aristotle_mdr.ConceptualDomain', verbose_name='Conceptual Domain'),
        ),
        migrations.AlterField(
            model_name='valuedomain',
            name='data_type',
            field=aristotle_mdr.fields.ConceptForeignKey(blank=True, help_text='Datatype used in a Value Domain', null=True, on_delete=django.db.models.deletion.CASCADE, to='aristotle_mdr.DataType', verbose_name='Data Type'),
        ),
        migrations.AlterField(
            model_name='valuedomain',
            name='unit_of_measure',
            field=aristotle_mdr.fields.ConceptForeignKey(blank=True, help_text='Unit of Measure used in a Value Domain', null=True, on_delete=django.db.models.deletion.CASCADE, to='aristotle_mdr.UnitOfMeasure', verbose_name='Unit Of Measure'),
        ),
        migrations.AlterField(
            model_name='valuemeaning',
            name='conceptual_domain',
            field=aristotle_mdr.fields.ConceptForeignKey(on_delete=django.db.models.deletion.CASCADE, to='aristotle_mdr.ConceptualDomain', verbose_name='Conceptual Domain'),
        ),
    ]
