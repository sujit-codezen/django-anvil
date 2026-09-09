import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from django_anvil.tenancy.models import Organization, OrganizationMembership

from ..models import Coupon

pytestmark = pytest.mark.django_db

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


def make_viewer(username):
    # This resource's "view" permission isn't public (see
    # test_..._permissions.py for RBAC coverage); these tests are about
    # tenancy, not authorization, so the viewer is a superuser to bypass
    # RBAC rather than needing a real grant.
    return User.objects.create_superuser(username=username, email=f"{username}@example.com", password="pass1234")


class TestCouponTenantIsolation:
    def test_list_excludes_other_organizations(self, api_client):
        payload_a = {'code': 'test-code', 'percent_off': 1, 'amount_off': '9.99', 'expires_at': '2026-01-01T00:00:00Z', 'max_uses': 1, 'is_active': True}
        payload_b = {'code': 'test-code-b', 'percent_off': 1, 'amount_off': '9.99', 'expires_at': '2026-01-01T00:00:00Z', 'max_uses': 1, 'is_active': True}
        org_a = Organization.objects.create(name="Org A", slug="org-a")
        org_b = Organization.objects.create(name="Org B", slug="org-b")
        product_a = Coupon.objects.create(organization=org_a, **payload_a)
        Coupon.objects.create(organization=org_b, **payload_b)

        user_a = make_viewer("tenant-user-a")
        OrganizationMembership.objects.create(user=user_a, organization=org_a)
        api_client.force_authenticate(user_a)

        response = api_client.get(reverse("coupons-list"))
        assert response.status_code == status.HTTP_200_OK
        assert {row["id"] for row in response.data} == {product_a.id}

    def test_cannot_retrieve_other_organizations_row(self, api_client):
        payload = {'code': 'test-code', 'percent_off': 1, 'amount_off': '9.99', 'expires_at': '2026-01-01T00:00:00Z', 'max_uses': 1, 'is_active': True}
        org_a = Organization.objects.create(name="Org A", slug="org-a")
        org_b = Organization.objects.create(name="Org B", slug="org-b")
        other_org_instance = Coupon.objects.create(organization=org_b, **payload)

        user_a = make_viewer("tenant-user-a2")
        OrganizationMembership.objects.create(user=user_a, organization=org_a)
        api_client.force_authenticate(user_a)

        response = api_client.get(reverse("coupons-detail", args=[other_org_instance.id]))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_no_membership_sees_nothing(self, api_client):
        payload = {'code': 'test-code', 'percent_off': 1, 'amount_off': '9.99', 'expires_at': '2026-01-01T00:00:00Z', 'max_uses': 1, 'is_active': True}
        org_a = Organization.objects.create(name="Org A", slug="org-a")
        Coupon.objects.create(organization=org_a, **payload)

        user_without_org = make_viewer("tenant-user-none")
        api_client.force_authenticate(user_without_org)

        response = api_client.get(reverse("coupons-list"))
        assert response.status_code == status.HTTP_200_OK
        assert list(response.data) == []
