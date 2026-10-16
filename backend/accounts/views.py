from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import update_last_login
from django.middleware.csrf import get_token
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings as jwt_settings
from rest_framework_simplejwt.tokens import RefreshToken

from .authentication import enforce_csrf
from .models import Role, User
from .serializers import LoginSerializer, SignupSerializer, UserSerializer

INVALID_LOGIN_MESSAGE = "Invalid email or password."
SESSION_ENDED_MESSAGE = "Session expired. Please log in again."


def set_auth_cookies(response, refresh):
    cookie_options = {
        "httponly": True,
        "secure": settings.JWT_COOKIE_SECURE,
        "samesite": settings.JWT_COOKIE_SAMESITE,
    }
    response.set_cookie(
        settings.JWT_ACCESS_COOKIE,
        str(refresh.access_token),
        max_age=int(jwt_settings.ACCESS_TOKEN_LIFETIME.total_seconds()),
        path="/",
        **cookie_options,
    )
    response.set_cookie(
        settings.JWT_REFRESH_COOKIE,
        str(refresh),
        max_age=int(jwt_settings.REFRESH_TOKEN_LIFETIME.total_seconds()),
        path=settings.JWT_REFRESH_COOKIE_PATH,
        **cookie_options,
    )


def clear_auth_cookies(response):
    response.delete_cookie(
        settings.JWT_ACCESS_COOKIE,
        path="/",
        samesite=settings.JWT_COOKIE_SAMESITE,
    )
    response.delete_cookie(
        settings.JWT_REFRESH_COOKIE,
        path=settings.JWT_REFRESH_COOKIE_PATH,
        samesite=settings.JWT_COOKIE_SAMESITE,
    )


class CsrfView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"csrfToken": get_token(request)})


class SignupView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class UserLoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            request=request,
            username=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )
        if user is None or user.role != Role.USER:
            return Response(
                {"detail": INVALID_LOGIN_MESSAGE},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        update_last_login(None, user)
        refresh = RefreshToken.for_user(user)
        response = Response({"user": UserSerializer(user).data})
        set_auth_cookies(response, refresh)
        return response


class RefreshView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        enforce_csrf(request)

        raw_token = request.COOKIES.get(settings.JWT_REFRESH_COOKIE)
        if not raw_token:
            return self._reject()

        try:
            old_token = RefreshToken(raw_token)
        except TokenError:
            return self._reject()

        user = User.objects.filter(
            pk=old_token[jwt_settings.USER_ID_CLAIM],
            is_active=True,
            role=Role.USER,
        ).first()
        if user is None:
            return self._reject()

        old_token.blacklist()
        new_refresh = RefreshToken.for_user(user)
        response = Response({"detail": "Token refreshed."})
        set_auth_cookies(response, new_refresh)
        return response

    @staticmethod
    def _reject():
        response = Response(
            {"detail": SESSION_ENDED_MESSAGE},
            status=status.HTTP_401_UNAUTHORIZED,
        )
        clear_auth_cookies(response)
        return response


class UserLogoutView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        enforce_csrf(request)

        raw_token = request.COOKIES.get(settings.JWT_REFRESH_COOKIE)
        if raw_token:
            try:
                RefreshToken(raw_token).blacklist()
            except TokenError:
                pass

        response = Response(status=status.HTTP_204_NO_CONTENT)
        clear_auth_cookies(response)
        return response
