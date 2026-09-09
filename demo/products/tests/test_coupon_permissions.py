import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from django_anvil.rbac.models import Role
from django_anvil.tenancy.models import Organization, OrganizationMembership

from ..models import Coupon

pytestmark = pytest.mark.django_db

User = get_user_model()


@pytest.fixture
def test_organization(db):
    return Organization.objects.create(name="Test Org", slug="test-org")


@pytest.fixture
def api_client():
    return APIClient()


class TestCouponPermissions:
    def test_anonymous_denied_on_view(self, api_client):
        response = api_client.get(reverse("coupons-list"))
        assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    def test_granted_user_can_view(self, api_client, test_organization):
        # Created before the instance below: with OwnerScopedViewSetMixin,
        # a user can only reach rows they own, so the granted user has to
        # be the same one who owns whatever gets created here.
        user = User.objects.create_user(username="view-role-user", password="pass1234")
        OrganizationMembership.objects.create(user=user, organization=test_organization)
        role = Role.objects.create(name="Coupon view role")
        role.grant("products.view_coupon")
        user.groups.add(role)
        api_client.force_authenticate(user)
        response = api_client.get(reverse("coupons-list"))
        assert response.status_code not in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    def test_anonymous_denied_on_create(self, api_client):
        payload = {'code': 'test-code', 'percent_off': 1, 'amount_off': '9.99', 'expires_at': '2026-01-01T00:00:00Z', 'max_uses': 1, 'is_active': True}
        response = api_client.post(reverse("coupons-list"), payload, format="json")
        assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    def test_granted_user_can_create(self, api_client, test_organization):
        # Created before the instance below: with OwnerScopedViewSetMixin,
        # a user can only reach rows they own, so the granted user has to
        # be the same one who owns whatever gets created here.
        user = User.objects.create_user(username="create-role-user", password="pass1234")
        OrganizationMembership.objects.create(user=user, organization=test_organization)
        role = Role.objects.create(name="Coupon create role")
        role.grant("products.add_coupon")
        user.groups.add(role)
        payload = {'code': 'test-code', 'percent_off': 1, 'amount_off': '9.99', 'expires_at': '2026-01-01T00:00:00Z', 'max_uses': 1, 'is_active': True}
        api_client.force_authenticate(user)
        response = api_client.post(reverse("coupons-list"), payload, format="json")
        assert response.status_code not in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    def test_anonymous_denied_on_update(self, api_client, test_organization):
        payload = {'code': 'test-code', 'percent_off': 1, 'amount_off': '9.99', 'expires_at': '2026-01-01T00:00:00Z', 'max_uses': 1, 'is_active': True}
        instance = Coupon.objects.create(organization=test_organization, **payload)
        response = api_client.patch(reverse("coupons-detail", args=[instance.id]), payload, format="json")
        assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    def test_granted_user_can_update(self, api_client, test_organization):
        # Created before the instance below: with OwnerScopedViewSetMixin,
        # a user can only reach rows they own, so the granted user has to
        # be the same one who owns whatever gets created here.
        user = User.objects.create_user(username="update-role-user", password="pass1234")
        OrganizationMembership.objects.create(user=user, organization=test_organization)
        role = Role.objects.create(name="Coupon update role")
        role.grant("products.change_coupon")
        user.groups.add(role)
        payload = {'code': 'test-code', 'percent_off': 1, 'amount_off': '9.99', 'expires_at': '2026-01-01T00:00:00Z', 'max_uses': 1, 'is_active': True}
        instance = Coupon.objects.create(organization=test_organization, **payload)
        api_client.force_authenticate(user)
        response = api_client.patch(reverse("coupons-detail", args=[instance.id]), payload, format="json")
        assert response.status_code not in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    def test_anonymous_denied_on_delete(self, api_client, test_organization):
        payload = {'code': 'test-code', 'percent_off': 1, 'amount_off': '9.99', 'expires_at': '2026-01-01T00:00:00Z', 'max_uses': 1, 'is_active': True}
        instance = Coupon.objects.create(organization=test_organization, **payload)
        response = api_client.delete(reverse("coupons-detail", args=[instance.id]))
        assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    def test_granted_user_can_delete(self, api_client, test_organization):
        # Created before the instance below: with OwnerScopedViewSetMixin,
        # a user can only reach rows they own, so the granted user has to
        # be the same one who owns whatever gets created here.
        user = User.objects.create_user(username="delete-role-user", password="pass1234")
        OrganizationMembership.objects.create(user=user, organization=test_organization)
        role = Role.objects.create(name="Coupon delete role")
        role.grant("products.delete_coupon")
        user.groups.add(role)
        payload = {'code': 'test-code', 'percent_off': 1, 'amount_off': '9.99', 'expires_at': '2026-01-01T00:00:00Z', 'max_uses': 1, 'is_active': True}
        instance = Coupon.objects.create(organization=test_organization, **payload)
        api_client.force_authenticate(user)
        response = api_client.delete(reverse("coupons-detail", args=[instance.id]))
        assert response.status_code not in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

