from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .authentication import AdminSessionAuthentication, enforce_csrf
from .models import Role
from .permissions import IsAdminRole
from .serializers import AdminUserSerializer, LoginSerializer
from .views import INVALID_LOGIN_MESSAGE


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
            return Response(
                {"detail": INVALID_LOGIN_MESSAGE},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        login(request, user)
        return Response(
            {
                "user": AdminUserSerializer(user).data,
                "csrfToken": get_token(request),
            }
        )


class AdminLogoutView(APIView):
    authentication_classes = [AdminSessionAuthentication]
    permission_classes = [IsAdminRole]

    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminMeView(APIView):
    authentication_classes = [AdminSessionAuthentication]
    permission_classes = [IsAdminRole]

    def get(self, request):
        return Response(AdminUserSerializer(request.user).data)