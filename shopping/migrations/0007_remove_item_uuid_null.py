# Generated by Django 5.1 on 2024-08-23 07:00

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):
    dependencies = [
        ('shopping', '0006_populate_item_uuid_values'),
    ]

    operations = [
        migrations.AlterField(
            model_name='item',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
