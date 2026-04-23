from django.db import IntegrityError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .exceptions import ExternalAPIException, InvalidProfileDataException
from .filters import build_profile_queryset
from .models import Profile
from .pagination import ProfilePagination
from .parser import parse_query
from .serializers import ProfileListSerializer, ProfileSerializer
from .services import ProfileAggregatorService


# ── Helpers ───────────────────────────────────────────────────────────────────

def _error(message: str, http_status: int) -> Response:
    return Response(
        {"status": "error", "message": message}, status=http_status
    )


def _paginate(request, queryset):
    paginator = ProfilePagination()
    page = paginator.paginate_queryset(queryset, request)
    serializer = ProfileListSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)


# ── Views ─────────────────────────────────────────────────────────────────────

class ProfileView(APIView):
    """
    GET  /api/profiles  — filtered, sorted, paginated list
    POST /api/profiles  — create profile via external API aggregation
    """

    def get(self, request):
        queryset = Profile.objects.all()
        queryset, err = build_profile_queryset(queryset, request.query_params)

        if err:
            return _error(err["message"], err["_status_code"])

        return _paginate(request, queryset)

    def post(self, request):
        if "name" not in request.data:
            return _error("Missing 'name' field", status.HTTP_400_BAD_REQUEST)

        name = request.data.get("name")

        if name == "" or (isinstance(name, str) and not name.strip()):
            return _error("Name cannot be empty", status.HTTP_400_BAD_REQUEST)

        if not isinstance(name, str):
            return _error("Name must be a string", status.HTTP_422_UNPROCESSABLE_ENTITY)

        normalized = name.strip().lower()

        # Idempotency check
        try:
            profile = Profile.objects.get(name=normalized)
            return Response(
                {
                    "status": "success",
                    "message": "Profile already exists",
                    "data": ProfileSerializer(profile).data,
                },
                status=status.HTTP_200_OK,
            )
        except Profile.DoesNotExist:
            pass

        # Fetch from external APIs
        try:
            data = ProfileAggregatorService.fetch_and_process_data(normalized)
        except ExternalAPIException as exc:
            return _error(str(exc), status.HTTP_502_BAD_GATEWAY)
        except InvalidProfileDataException as exc:
            return _error(str(exc), status.HTTP_502_BAD_GATEWAY)
        except Exception:
            return _error(
                "Unexpected error while fetching external data",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            profile = Profile.objects.create(**data)
            return Response(
                {"status": "success", "data": ProfileSerializer(profile).data},
                status=status.HTTP_201_CREATED,
            )
        except IntegrityError:
            profile = Profile.objects.get(name=normalized)
            return Response(
                {
                    "status": "success",
                    "message": "Profile already exists",
                    "data": ProfileSerializer(profile).data,
                },
                status=status.HTTP_200_OK,
            )


class ProfileDetailView(APIView):
    """
    GET    /api/profiles/<uuid:id>
    DELETE /api/profiles/<uuid:id>
    """

    def _get_profile(self, pk):
        try:
            return Profile.objects.get(id=pk), None
        except Profile.DoesNotExist:
            return None, _error("Profile not found", status.HTTP_404_NOT_FOUND)

    def get(self, request, id):
        profile, err = self._get_profile(id)
        if err:
            return err
        return Response(
            {"status": "success", "data": ProfileSerializer(profile).data},
            status=status.HTTP_200_OK,
        )

    def delete(self, request, id):
        profile, err = self._get_profile(id)
        if err:
            return err
        profile.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProfileSearchView(APIView):
    """
    GET /api/profiles/search?q=<natural-language-query>

    Rule-based NLP parsing — no AI, no LLMs.
    Supports pagination via ?page=&limit= params.
    """

    def get(self, request):
        q = request.query_params.get("q", "").strip()

        if not q:
            return _error(
                "Missing or empty 'q' parameter", status.HTTP_400_BAD_REQUEST
            )

        filters = parse_query(q)
        if filters is None:
            return Response(
                {"status": "error", "message": "Unable to interpret query"},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        queryset = Profile.objects.all()
        queryset, err = build_profile_queryset(queryset, filters)
        if err:
            return _error(err["message"], err["_status_code"])

        return _paginate(request, queryset)
