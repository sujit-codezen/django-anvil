import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from django_forge.rbac.models import Role

from ..models import Review

pytestmark = pytest.mark.django_db

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


class TestReviewPermissions:
    def test_anonymous_denied_on_view(self, api_client):
        response = api_client.get(reverse("reviews-list"))
        assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    def test_granted_user_can_view(self, api_client):
        # Created before the instance below: with OwnerScopedViewSetMixin,
        # a user can only reach rows they own, so the granted user has to
        # be the same one who owns whatever gets created here.
        user = User.objects.create_user(username="view-role-user", password="pass1234")
        api_client.force_authenticate(user)
        response = api_client.get(reverse("reviews-list"))
        assert response.status_code not in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    def test_anonymous_denied_on_create(self, api_client):
        payload = {'rating': 1, 'comment': 'test-comment'}
        response = api_client.post(reverse("reviews-list"), payload, format="json")
        assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    def test_granted_user_can_create(self, api_client):
        # Created before the instance below: with OwnerScopedViewSetMixin,
        # a user can only reach rows they own, so the granted user has to
        # be the same one who owns whatever gets created here.
        user = User.objects.create_user(username="create-role-user", password="pass1234")
        payload = {'rating': 1, 'comment': 'test-comment'}
        api_client.force_authenticate(user)
        response = api_client.post(reverse("reviews-list"), payload, format="json")
        assert response.status_code not in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    def test_anonymous_denied_on_update(self, api_client):
        instance_owner = User.objects.create_user(username="update-instance-owner", password="pass1234")
        payload = {'rating': 1, 'comment': 'test-comment'}
        instance = Review.objects.create(owner=instance_owner, **payload)
        response = api_client.patch(reverse("reviews-detail", args=[instance.id]), payload, format="json")
        assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    def test_granted_user_can_update(self, api_client):
        # Created before the instance below: with OwnerScopedViewSetMixin,
        # a user can only reach rows they own, so the granted user has to
        # be the same one who owns whatever gets created here.
        user = User.objects.create_user(username="update-role-user", password="pass1234")
        payload = {'rating': 1, 'comment': 'test-comment'}
        instance = Review.objects.create(owner=user, **payload)
        api_client.force_authenticate(user)
        response = api_client.patch(reverse("reviews-detail", args=[instance.id]), payload, format="json")
        assert response.status_code not in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    def test_anonymous_denied_on_delete(self, api_client):
        instance_owner = User.objects.create_user(username="delete-instance-owner", password="pass1234")
        payload = {'rating': 1, 'comment': 'test-comment'}
        instance = Review.objects.create(owner=instance_owner, **payload)
        response = api_client.delete(reverse("reviews-detail", args=[instance.id]))
        assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    def test_granted_user_can_delete(self, api_client):
        # Created before the instance below: with OwnerScopedViewSetMixin,
        # a user can only reach rows they own, so the granted user has to
        # be the same one who owns whatever gets created here.
        user = User.objects.create_user(username="delete-role-user", password="pass1234")
        payload = {'rating': 1, 'comment': 'test-comment'}
        instance = Review.objects.create(owner=user, **payload)
        api_client.force_authenticate(user)
        response = api_client.delete(reverse("reviews-detail", args=[instance.id]))
        assert response.status_code not in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

