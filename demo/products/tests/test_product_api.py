import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from django_anvil.tenancy.models import Organization, OrganizationMembership

from ..models import Product


@pytest.fixture
def test_organization(db):
    return Organization.objects.create(name="Test Org", slug="test-org")


@pytest.fixture
def test_actor(test_organization):
    # This resource has RBAC/tenancy/ownership rules (see the other
    # generated test files for those); this file only checks that the
    # CRUD flow itself works, so this one shared user is a superuser
    # (bypasses RBAC) who also owns/belongs-to anything created directly
    # below, rather than testing any of those rules itself.
    user = get_user_model().objects.create_superuser(
        username="crud-test-actor", email="crud-test-actor@example.com", password="pass1234"
    )
    OrganizationMembership.objects.create(user=user, organization=test_organization)
    return user


@pytest.fixture
def api_client(test_actor):
    client = APIClient()
    client.force_authenticate(test_actor)
    return client


@pytest.mark.django_db
class TestProductAPI:
    def test_list(self, api_client):
        response = api_client.get(reverse("products-list"))
        assert response.status_code == status.HTTP_200_OK

    def test_create_and_retrieve(self, api_client):
        payload = {'name': 'test-name', 'price': '9.99', 'stock': 1, 'is_active': True}
        create_response = api_client.post(reverse("products-list"), payload, format="json")
        assert create_response.status_code == status.HTTP_201_CREATED

        object_id = create_response.data["id"]
        detail_response = api_client.get(reverse("products-detail", args=[object_id]))
        assert detail_response.status_code == status.HTTP_200_OK

    def test_delete(self, api_client, test_organization):
        payload = {'name': 'test-name', 'price': '9.99', 'stock': 1, 'is_active': True}
        instance = Product.objects.create(organization=test_organization, **payload)
        response = api_client.delete(reverse("products-detail", args=[instance.id]))
        assert response.status_code == status.HTTP_204_NO_CONTENT
