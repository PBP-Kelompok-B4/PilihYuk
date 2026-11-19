from rest_framework import serializers

from .forms import DecisionForm
from .models import Decision, Preference

MAX_ID = 9223372036854775807


class PreferenceSerializer(serializers.ModelSerializer):
    nutrient_label = serializers.CharField(source="get_nutrient_display", read_only=True)

    class Meta:
        model = Preference
        fields = ("id", "nutrient", "nutrient_label", "direction", "weight")
        # Uniqueness is scoped to the authenticated user, who is not an input field.
        validators = []

    def get_fields(self):
        fields = super().get_fields()
        if isinstance(self.instance, Preference):
            fields["nutrient"].required = False
        return fields

    def validate_nutrient(self, value):
        if self.instance:
            if value != self.instance.nutrient:
                raise serializers.ValidationError("Nutrien tidak bisa diubah.")
        elif Preference.objects.filter(user=self.context["request"].user, nutrient=value).exists():
            raise serializers.ValidationError("Preferensi nutrien ini sudah aktif.")
        return value


class DecisionSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(min_value=1, max_value=MAX_ID, required=False)
    shelf_id = serializers.IntegerField(min_value=1, max_value=MAX_ID, required=False, allow_null=True)
    compared_product_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1, max_value=MAX_ID),
        min_length=1, max_length=4, required=False, write_only=True,
    )
    note = serializers.CharField(required=False, allow_blank=True, max_length=500, trim_whitespace=False)

    class Meta:
        model = Decision
        fields = ("id", "product_id", "shelf_id", "note", "compared_product_count",
                  "created_at", "compared_product_ids")
        read_only_fields = ("compared_product_count", "created_at")

    def validate(self, attrs):
        if self.instance:
            errors = {field: "Field ini tidak bisa diubah." for field in attrs.keys() - {"note"}}
            if errors:
                raise serializers.ValidationError(errors)
            data = {"note": attrs.get("note", self.instance.note)}
        else:
            data = {key: value for key, value in attrs.items() if key not in ("product_id", "shelf_id")}
            data.update(product=attrs.get("product_id"), shelf=attrs.get("shelf_id"))
        # The existing form enforces shelf visibility, product membership, and snapshot rules.
        self.form = DecisionForm(data=data, instance=self.instance, user=self.context["request"].user)
        if not self.form.is_valid():
            aliases = {"product": "product_id", "shelf": "shelf_id"}
            raise serializers.ValidationError({
                aliases.get(key, key): messages for key, messages in self.form.errors.items()
            })
        return attrs

    def create(self, validated_data):
        return self.form.save()

    def update(self, instance, validated_data):
        return self.form.save()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        user = self.context["request"].user
        product = instance.product
        shelf = instance.shelf
        if not product or not product.is_active:
            data["product_id"] = None
            product = None
        if shelf and shelf.is_private and shelf.owner_id != user.pk:
            data["shelf_id"] = None
            shelf = None
        data.update(
            product_name=product.product_name if product else "Tidak diketahui",
            brand=product.brand if product else "",
            quantity=product.quantity if product else "",
            image_url=product.image_url if product else "",
            shelf_name=shelf.name if shelf else "Tidak diketahui",
        )
        return data


class BulkDeleteSerializer(serializers.Serializer):
    ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1, max_value=MAX_ID),
        min_length=1, max_length=100,
    )

    def validate_ids(self, value):
        return list(dict.fromkeys(value))
