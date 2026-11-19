from collections.abc import Mapping

from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.exceptions import NotFound, PermissionDenied, Throttled, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .constants import DIRECTION_CHOICES, NUTRIENT_FIELDS, WRITE_WINDOW_SECONDS
from .decorators import write_limit_exceeded
from .forms import PreferenceDraftForm
from .models import Decision, Preference
from .serializers import BulkDeleteSerializer, DecisionSerializer, PreferenceSerializer
from .views import combined_preview_data, single_preview_data


def owned_item(queryset, pk, user):
    item = get_object_or_404(queryset, pk=pk)
    if item.user_id != user.pk:
        raise PermissionDenied("Kamu tidak punya akses ke data ini.")
    return item


def check_write_limit(user):
    if write_limit_exceeded(user):
        raise Throttled(wait=WRITE_WINDOW_SECONDS)


def save_item(serializer, *, created=False, **fields):
    serializer.is_valid(raise_exception=True)
    serializer.save(**fields)
    return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


@api_view(["GET", "HEAD", "POST"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def preference_list(request):
    context = {"request": request}
    if request.method in ("GET", "HEAD"):
        items = Preference.objects.filter(user=request.user).order_by("pk")
        return Response(PreferenceSerializer(items, many=True, context=context).data)
    check_write_limit(request.user)
    with transaction.atomic():
        # Share the same per-user lock as the browser's draft save.
        get_user_model().objects.select_for_update().get(pk=request.user.pk)
        serializer = PreferenceSerializer(data=request.data, context=context)
        return save_item(serializer, created=True, user=request.user)


@api_view(["GET", "HEAD", "PUT", "PATCH", "DELETE"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def preference_detail(request, pk):
    item = owned_item(Preference.objects.all(), pk, request.user)
    context = {"request": request}
    if request.method in ("GET", "HEAD"):
        return Response(PreferenceSerializer(item, context=context).data)
    check_write_limit(request.user)
    if request.method == "DELETE":
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    return save_item(PreferenceSerializer(
        item, data=request.data, partial=request.method == "PATCH", context=context,
    ))


@api_view(["GET", "HEAD"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def preference_preview(request):
    nutrient = request.query_params.get("nutrient")
    direction = request.query_params.get("direction")
    if nutrient not in NUTRIENT_FIELDS or direction not in dict(DIRECTION_CHOICES):
        raise ValidationError({"detail": "Nutrien atau arah tidak valid."})
    return Response(single_preview_data(nutrient, direction))


@api_view(["POST"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def preference_combined_preview(request):
    if not isinstance(request.data, Mapping):
        raise ValidationError({"detail": "Kirim objek berisi daftar preferensi."})
    form = PreferenceDraftForm(request.data)
    if not form.is_valid():
        raise ValidationError(form.errors)
    return Response(combined_preview_data(form.cleaned_data["preferences"]))


@api_view(["GET", "HEAD", "POST"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def decision_list(request):
    context = {"request": request}
    if request.method in ("GET", "HEAD"):
        items = Decision.objects.filter(user=request.user).select_related("product", "shelf")
        return Response(DecisionSerializer(items.order_by("-created_at", "-pk"), many=True, context=context).data)
    check_write_limit(request.user)
    with transaction.atomic():
        return save_item(DecisionSerializer(data=request.data, context=context), created=True)


@api_view(["GET", "HEAD", "PUT", "PATCH", "DELETE"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def decision_detail(request, pk):
    item = owned_item(Decision.objects.select_related("product", "shelf"), pk, request.user)
    context = {"request": request}
    if request.method in ("GET", "HEAD"):
        return Response(DecisionSerializer(item, context=context).data)
    check_write_limit(request.user)
    if request.method == "DELETE":
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    return save_item(DecisionSerializer(
        item, data=request.data, partial=request.method == "PATCH", context=context,
    ))


@api_view(["POST"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def decision_bulk_delete(request):
    check_write_limit(request.user)
    serializer = BulkDeleteSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    ids = serializer.validated_data["ids"]
    with transaction.atomic():
        items = Decision.objects.filter(user=request.user, pk__in=ids)
        locked_ids = list(items.select_for_update().order_by("pk").values_list("pk", flat=True))
        if len(locked_ids) != len(ids):
            raise NotFound("Data tidak ditemukan.")
        items.delete()
    return Response({"deleted_ids": ids})
