from django.urls import path

from .views import ContactDetailView, ContactListView, DemographicsView, MyProfileView, WellnessView

urlpatterns = [
    # Root profile lifecycle
    # POST   → create a new profile (201)
    # GET    → read the profile     (200 / 404)
    # DELETE → delete the profile   (204 / 404)
    # PATCH  → not allowed          (405) – use section endpoints
    path("me", MyProfileView.as_view()),

    # Section-level endpoints (edit and reset individual sections)
    path("me/demographics", DemographicsView.as_view()),
    path("me/wellness", WellnessView.as_view()),
    path("me/emergency-contacts", ContactListView.as_view()),
    path("me/emergency-contacts/<int:pk>", ContactDetailView.as_view()),
]
