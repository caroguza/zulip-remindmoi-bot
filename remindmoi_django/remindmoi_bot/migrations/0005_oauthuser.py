# Generated by Django 3.0.5 on 2020-05-14 16:43

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('remindmoi_bot', '0004_auto_20200414_2124'),
    ]

    operations = [
        migrations.CreateModel(
            name='OAuthUser',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('zulip_user_email', models.CharField(max_length=128)),
                ('user_id', models.CharField(max_length=64)),
                ('access_token', models.CharField(blank=True, max_length=64, null=True, unique=True)),
                ('refresh_token', models.CharField(blank=True, max_length=64, null=True, unique=True)),
                ('token_expiry', models.DateTimeField(blank=True, null=True)),
            ],
        ),
    ]
