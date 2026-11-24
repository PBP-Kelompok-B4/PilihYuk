"""Serializer DRF Modul Antrean Data. Masukan hanya diperiksa bentuknya; isinya dinilai services.py."""
from rest_framework import serializers

from product_catalog.models import Product

from .models import DataCorrection, DataCorrectionItem
from .validators import to_column_value, to_display

MAX_ID = 9223372036854775807  # batas BIGINT


class MissingEntrySerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()
    correctable = serializers.BooleanField()
    fields = serializers.ListField(child=serializers.CharField())


class ContributionRowSerializer(serializers.Serializer):
    id = serializers.IntegerField(source="pk")
    product_name = serializers.CharField()
    brand = serializers.CharField()
    quantity = serializers.CharField()
    image_url = serializers.CharField()
    missing = MissingEntrySerializer(many=True)
    missing_count = serializers.IntegerField()
    shelf_count = serializers.IntegerField(allow_null=True)
    status = serializers.CharField()
    status_label = serializers.CharField()


class ContributionStatsSerializer(serializers.Serializer):
    incomplete_products = serializers.IntegerField()
    submitted_last_7_days = serializers.IntegerField()
    approved = serializers.IntegerField()
    shelf_average = serializers.FloatField(allow_null=True)


class OptionSerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()


class ContributionQueueSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    num_pages = serializers.IntegerField()
    next_page = serializers.IntegerField(allow_null=True)
    previous_page = serializers.IntegerField(allow_null=True)
    sort = serializers.CharField()
    missing = serializers.CharField(allow_null=True)
    shelf_available = serializers.BooleanField()
    sort_options = OptionSerializer(many=True)
    missing_options = OptionSerializer(many=True)
    stats = ContributionStatsSerializer()
    results = ContributionRowSerializer(many=True)


class ProductSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ("id", "product_name", "brand", "quantity", "image_url", "is_active")
        read_only_fields = fields


class CorrectionFieldSerializer(serializers.Serializer):
    field_name = serializers.CharField()
    label = serializers.CharField()
    group = serializers.CharField()
    type = serializers.CharField()
    current_value = serializers.ReadOnlyField()
    current_display = serializers.CharField(allow_null=True)
    display_factor = serializers.IntegerField()
    help_text = serializers.CharField()


class CorrectionFormSerializer(serializers.Serializer):
    product = ProductSummarySerializer()
    focus = serializers.ListField(child=serializers.CharField())
    correctable_fields = CorrectionFieldSerializer(many=True)


class CorrectionItemSerializer(serializers.ModelSerializer):
    """Nilai dalam satuan kolom (natrium gram); *_display untuk tampilan (natrium mg)."""

    label = serializers.CharField(source="get_field_name_display")
    old_value = serializers.SerializerMethodField()
    proposed_value = serializers.SerializerMethodField()
    old_display = serializers.SerializerMethodField()
    proposed_display = serializers.SerializerMethodField()
    status_label = serializers.CharField(source="get_status_display")

    class Meta:
        model = DataCorrectionItem
        fields = (
            "id", "field_name", "label", "old_value", "proposed_value", "old_display",
            "proposed_display", "status", "status_label", "review_note",
        )
        read_only_fields = ("id", "field_name", "status", "review_note")

    def get_old_value(self, item):
        return to_column_value(item.field_name, item.old_value)

    def get_proposed_value(self, item):
        return to_column_value(item.field_name, item.proposed_value)

    def get_old_display(self, item):
        return to_display(item.field_name, item.old_value)

    def get_proposed_display(self, item):
        return to_display(item.field_name, item.proposed_value)


class CorrectionSerializer(serializers.ModelSerializer):
    """Prefetch items dulu, karena status, is_withdrawable, dan items membaca items.all()."""

    product = ProductSummarySerializer()
    status = serializers.CharField()
    status_label = serializers.CharField(source="get_status_display")
    is_withdrawable = serializers.BooleanField()
    items = CorrectionItemSerializer(many=True)

    class Meta:
        model = DataCorrection
        fields = ("id", "product", "status", "status_label", "is_withdrawable", "created_at", "items")
        read_only_fields = ("id", "created_at")


class CorrectionPageSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    num_pages = serializers.IntegerField()
    next_page = serializers.IntegerField(allow_null=True)
    previous_page = serializers.IntegerField(allow_null=True)
    results = CorrectionSerializer(many=True)


class CorrectionChangeSerializer(serializers.Serializer):
    field_name = serializers.CharField()
    proposed_value = serializers.JSONField(allow_null=True)


class CorrectionSubmitSerializer(serializers.Serializer):
    product = serializers.IntegerField(min_value=1, max_value=MAX_ID)
    items = CorrectionChangeSerializer(many=True)