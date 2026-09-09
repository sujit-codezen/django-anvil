from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework.viewsets import ModelViewSet
from django_forge.mixins import OwnerScopedViewSetMixin, SoftDeleteViewSetMixin, TenantScopedViewSetMixin
from django_forge.rbac.permissions import ResourcePermission

from ..models import Coupon, Product, Review, Tag
from .serializers import CouponSerializer, ProductSerializer, ReviewSerializer, TagSerializer


class ProductViewSet(SoftDeleteViewSetMixin, TenantScopedViewSetMixin, ModelViewSet):
    serializer_class = ProductSerializer
    # No `queryset` attribute: TenantScopedViewSetMixin.get_queryset() calls
    # Product.objects.all() fresh per request instead -- see its docstring.
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name']
    ordering_fields = ['price', 'created_at']
    permission_classes = [ResourcePermission]
    permission_map = {
        'view': 'public',
        'create': 'products.add_product',
        'update': 'products.change_product',
        'delete': 'products.delete_product',
    }


class CouponViewSet(TenantScopedViewSetMixin, ModelViewSet):
    serializer_class = CouponSerializer
    # No `queryset` attribute: TenantScopedViewSetMixin.get_queryset() calls
    # Coupon.objects.all() fresh per request instead -- see its docstring.
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['code']
    ordering_fields = ['expires_at', 'created_at']
    permission_classes = [ResourcePermission]
    permission_map = {
        'view': 'products.view_coupon',
        'create': 'products.add_coupon',
        'update': 'products.change_coupon',
        'delete': 'products.delete_coupon',
    }


class ReviewViewSet(OwnerScopedViewSetMixin, ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['rating']
    ordering_fields = ['created_at', 'rating']
    permission_classes = [ResourcePermission]
    permission_map = {
        'view': 'authenticated',
        'create': 'authenticated',
        'update': 'authenticated',
        'delete': 'authenticated',
    }


class TagViewSet(TenantScopedViewSetMixin, ModelViewSet):
    serializer_class = TagSerializer
    # No `queryset` attribute: TenantScopedViewSetMixin.get_queryset() calls
    # Tag.objects.all() fresh per request instead -- see its docstring.
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name']
    permission_classes = [ResourcePermission]
    permission_map = {
        'view': 'public',
        'create': 'products.add_tag',
        'update': 'products.change_tag',
        'delete': 'products.delete_tag',
    }
