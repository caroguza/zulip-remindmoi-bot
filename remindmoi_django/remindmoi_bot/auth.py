import datetime
import json
from typing import Dict, Any

import pytz
import requests
from django.http import JsonResponse

from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views import View
from django.views.generic import RedirectView
from django.conf import settings
from oauth2client.client import OAuth2Credentials
from requests.auth import AuthBase

from remindmoi_bot.models import OAuthUser

NEXTCLOUD_BASE_URL = "https://cloud.monadical.com/"
NEXTCLOUD_TOKEN_URL = f"{NEXTCLOUD_BASE_URL}index.php/apps/oauth2/api/v1/token"
NEXTCLOUD_REDIRECT_URL = f"{NEXTCLOUD_BASE_URL}auth/nextcloud/success/"
NEXTCLOUD_LOGIN_URL = f"{NEXTCLOUD_BASE_URL}index.php/apps/oauth2/authorize"


def login_url() -> str:
    icloud_secrets = settings.ICLOUD_SECRETS

    with open(icloud_secrets) as secret_file:
        json_file = json.load(secret_file)
        secrets_dict = {key: value for key, value in json_file["web"].items()}

    return (
        f"{NEXTCLOUD_LOGIN_URL}?"
        f"client_id={secrets_dict['client_id']}&"
        f"redirect_uri={NEXTCLOUD_REDIRECT_URL}&"
        f"response_type=code")


def auth_token_request(**data) -> Dict[str, Any]:
    icloud_secrets = settings.ICLOUD_SECRETS

    with open(icloud_secrets) as secret_file:
        json_file = json.load(secret_file)
        secrets_dict = {key: value for key, value in json_file["web"].items()}

    resp_json = requests.post(
        NEXTCLOUD_TOKEN_URL,
        data={
            "client_id": secrets_dict["client_id"],
            "client_secret": secrets_dict["client_secret"],
            **data
        },
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
        },
    ).json()
    return resp_json


def get_user_info(access_token, user_id):
    user_info = requests.get(
        url=f"https://cloud.monadical.com/ocs/v1.php/cloud/users/{user_id}?format=json",
        headers=auth_headers(access_token, True)

    ).json()

    return user_info


def auth_headers(access_token, is_ocs=False):
    return {
        "Authorization": f"Bearer {access_token}",
        "OCS-APIRequest": "true" if is_ocs else "false",
    }


def set_oauth_credentials(secrets_dict: Dict[str, str], access_token, token_expiry, refresh_token) -> OAuth2Credentials:

    return OAuth2Credentials(
        access_token=access_token,
        client_id=secrets_dict["client_id"],
        client_secret=secrets_dict["client_secret"],
        refresh_token=refresh_token,
        token_expiry=token_expiry,
        token_uri=secrets_dict["token_uri"],
        user_agent=None,

    )


class OAuth(AuthBase):
    def __init__(self, credentials):
        self.credentials = credentials

    def __call__(self, r):
        self.credentials.apply(r.headers)
        return r


class RedirectLoginView(RedirectView):

    def get_redirect_url(self, *args, **kwargs):
        print(login_url())
        return login_url()


class NextCloudLoginSuccess(View):
    template_name = "succeed_auth.html"

    def get(self, request, *args, **kwargs):

        context = {}
        auth_code = request.GET.get("code")
        if not auth_code:
            raise ValueError(
                "No auth code was provided by NetCloud "
                "Check if the authorization was rejected"
            )

        response = auth_token_request(
            redirect_uri=f"{NEXTCLOUD_REDIRECT_URL}",
            grant_type="authorization_code",
            code=auth_code,
            scope="",
        )
        if "access_token" not in response:
            raise ValueError("Nextcloud didn't return an access token")

        refresh_token = response.get('refresh_token', None)

        token_expiry = None
        if 'expires_in' in response:
            delta = datetime.timedelta(seconds=int(response['expires_in']))
            token_expiry = delta + datetime.datetime.utcnow()

        user_info = get_user_info(response["access_token"], response["user_id"])["ocs"]
        user_email = user_info["data"]["email"]

        obj, created = OAuthUser.objects.update_or_create(
            zulip_user_email=user_email,
            defaults={
                "user_id": response["user_id"],
                "access_token": response["access_token"],
                "refresh_token": refresh_token,
                "token_expiry": token_expiry,
            }
        )

        return render(request, self.template_name, context)


class NextCloudRefreshToken(View):
    template_name = "succeed_auth.html"

    def get(self, request, *args, **kwargs):
        user_email = request.GET.get("email", None)
        assert user_email is not None
        oauth_obj = OAuthUser.objects.filter(zulip_user_email=user_email)
        context = {}

        if not oauth_obj.exists():
            return JsonResponse({
                "message": 'Oauth Object does not exist yet',
            }, status=500)

        oauth_obj = oauth_obj.first()

        if not oauth_obj.refresh_token:
            return JsonResponse({
                "message": 'Refresh token is not in the Oauth Object',

            }, status=500)

        response = auth_token_request(
            grant_type='refresh_token',
            refresh_token=oauth_obj.refresh_token,
        )

        if "access_token" not in response:
            return JsonResponse({
                "message": 'Access token is not in the response',

            }, status=500)

        refresh_token = response.get('refresh_token', None)
        oauth_obj.refresh_token = refresh_token
        oauth_obj.save()

        token_expiry = None
        if 'expires_in' in response:
            delta = datetime.timedelta(seconds=int(response['expires_in']))
            token_expiry = delta + datetime.datetime.utcnow()

        oauth_obj.token_expiry = token_expiry
        oauth_obj.access_token = response["access_token"]
        oauth_obj.save()

        return render(request, self.template_name, context)


@method_decorator(csrf_exempt, name="dispatch")
class EmailAuthorizedView(View):

    def get(self, request):
        user_email = request.GET.get("email")
        user_authorized_qs = OAuthUser.objects.filter(zulip_user_email=user_email)
        status = 200 if user_authorized_qs.exists() else 404
        user_authorized = user_authorized_qs.first()

        return JsonResponse({
            "user_authorized": user_authorized_qs.exists(),
            "user_expired": user_authorized.token_expiry <= datetime.datetime.now(pytz.timezone("utc"))
        }, status=status)
