from django.urls import path
from .views import ProfileDetailView, ProfileSearchView, ProfileView

urlpatterns = [
    path("profiles/search/", ProfileSearchView.as_view(), name="profiles-search"),
    path("profiles/", ProfileView.as_view(), name="profiles"),
    path("profiles/<uuid:id>/", ProfileDetailView.as_view(), name="profile-detail"),
]
