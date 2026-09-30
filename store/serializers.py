from rest_framework import serializers

from .models import Order, Product, StoreContent


class ProductSerializer(serializers.ModelSerializer):
    localized_name = serializers.SerializerMethodField()
    localized_description = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "name_en",
            "description",
            "description_en",
            "localized_name",
            "localized_description",
            "price",
            "image",
            "available",
            "stock",
            "created_at",
        )
        read_only_fields = ("id", "localized_name", "localized_description", "created_at")

    def get_localized_name(self, product):
        request = self.context.get("request")
        language = getattr(request, "LANGUAGE_CODE", "ar")
        return product.name_en if language == "en" and product.name_en else product.name

    def get_localized_description(self, product):
        request = self.context.get("request")
        language = getattr(request, "LANGUAGE_CODE", "ar")
        return product.description_en if language == "en" and product.description_en else product.description


class AdminOrderSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    item_count = serializers.SerializerMethodField()

    def get_item_count(self, order):
        return order.items.count()

    class Meta:
        model = Order
        fields = (
            "id",
            "username",
            "full_name",
            "phone",
            "city",
            "address",
            "notes",
            "subtotal",
            "shipping_fee",
            "total",
            "status",
            "payment_status",
            "item_count",
            "created_at",
        )
        read_only_fields = (
            "id",
            "username",
            "full_name",
            "phone",
            "city",
            "address",
            "notes",
            "subtotal",
            "shipping_fee",
            "total",
            "payment_status",
            "item_count",
            "created_at",
        )


class StoreContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreContent
        fields = (
            "hero_title_ar",
            "hero_title_en",
            "hero_description_ar",
            "hero_description_en",
            "story_title_ar",
            "story_title_en",
            "story_description_ar",
            "story_description_en",
        )
