"""The Resource base class: the single declarative definition that the
generator turns into a serializer, a viewset, admin registration, and a
test file.
"""

from django_forge.core.registry import registry


class Resource:
    """Subclass this once per model to describe its generated API.

    Example:

        class ProductResource(Resource):
            model = Product
            fields = ["name", "price", "stock", "is_active"]
            read_only_fields = ["id", "created_at", "updated_at"]
            searchable = ["name"]
            filters = ["is_active"]
            sortable = ["price", "created_at"]
            mixins = []
            permissions = {}       # wired up by the RBAC module (phase 2)
            tenant_scoped = False  # wired up by the tenancy module (phase 3)
            audited = False        # wired up by the audit module (phase 5)
    """

    # Set by the subclass — the model this resource describes.
    model = None

    fields: list = []
    read_only_fields: list = []
    searchable: list = []
    filters: list = []
    sortable: list = []
    mixins: list = []
    permissions: dict = {}
    tenant_scoped: bool = False
    audited: bool = False

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        # Resource itself has no model; only real subclasses register.
        if cls.model is None:
            return

        registry.register(cls)

    @classmethod
    def app_label(cls):
        return cls.model._meta.app_label

    @classmethod
    def model_name(cls):
        return cls.model.__name__

    @classmethod
    def all_field_names(cls):
        """fields + read_only_fields, de-duplicated, order preserved."""
        seen = []
        for name in (*cls.fields, *cls.read_only_fields):
            if name not in seen:
                seen.append(name)
        return seen
