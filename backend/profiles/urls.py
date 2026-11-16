from django.urls import path

from .views import ContactDetailView, ContactListView, DemographicsView, MyProfileView, WellnessView

urlpatterns = [
    path("me", MyProfileView.as_view()),
    path("me/demographics", DemographicsView.as_view()),
    path("me/wellness", WellnessView.as_view()),
    path("me/emergency-contacts", ContactListView.as_view()),
    path("me/emergency-contacts/<int:pk>", ContactDetailView.as_view()),
]
