from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import IntegrityError
from .models import Profile
from .serializers import ProfileSerializer, ProfileListSerializer
from .services import ProfileAggregatorService
from .exceptions import ExternalAPIException, InvalidProfileDataException


class ProfileView(APIView):
    def get(self, request):
        queryset = Profile.objects.all()

        gender = request.query_params.get('gender')
        country_id = request.query_params.get('country_id')
        age_group = request.query_params.get('age_group')

        if gender:
            queryset = queryset.filter(gender__iexact=gender)
        if country_id:
            queryset = queryset.filter(country_id__iexact=country_id)
        if age_group:
            queryset = queryset.filter(age_group__iexact=age_group)

        serializer = ProfileListSerializer(queryset, many=True)
        return Response({
            "status": "success",
            "count": queryset.count(),
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    def post(self, request):
        if 'name' not in request.data:
            return Response({"status": "error", "message": "Missing 'name' field"}, status=status.HTTP_400_BAD_REQUEST)

        name = request.data.get('name')

        if name == "":
            return Response({"status": "error", "message": "Name cannot be empty"}, status=status.HTTP_400_BAD_REQUEST)

        if not isinstance(name, str):
            return Response({"status": "error", "message": "Name must be a string"}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        normalized_name = name.strip().lower()
        if not normalized_name:
            return Response({"status": "error", "message": "Name cannot be only whitespace"}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Check Idempotency
        try:
            profile = Profile.objects.get(name=normalized_name)
            return Response({
                "status": "success",
                "message": "Profile already exists",
                "data": ProfileSerializer(profile).data
            }, status=status.HTTP_200_OK)
        except Profile.DoesNotExist:
            pass

        # 2. Fetch and Validate External Data
        try:
            processed_data = ProfileAggregatorService.fetch_and_process_data(normalized_name)
        except ExternalAPIException as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_502_BAD_GATEWAY)
        except InvalidProfileDataException as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_502_BAD_GATEWAY)
        except Exception:
            return Response({"status": "error", "message": "Unexpected error while fetching external data"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 3. Handle Persistence
        try:
            profile = Profile.objects.create(**processed_data)
            return Response({
                "status": "success",
                "data": ProfileSerializer(profile).data
            }, status=status.HTTP_201_CREATED)
        except IntegrityError:
            # Race condition handling
            profile = Profile.objects.get(name=normalized_name)
            return Response({
                "status": "success",
                "message": "Profile already exists",
                "data": ProfileSerializer(profile).data
            }, status=status.HTTP_200_OK)


class ProfileDetailView(APIView):
    def get(self, request, id):
        try:
            profile = Profile.objects.get(id=id)
            return Response({
                "status": "success",
                "data": ProfileSerializer(profile).data
            }, status=status.HTTP_200_OK)
        except Profile.DoesNotExist:
            return Response({"status": "error", "message": "Profile not found"}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, id):
        try:
            profile = Profile.objects.get(id=id)
            profile.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Profile.DoesNotExist:
            return Response({"status": "error", "message": "Profile not found"}, status=status.HTTP_404_NOT_FOUND)