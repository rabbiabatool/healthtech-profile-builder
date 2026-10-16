from django.urls import path

from .views import CsrfView, RefreshView, SignupView, UserLoginView, UserLogoutView

urlpatterns = [
    path("csrf", CsrfView.as_view()),
    path("signup", SignupView.as_view()),
    path("user/login", UserLoginView.as_view()),
    path("user/logout", UserLogoutView.as_view()),
    path("refresh", RefreshView.as_view()),
]