# Generated by Django 5.0.7 on 2024-08-05 19:19

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('master', '0002_alter_product_options'),
        ('shopping', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='item',
            name='product',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.RESTRICT, to='master.product'),
        ),
    ]
