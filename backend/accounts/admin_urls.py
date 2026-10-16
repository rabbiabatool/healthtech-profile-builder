from django.urls import path

from .admin_views import AdminLoginView, AdminLogoutView, AdminMeView
from .views import CsrfView

urlpatterns = [
    path("csrf", CsrfView.as_view()),
    path("login", AdminLoginView.as_view()),
    path("logout", AdminLogoutView.as_view()),
    path("me", AdminMeView.as_view()),
]