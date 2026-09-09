import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from ..models import Review


@pytest.fixture
def test_actor():
    # This resource has RBAC/tenancy/ownership rules (see the other
    # generated test files for those); this file only checks that the
    # CRUD flow itself works, so this one shared user is a superuser
    # (bypasses RBAC) who also owns/belongs-to anything created directly
    # below, rather than testing any of those rules itself.
    user = get_user_model().objects.create_superuser(
        username="crud-test-actor", email="crud-test-actor@example.com", password="pass1234"
    )
    return user


@pytest.fixture
def api_client(test_actor):
    client = APIClient()
    client.force_authenticate(test_actor)
    return client


@pytest.mark.django_db
class TestReviewAPI:
    def test_list(self, api_client):
        response = api_client.get(reverse("reviews-list"))
        assert response.status_code == status.HTTP_200_OK

    def test_create_and_retrieve(self, api_client):
        payload = {'rating': 1, 'comment': 'test-comment'}
        create_response = api_client.post(reverse("reviews-list"), payload, format="json")
        assert create_response.status_code == status.HTTP_201_CREATED

        object_id = create_response.data["id"]
        detail_response = api_client.get(reverse("reviews-detail", args=[object_id]))
        assert detail_response.status_code == status.HTTP_200_OK

    def test_delete(self, api_client, test_actor):
        payload = {'rating': 1, 'comment': 'test-comment'}
        instance = Review.objects.create(owner=test_actor, **payload)
        response = api_client.delete(reverse("reviews-detail", args=[instance.id]))
        assert response.status_code == status.HTTP_204_NO_CONTENT
