# Generated by Django 5.1 on 2024-08-23 13:30

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0008_alter_minimumproductstock_unique_together'),
    ]

    operations = [
        migrations.AddField(
            model_name='productstock',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, editable=False, null=True),
        ),
    ]
