import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from django_forge.tenancy.models import Organization, OrganizationMembership

from ..models import Coupon


@pytest.fixture
def test_organization(db):
    return Organization.objects.create(name="Test Org", slug="test-org")


@pytest.fixture
def api_client(test_organization):
    client = APIClient()
    # This resource has RBAC/tenancy rules (see the other generated test
    # files for those); this file only checks that the CRUD flow itself
    # works, so it runs as a superuser with organization membership to
    # bypass authorization concerns rather than testing them.
    user = get_user_model().objects.create_superuser(
        username="crud-test-admin", email="crud-test-admin@example.com", password="pass1234"
    )
    OrganizationMembership.objects.create(user=user, organization=test_organization)
    client.force_authenticate(user)
    return client


@pytest.mark.django_db
class TestCouponAPI:
    def test_list(self, api_client):
        response = api_client.get(reverse("coupons-list"))
        assert response.status_code == status.HTTP_200_OK

    def test_create_and_retrieve(self, api_client):
        payload = {'code': 'test-code', 'percent_off': 1, 'amount_off': '9.99', 'expires_at': '2026-01-01T00:00:00Z', 'max_uses': 1, 'is_active': True}
        create_response = api_client.post(reverse("coupons-list"), payload, format="json")
        assert create_response.status_code == status.HTTP_201_CREATED

        object_id = create_response.data["id"]
        detail_response = api_client.get(reverse("coupons-detail", args=[object_id]))
        assert detail_response.status_code == status.HTTP_200_OK

    def test_delete(self, api_client, test_organization):
        payload = {'code': 'test-code', 'percent_off': 1, 'amount_off': '9.99', 'expires_at': '2026-01-01T00:00:00Z', 'max_uses': 1, 'is_active': True}
        instance = Coupon.objects.create(organization=test_organization, **payload)
        response = api_client.delete(reverse("coupons-detail", args=[instance.id]))
        assert response.status_code == status.HTTP_204_NO_CONTENT
