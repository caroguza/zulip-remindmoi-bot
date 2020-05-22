import json
import uuid

from django.db import models


class Reminder(models.Model):
    reminder_id = models.AutoField(primary_key=True)

    zulip_user_email = models.CharField(max_length=128)
    title = models.CharField(max_length=1024)
    created = models.DateTimeField()
    deadline = models.DateTimeField()
    active = models.BooleanField(default=True)


class OAuthUser(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    zulip_user_email = models.CharField(max_length=128)
    user_id = models.CharField(max_length=64)

    access_token = models.CharField(max_length=64, unique=True, blank=True, null=True)
    refresh_token = models.CharField(max_length=64, unique=True, blank=True, null=True)
    token_expiry = models.DateTimeField(blank=True, null=True)

    def oauth_to_dict(self):
        return {
            "zulip_user_email": self.zulip_user_email,
            "user_id": self.user_id,
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_expiry": self.token_expiry,
        }


class HistoryEvents(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    zulip_user_email = models.CharField(max_length=128)
    dt_start = models.DateTimeField()
