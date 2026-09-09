"""Keeps track of every Resource subclass that has been defined.

A Resource registers itself the moment its class body finishes executing
(see Resource.__init_subclass__), the same way Django's admin.site.register
works, just automatic instead of explicit.
"""


class ResourceRegistry:
    def __init__(self):
        self._by_model = {}

    def register(self, resource_cls):
        model = resource_cls.model
        if model in self._by_model:
            existing = self._by_model[model]
            raise ValueError(
                f"{model.__name__} already has a registered resource "
                f"({existing.__name__}). Only one Resource per model is allowed."
            )
        self._by_model[model] = resource_cls

    def get_for_model(self, model):
        try:
            return self._by_model[model]
        except KeyError:
            raise LookupError(
                f"No Resource is registered for {model.__name__}. "
                f"Define one in <app>/resources.py, e.g.\n\n"
                f"    class {model.__name__}Resource(Resource):\n"
                f"        model = {model.__name__}\n"
                f"        fields = [...]\n"
            ) from None

    def all(self):
        return list(self._by_model.values())


registry = ResourceRegistry()
