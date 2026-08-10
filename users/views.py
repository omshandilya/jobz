import base64
import logging
import requests as http_requests
from django.conf import settings
from django.shortcuts import redirect
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from .models import User

logger = logging.getLogger(__name__)

GOOGLE_AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
GOOGLE_TOKEN_URL = 'https://oauth2.googleapis.com/token'
GOOGLE_USERINFO_URL = 'https://www.googleapis.com/oauth2/v3/userinfo'
GMAIL_SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/userinfo.email',
    'openid',
]


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


def user_data(user):
    return {
        'id': str(user.id),
        'email': user.email,
        'name': user.name,
        'gmail_connected': user.gmail_connected,
        'gmail_email': user.gmail_email,
        'email_template': user.email_template,
    }


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email', '').strip().lower()
        password = request.data.get('password', '')
        name = request.data.get('name', '').strip()

        if not email or not password:
            return Response(
                {'error': 'email and password are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if User.objects.filter(email=email).exists():
            return Response(
                {'error': 'An account with this email already exists.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Generate a unique username from email
        base_username = email.split('@')[0]
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f'{base_username}{counter}'
            counter += 1

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            name=name,
        )

        tokens = get_tokens_for_user(user)
        return Response(
            {**tokens, 'user': user_data(user)},
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email', '').strip().lower()
        password = request.data.get('password', '')

        if not email or not password:
            return Response(
                {'error': 'email and password are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {'error': 'Invalid credentials.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.check_password(password):
            return Response(
                {'error': 'Invalid credentials.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.is_active:
            return Response(
                {'error': 'Account is disabled.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        tokens = get_tokens_for_user(user)
        return Response({**tokens, 'user': user_data(user)})


class TokenRefreshView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response(
                {'error': 'refresh token is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            token = RefreshToken(refresh_token)
            return Response({'access': str(token.access_token)})
        except TokenError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_401_UNAUTHORIZED,
            )


class GmailConnectView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Encode user_id as base64 for state param
        state = base64.urlsafe_b64encode(str(request.user.id).encode()).decode()

        params = {
            'client_id': settings.GOOGLE_CLIENT_ID,
            'redirect_uri': settings.GOOGLE_REDIRECT_URI,
            'response_type': 'code',
            'scope': ' '.join(GMAIL_SCOPES),
            'access_type': 'offline',
            'prompt': 'consent',
            'state': state,
        }
        query_string = '&'.join(f'{k}={v}' for k, v in params.items())
        auth_url = f'{GOOGLE_AUTH_URL}?{query_string}'

        return Response({'auth_url': auth_url})


class GmailCallbackView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        code = request.query_params.get('code')
        state = request.query_params.get('state')
        error = request.query_params.get('error')

        if error:
            return redirect(f'http://localhost:3000/settings?gmail=error&reason={error}')

        if not code or not state:
            return redirect('http://localhost:3000/settings?gmail=error&reason=missing_params')

        # Decode user_id from state
        try:
            user_id = base64.urlsafe_b64decode(state.encode()).decode()
            user = User.objects.get(id=user_id)
        except Exception:
            return redirect('http://localhost:3000/settings?gmail=error&reason=invalid_state')

        # Exchange code for tokens
        token_data = {
            'client_id': settings.GOOGLE_CLIENT_ID,
            'client_secret': settings.GOOGLE_CLIENT_SECRET,
            'redirect_uri': settings.GOOGLE_REDIRECT_URI,
            'grant_type': 'authorization_code',
            'code': code,
        }

        try:
            token_resp = http_requests.post(GOOGLE_TOKEN_URL, data=token_data, timeout=10)
            token_resp.raise_for_status()
            token_json = token_resp.json()
        except Exception as e:
            logger.error(f'Gmail OAuth token exchange failed: {e}')
            return redirect('http://localhost:3000/settings?gmail=error&reason=token_exchange_failed')

        access_token = token_json.get('access_token', '')
        refresh_token = token_json.get('refresh_token', '')

        # Get the Gmail email address
        try:
            userinfo_resp = http_requests.get(
                GOOGLE_USERINFO_URL,
                headers={'Authorization': f'Bearer {access_token}'},
                timeout=10,
            )
            userinfo_resp.raise_for_status()
            gmail_email = userinfo_resp.json().get('email', '')
        except Exception as e:
            logger.error(f'Gmail userinfo fetch failed: {e}')
            gmail_email = ''

        # Save tokens to user
        user.gmail_access_token = access_token
        if refresh_token:
            user.gmail_refresh_token = refresh_token
        user.gmail_email = gmail_email
        user.gmail_connected_at = timezone.now()
        user.save(update_fields=[
            'gmail_access_token', 'gmail_refresh_token',
            'gmail_email', 'gmail_connected_at',
        ])

        return redirect('http://localhost:3000/settings?gmail=connected')


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(user_data(request.user))


class TemplateView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        template = request.data.get('email_template', '')
        request.user.email_template = template
        request.user.save(update_fields=['email_template'])
        return Response(user_data(request.user))
