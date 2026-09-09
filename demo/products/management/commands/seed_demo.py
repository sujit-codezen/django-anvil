"""Populates the demo project with enough realistic data to explore every
Anvil feature by hand -- in the admin, in the browsable API, or with curl.
Safe to re-run: everything is get_or_create'd.
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from django_anvil.rbac.models import Role
from django_anvil.tenancy.models import Organization, OrganizationMembership
from products.models import Coupon, Product, Review, Tag

User = get_user_model()

DEMO_PASSWORD = "demo-pass-1234"


class Command(BaseCommand):
    help = "Seed the demo project: orgs, roles, users, products, coupons, reviews."

    def handle(self, *args, **options):
        admin = self._seed_superuser()
        acme, globex = self._seed_organizations()
        manager_role, staff_role = self._seed_roles()
        alice, bob, carol, dave = self._seed_users(acme, globex, manager_role, staff_role)
        self._seed_products(acme, globex)
        self._seed_coupons(acme, globex)
        self._seed_reviews(alice, bob)
        self._seed_tags(acme, globex)

        self.stdout.write(self.style.SUCCESS("Demo data ready."))
        self.stdout.write("")
        self.stdout.write(f"Admin login:  admin / {DEMO_PASSWORD}  (http://127.0.0.1:8000/admin/)")
        self.stdout.write(f"Acme Manager: alice / {DEMO_PASSWORD}  (sees only Acme's Products/Coupons/Tags, full CRUD)")
        self.stdout.write(f"Globex Manager: bob / {DEMO_PASSWORD}  (sees only Globex's, full CRUD)")
        self.stdout.write(f"Acme Staff:   carol / {DEMO_PASSWORD}  (Acme, view-only -- create/update/delete all 403)")
        self.stdout.write(f"No org:       dave / {DEMO_PASSWORD}  (sees nothing -- tenancy fails closed)")
        self.stdout.write("")
        self.stdout.write("Try, e.g.:")
        self.stdout.write("  curl http://127.0.0.1:8000/api/products/")
        self.stdout.write(
            "  curl -u alice:" + DEMO_PASSWORD + " -X POST http://127.0.0.1:8000/api/products/ "
            "-d 'name=New&price=1&stock=1&is_active=true'"
        )

    def _seed_superuser(self):
        admin, created = User.objects.get_or_create(username="admin", defaults={"is_staff": True, "is_superuser": True})
        if created:
            admin.set_password(DEMO_PASSWORD)
            admin.save()
        return admin

    def _seed_organizations(self):
        acme, _ = Organization.objects.get_or_create(slug="acme", defaults={"name": "Acme Inc"})
        globex, _ = Organization.objects.get_or_create(slug="globex", defaults={"name": "Globex Corp"})
        return acme, globex

    def _seed_roles(self):
        manager_role, _ = Role.objects.get_or_create(name="Manager")
        manager_role.grant(
            "products.add_product", "products.change_product", "products.delete_product",
            "products.view_coupon", "products.add_coupon", "products.change_coupon", "products.delete_coupon",
            "products.add_tag", "products.change_tag", "products.delete_tag",
        )

        staff_role, _ = Role.objects.get_or_create(name="Staff")
        staff_role.grant("products.view_coupon")

        return manager_role, staff_role

    def _seed_users(self, acme, globex, manager_role, staff_role):
        def make_user(username, organization, role):
            user, created = User.objects.get_or_create(username=username)
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save()
            if role:
                user.groups.add(role)
            if organization:
                OrganizationMembership.objects.get_or_create(user=user, organization=organization)
            return user

        alice = make_user("alice", acme, manager_role)
        bob = make_user("bob", globex, manager_role)
        carol = make_user("carol", acme, staff_role)
        dave = make_user("dave", None, None)
        return alice, bob, carol, dave

    def _seed_products(self, acme, globex):
        # .all_objects, not .objects: this runs with no request/current-
        # organization context, so the tenant-scoped default manager
        # would fail closed and see zero existing rows every time --
        # exactly the footgun all_objects exists to avoid in scripts.
        Product.all_objects.get_or_create(
            organization=acme, name="Acme Widget",
            defaults={"price": "19.99", "stock": 100, "is_active": True},
        )
        Product.all_objects.get_or_create(
            organization=acme, name="Acme Anvil",
            defaults={"price": "249.99", "stock": 5, "is_active": True},
        )
        Product.all_objects.get_or_create(
            organization=globex, name="Globex Gadget",
            defaults={"price": "49.99", "stock": 30, "is_active": True},
        )

    def _seed_coupons(self, acme, globex):
        Coupon.all_objects.get_or_create(
            organization=acme, code="ACME10",
            defaults={"percent_off": 10, "is_active": True},
        )
        Coupon.all_objects.get_or_create(
            organization=globex, code="GLOBEX20",
            defaults={"percent_off": 20, "is_active": True},
        )

    def _seed_reviews(self, alice, bob):
        Review.objects.get_or_create(
            owner=alice, defaults={"rating": 5, "comment": "Solid widget, does the job."}
        )
        Review.objects.get_or_create(
            owner=bob, defaults={"rating": 2, "comment": "Gadget broke after a week."}
        )

    def _seed_tags(self, acme, globex):
        Tag.all_objects.get_or_create(organization=acme, name="Hardware", defaults={"slug": "hardware"})
        Tag.all_objects.get_or_create(organization=acme, name="On Sale", defaults={"slug": "on-sale"})
        Tag.all_objects.get_or_create(organization=globex, name="Gadgets", defaults={"slug": "gadgets"})
