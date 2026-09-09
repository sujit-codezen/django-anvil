from rest_framework import serializers
from django_forge.mixins import TimestampedSerializerMixin

from ..models import Coupon, Product, Review, Tag


class ProductSerializer(TimestampedSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name', 'price', 'stock', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = ['id', 'code', 'percent_off', 'amount_off', 'expires_at', 'max_uses', 'times_used', 'is_active', 'created_at']
        read_only_fields = ['id', 'times_used', 'created_at']


class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ['id', 'owner', 'rating', 'comment', 'created_at']
        read_only_fields = ['id', 'owner', 'created_at']


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'slug']
        read_only_fields = ['id']
