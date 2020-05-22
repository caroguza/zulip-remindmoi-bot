from django.urls import path

from remindmoi_bot.auth import RedirectLoginView, NextCloudLoginSuccess, \
    EmailAuthorizedView, NextCloudRefreshToken

urlpatterns = [
    path("cloud-login/", RedirectLoginView.as_view(), name="cloud_login"),
    path("auth/nextcloud/success/", NextCloudLoginSuccess.as_view(), name="cloud_login"),
    path("email-authorized", EmailAuthorizedView.as_view(), name="email_authorized"),
    path("auth/nextcloud/refresh-token", NextCloudRefreshToken.as_view(), name="refresh_token"),
]