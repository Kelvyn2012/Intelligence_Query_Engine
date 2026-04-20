from django.urls import path

from .views import ProfileDetailView, ProfileSearchView, ProfileView

urlpatterns = [
    # Search must be declared before <uuid:id> to avoid ambiguity
    path("profiles/search", ProfileSearchView.as_view(), name="profiles-search"),
    path("profiles", ProfileView.as_view(), name="profiles"),
    path("profiles/<uuid:id>", ProfileDetailView.as_view(), name="profile-detail"),
]
