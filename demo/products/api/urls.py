from rest_framework.routers import DefaultRouter

from .views import CouponViewSet, ProductViewSet, ReviewViewSet, TagViewSet

router = DefaultRouter()
router.register(r"products", ProductViewSet, basename="products")
router.register(r"coupons", CouponViewSet, basename="coupons")
router.register(r"reviews", ReviewViewSet, basename="reviews")
router.register(r"tags", TagViewSet, basename="tags")

urlpatterns = router.urls
