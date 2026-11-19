from rest_framework import serializers

from .models import Shelf
from .views import owner_name


class ShelfSerializer(serializers.ModelSerializer):
    owner = serializers.SerializerMethodField()
    item_count = serializers.IntegerField(read_only=True)
    save_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Shelf
        fields = ["id", "name", "store_context", "description", "is_private", "owner",
                  "item_count", "save_count", "updated_at"]

    def get_owner(self, shelf):
        return owner_name(shelf.owner)
