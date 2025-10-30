from django.urls import path

from whimo.auth.otp.views import (
    OTPSendView,
    OTPVerifyView,
    PasswordResetCheckView,
    PasswordResetSendView,
    PasswordResetVerifyView,
)

urlpatterns = [
    path("verify/", OTPVerifyView.as_view(), name="otp_verify"),
    path("send/", OTPSendView.as_view(), name="otp_send"),
    path("password-reset/send/", PasswordResetSendView.as_view(), name="password_reset_send"),
    path("password-reset/check/", PasswordResetCheckView.as_view(), name="password_reset_check"),
    path("password-reset/verify/", PasswordResetVerifyView.as_view(), name="password_reset_verify"),
]
