from django.urls import path
from .views import (
    RegisterView,
    LoginView,
    TokenRefreshView,
    GmailConnectView,
    GmailCallbackView,
    MeView,
    TemplateView,
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='auth-register'),
    path('login/', LoginView.as_view(), name='auth-login'),
    path('refresh/', TokenRefreshView.as_view(), name='auth-refresh'),
    path('gmail/connect/', GmailConnectView.as_view(), name='gmail-connect'),
    path('gmail/callback/', GmailCallbackView.as_view(), name='gmail-callback'),
    path('me/', MeView.as_view(), name='auth-me'),
    path('template/', TemplateView.as_view(), name='auth-template'),
]
