from django.contrib import admin

from .models import Coupon, Product, Review, Tag
from simple_history.admin import SimpleHistoryAdmin

# Register your models here.


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'price', 'stock', 'is_active', 'created_at']
    search_fields = ['name']
    list_filter = ['is_active']

    def get_queryset(self, request):
        # Admin is a global surface: show every organization's rows here,
        # not just whichever one (if any) the logged-in staff user belongs to.
        return Product.all_objects.all()


@admin.register(Coupon)
class CouponAdmin(SimpleHistoryAdmin):
    list_display = ['id', 'code', 'percent_off', 'amount_off', 'expires_at', 'max_uses']
    search_fields = ['code']
    list_filter = ['is_active']

    def get_queryset(self, request):
        # Admin is a global surface: show every organization's rows here,
        # not just whichever one (if any) the logged-in staff user belongs to.
        return Coupon.all_objects.all()


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['id', 'owner', 'rating', 'comment', 'created_at']
    list_filter = ['rating']


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'slug']
    search_fields = ['name']

    def get_queryset(self, request):
        # Admin is a global surface: show every organization's rows here,
        # not just whichever one (if any) the logged-in staff user belongs to.
        return Tag.all_objects.all()
