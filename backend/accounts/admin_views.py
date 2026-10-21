from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.models import AuditAction, Outcome
from audit.services import record_event

from .authentication import AdminSessionAuthentication, enforce_csrf
from .models import Role
from .permissions import IsAdminRole
from .serializers import AdminUserSerializer, LoginSerializer
from .views import INVALID_LOGIN_MESSAGE, clear_auth_cookies

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken


# class AdminLoginView(APIView):
#     authentication_classes = []
#     permission_classes = [AllowAny]

#     def post(self, request):
#         enforce_csrf(request)

#         serializer = LoginSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)

#         user = authenticate(
#             request=request,
#             username=serializer.validated_data["email"],
#             password=serializer.validated_data["password"],
#         )
#         if user is None or user.role != Role.ADMIN:
#             record_event(None, AuditAction.ADMIN_LOGIN_FAILED, outcome=Outcome.FAILED)
#             return Response(
#                 {"detail": INVALID_LOGIN_MESSAGE},
#                 status=status.HTTP_401_UNAUTHORIZED,
#             )

#         login(request, user)
#         record_event(user, AuditAction.ADMIN_LOGIN)
#         return Response(
#             {
#                 "user": AdminUserSerializer(user).data,
#                 "csrfToken": get_token(request),
#             }
#         )


class AdminLoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        enforce_csrf(request)

        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            request=request,
            username=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )

        if user is None or user.role != Role.ADMIN:
            record_event(
                None,
                AuditAction.ADMIN_LOGIN_FAILED,
                outcome=Outcome.FAILED,
            )
            return Response(
                {"detail": INVALID_LOGIN_MESSAGE},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # 1. Revoke the member's refresh token, if one exists.
        raw_refresh_token = request.COOKIES.get(
            settings.JWT_REFRESH_COOKIE
        )

        if raw_refresh_token:
            try:
                RefreshToken(raw_refresh_token).blacklist()
            except TokenError:
                # The token may be invalid, expired, or already blacklisted.
                pass

        # 2. Remove any existing Django session before creating
        #    the admin session.
        logout(request)

        # 3. Create the new admin session.
        login(request, user)

        record_event(user, AuditAction.ADMIN_LOGIN)

        # 4. Return the admin details and fresh CSRF token.
        response = Response(
            {
                "user": AdminUserSerializer(user).data,
                "csrfToken": get_token(request),
            }
        )

        # 5. Remove the member's JWT cookies from this browser.
        clear_auth_cookies(response)

        return response



class AdminLogoutView(APIView):
    authentication_classes = [AdminSessionAuthentication]
    permission_classes = [IsAdminRole]

    def post(self, request):
        record_event(request.user, AuditAction.ADMIN_LOGOUT)
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminMeView(APIView):
    authentication_classes = [AdminSessionAuthentication]
    permission_classes = [IsAdminRole]

    def get(self, request):
        return Response(AdminUserSerializer(request.user).data)