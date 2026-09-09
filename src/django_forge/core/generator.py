"""Turns a Resource subclass into real files: a serializer, a viewset, a
router urls.py, an admin registration, and a starter pytest file.

serializers.py, views.py, admin.py and urls.py are all *shared, per-app*
files -- an app with two Resources (Product and Coupon, say) gets both
classes in the same serializers.py, the way a person would write it by
hand. So every write to one of those goes through `_write_class_block`
(add this Resource's class, leaving any others in the file alone) or, for
urls.py specifically, `_write_router_registration`. Model-specific test
files are the exception: each Resource gets its own, via `_write_new`
(refuses to clobber a file that already has real content unless forced).
"""

import re
from pathlib import Path

from django.apps import apps
from jinja2 import Environment, FileSystemLoader

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    trim_blocks=True,
    lstrip_blocks=True,
    keep_trailing_newline=True,
)


def _render(template_name, **context):
    return _env.get_template(template_name).render(**context)


def _group_mixin_imports(mixin_classes) -> list[str]:
    """One `from X import A, B` line per module, not one line per class
    -- matches how a person would write these imports by hand.
    """
    modules: dict[str, list[str]] = {}
    for cls in mixin_classes:
        modules.setdefault(cls.__module__, []).append(cls.__name__)
    return [f"from {module} import {', '.join(names)}" for module, names in modules.items()]


def _format_dict_literal(mapping: dict, base_indent: int = 4) -> str:
    """A dict literal short enough to fit on one line stays inline;
    anything longer gets one key per line, like a human reformatting a
    line that ran past the margin.
    """
    if not mapping:
        return "{}"

    inline = repr(mapping)
    if len(inline) + base_indent <= 88:
        return inline

    pad = " " * base_indent
    item_pad = " " * (base_indent + 4)
    items = ",\n".join(f"{item_pad}{key!r}: {value!r}" for key, value in mapping.items())
    return "{\n" + items + f",\n{pad}}}"


def _split_mixins(resource):
    """A Resource's `mixins` list can hold serializer mixins and viewset
    mixins together; sort them by naming convention so each generated
    file only inherits the ones meant for it.
    """
    serializer_mixins = [m for m in resource.mixins if m.__name__.endswith("SerializerMixin")]
    viewset_mixins = [m for m in resource.mixins if m.__name__.endswith("ViewSetMixin")]
    unrecognised = [m for m in resource.mixins if m not in serializer_mixins and m not in viewset_mixins]
    if unrecognised:
        names = ", ".join(m.__name__ for m in unrecognised)
        raise ValueError(
            f"Can't tell where these mixins belong: {names}. "
            f"Name mixins ending in 'SerializerMixin' or 'ViewSetMixin' "
            f"so the generator knows which generated class to attach them to."
        )
    return serializer_mixins, viewset_mixins


def _app_dir(resource):
    app_config = apps.get_app_config(resource.app_label())
    return Path(app_config.path)


def _write_new(path: Path, content: str, force: bool = False) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    init_file = path.parent / "__init__.py"
    if not init_file.exists():
        init_file.write_text("")

    if path.exists() and path.read_text().strip() and not force:
        return False

    path.write_text(content)
    return True


def _append_once(path: Path, content: str, marker: str) -> bool:
    """Append `content` to `path` unless `marker` is already in the file."""
    path.parent.mkdir(parents=True, exist_ok=True)

    if not path.exists():
        path.write_text(content)
        return True

    existing = path.read_text()
    if marker in existing:
        return False

    separator = "\n\n" if existing and not existing.endswith("\n\n") else ""
    path.write_text(existing + separator + content)
    return True


_FROM_IMPORT_RE = re.compile(r"^from (?P<module>\S+) import (?P<names>.+)$")


def _import_block_end(lines: list[str]) -> int:
    """Index right after the file's leading run of import/blank lines."""
    insert_at = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("import ") or stripped.startswith("from "):
            insert_at = i + 1
        elif stripped == "":
            continue
        else:
            break
    return insert_at


def _ensure_imports(path: Path, import_lines: list[str]) -> None:
    """Make sure each of `import_lines` is covered by the file, without
    duplicating anything the file (e.g. Django's `startapp` stub
    admin.py, or an earlier Resource's generated imports) already has.

    A `from X import A` request folds into an existing `from X import B`
    line as `from X import A, B` instead of being added as a second,
    separate line -- otherwise generating a second Resource into the
    same app would leave two `from ..models import ...` lines behind.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    init_file = path.parent / "__init__.py"
    if not init_file.exists():
        init_file.write_text("")

    lines = path.read_text().splitlines() if path.exists() else []

    for import_line in import_lines:
        match = _FROM_IMPORT_RE.match(import_line)
        if not match:
            if import_line not in lines:
                _insert_import_line(lines, import_line)
            continue

        module = match.group("module")
        wanted_names = [n.strip() for n in match.group("names").split(",")]

        existing_index = next(
            (i for i, line in enumerate(lines) if _FROM_IMPORT_RE.match(line, 0) and _FROM_IMPORT_RE.match(line).group("module") == module),
            None,
        )
        if existing_index is None:
            _insert_import_line(lines, import_line)
            continue

        existing_names = [n.strip() for n in _FROM_IMPORT_RE.match(lines[existing_index]).group("names").split(",")]
        merged_names = sorted(set(existing_names) | set(wanted_names))
        lines[existing_index] = f"from {module} import {', '.join(merged_names)}"

    path.write_text("\n".join(lines) + "\n")


def _insert_import_line(lines: list[str], import_line: str) -> None:
    """Inserts at the end of the import block, adding a blank line ahead
    of it first if it's a relative import (`from .` / `from ..`) landing
    right after a non-relative one -- the usual stdlib/third-party vs.
    local-code grouping a person would use, that isort would also apply.
    """
    insert_at = _import_block_end(lines)
    is_relative = import_line.startswith("from .")
    if is_relative and insert_at > 0 and not lines[insert_at - 1].startswith("from ."):
        lines.insert(insert_at, "")
        insert_at += 1
    lines.insert(insert_at, import_line)


def _remove_block(lines: list[str], marker: str) -> list[str]:
    """Removes the block starting at the line containing `marker` (e.g.
    "class ProductSerializer(...):"), up to the next top-level line, plus
    any blank lines surrounding it -- so re-appending a fresh block in
    its place doesn't leave a stray extra blank line behind.
    """
    start = next(i for i, line in enumerate(lines) if marker in line)
    end = start + 1
    while end < len(lines) and (lines[end].startswith((" ", "\t")) or lines[end].strip() == ""):
        end += 1
    while end > start + 1 and lines[end - 1].strip() == "":
        end -= 1
    while start > 0 and lines[start - 1].strip() == "":
        start -= 1
    return lines[:start] + lines[end:]


def _status_note(status: str, path: Path) -> str:
    if status == "created":
        return f"created {path}"
    if status in ("updated", "appended"):
        return f"updated {path}"
    return f"skipped {path} (already has this Resource's block, use --force to overwrite)"


def _write_class_block(path: Path, import_lines: list[str], class_body: str, marker: str, force: bool) -> str:
    """Ensures `import_lines` are present, then ensures a class block
    starting with `marker` exists in `path`: appends it if this Resource
    doesn't have one yet, replaces it (moving it to the end of the file)
    if it does and `force=True`, or leaves the file untouched otherwise.
    Returns "created" (brand new file), "appended" (added alongside an
    existing Resource's block), "updated" (this Resource's own block was
    replaced), or "skipped".
    """
    file_already_had_content = path.exists() and bool(path.read_text().strip())

    _ensure_imports(path, import_lines)
    existing_text = path.read_text() if path.exists() else ""

    if marker not in existing_text:
        _append_once(path, class_body, marker)
        return "appended" if file_already_had_content else "created"

    if not force:
        return "skipped"

    lines = _remove_block(existing_text.splitlines(), marker)
    path.write_text("\n".join(lines).rstrip("\n") + "\n")
    _append_once(path, class_body, marker)
    return "updated"


def _write_router_registration(path: Path, model_name: str, url_prefix: str, force: bool) -> str:
    """urls.py holds one shared DefaultRouter for the whole app; each
    Resource contributes one `router.register(...)` line to it. Returns
    "created" (file didn't exist yet), "appended" (added alongside
    another Resource's registration), "updated" (this Resource's own
    registration was moved to the end, force=True), or "skipped".
    """
    register_line = f'router.register(r"{url_prefix}", {model_name}ViewSet, basename="{url_prefix}")'

    if not path.exists() or not path.read_text().strip():
        content = _render("urls.py.jinja", model_name=model_name, url_prefix=url_prefix)
        _write_new(path, content)
        return "created"

    existing_text = path.read_text()
    if register_line in existing_text:
        if not force:
            return "skipped"
        lines = [line for line in existing_text.splitlines() if line.strip() != register_line]
        path.write_text("\n".join(lines) + "\n")
        existing_text = path.read_text()
        status = "updated"
    else:
        status = "appended"

    _ensure_imports(path, [f"from .views import {model_name}ViewSet"])
    lines = path.read_text().splitlines()
    register_line_indices = [i for i, line in enumerate(lines) if line.strip().startswith("router.register(")]
    if register_line_indices:
        insert_at = register_line_indices[-1] + 1
    else:
        insert_at = next(i for i, line in enumerate(lines) if line.strip().startswith("router = DefaultRouter()")) + 1
    lines.insert(insert_at, register_line)
    path.write_text("\n".join(lines) + "\n")
    return status


_DJANGO_DEFAULT_TESTS_STUB = "from django.test import TestCase\n\n# Create your tests here."


def _resolve_tests_stub(app_dir: Path) -> str | None:
    """`django-admin startapp` creates app/tests.py. We generate a
    app/tests/ package instead, and Python can't have both a `tests.py`
    module and a `tests/` package side by side -- it breaks Django's own
    test runner. Remove the stub if it's untouched; otherwise leave it
    alone and report the conflict instead of deleting real work.
    """
    stub_path = app_dir / "tests.py"
    package_path = app_dir / "tests"

    if not stub_path.exists() or package_path.exists():
        return None

    if stub_path.read_text().strip() == _DJANGO_DEFAULT_TESTS_STUB:
        stub_path.unlink()
        return f"removed {stub_path} (untouched default stub; replaced by tests/ package)"

    return (
        f"WARNING: {stub_path} has content and conflicts with the tests/ "
        f"package Forge needs to create -- move your tests into tests/ "
        f"and delete tests.py yourself, then re-run this command."
    )


def generate(resource, force: bool = False) -> list[str]:
    """Generate every file for a Resource. Returns human-readable notes
    about what was written and what was skipped.

    `force` overwrites previously generated serializer/viewset/urls/tests
    files (use it after changing a Resource's declaration). It never
    touches admin.py's append-once registration block, since that file
    routinely holds hand-written admin customizations alongside it.
    """
    model_name = resource.model_name()
    url_prefix = resource.model._meta.verbose_name_plural.replace(" ", "-").lower()
    app_dir = _app_dir(resource)
    notes = []

    serializer_mixins, viewset_mixins = _split_mixins(resource)

    # --- serializer -------------------------------------------------
    serializer_bases = [m.__name__ for m in serializer_mixins] + ["serializers.ModelSerializer"]
    serializer_body = _render(
        "serializer_body.py.jinja",
        model_name=model_name,
        base_classes=", ".join(serializer_bases),
        fields=resource.all_field_names(),
        read_only_fields=resource.read_only_fields,
    )
    serializer_path = app_dir / "api" / "serializers.py"
    serializer_imports = [
        "from rest_framework import serializers",
        *_group_mixin_imports(serializer_mixins),
        f"from ..models import {model_name}",
    ]
    status = _write_class_block(
        serializer_path, serializer_imports, serializer_body, marker=f"class {model_name}Serializer", force=force
    )
    notes.append(_status_note(status, serializer_path))

    # --- viewset ------------------------------------------------------
    if resource.tenant_scoped:
        from django_forge.mixins import TenantScopedViewSetMixin

        # Last, right before ModelViewSet: it must be the one that
        # actually fetches the queryset (fresh, per request), with any
        # mixins ahead of it narrowing it further via super().
        if TenantScopedViewSetMixin not in viewset_mixins:
            viewset_mixins = [*viewset_mixins, TenantScopedViewSetMixin]

    viewset_bases = [m.__name__ for m in viewset_mixins] + ["ModelViewSet"]
    viewset_body = _render(
        "viewset_body.py.jinja",
        model_name=model_name,
        base_classes=", ".join(viewset_bases),
        filterset_fields=resource.filters,
        search_fields=resource.searchable,
        ordering_fields=resource.sortable,
        permission_map=resource.permissions,
        permission_map_literal=_format_dict_literal(resource.permissions, base_indent=4),
        tenant_scoped=resource.tenant_scoped,
    )
    viewset_path = app_dir / "api" / "views.py"
    viewset_imports = [
        "from django_filters.rest_framework import DjangoFilterBackend",
        "from rest_framework import filters",
        "from rest_framework.viewsets import ModelViewSet",
        *_group_mixin_imports(viewset_mixins),
        *(["from django_forge.rbac.permissions import ResourcePermission"] if resource.permissions else []),
        f"from ..models import {model_name}",
        f"from .serializers import {model_name}Serializer",
    ]
    status = _write_class_block(
        viewset_path, viewset_imports, viewset_body, marker=f"class {model_name}ViewSet", force=force
    )
    notes.append(_status_note(status, viewset_path))

    # --- urls -----------------------------------------------------------
    urls_path = app_dir / "api" / "urls.py"
    status = _write_router_registration(urls_path, model_name, url_prefix, force=force)
    notes.append(_status_note(status, urls_path))
    if status == "created":
        notes.append(
            f"  -> include it in your project urls.py: "
            f"path('api/', include('{resource.app_label()}.api.urls'))"
        )

    # --- admin --------------------------------------------------------
    list_display = resource.fields[:6] or ["id"]
    if "id" not in list_display:
        list_display = ["id", *list_display]

    admin_path = app_dir / "admin.py"
    admin_imports = ["from django.contrib import admin", f"from .models import {model_name}"]
    if resource.audited:
        admin_imports.append("from simple_history.admin import SimpleHistoryAdmin")
    _ensure_imports(admin_path, admin_imports)
    admin_body = _render(
        "admin_body.py.jinja",
        model_name=model_name,
        list_display=list_display,
        search_fields=resource.searchable,
        filterset_fields=resource.filters,
        tenant_scoped=resource.tenant_scoped,
        admin_base_class="SimpleHistoryAdmin" if resource.audited else "admin.ModelAdmin",
    )
    if _append_once(admin_path, admin_body, marker=f"class {model_name}Admin"):
        notes.append(f"updated {admin_path}")
    else:
        notes.append(f"skipped {admin_path} ({model_name}Admin already registered)")

    # --- tests ----------------------------------------------------------
    tests_conflict = _resolve_tests_stub(app_dir)
    if tests_conflict:
        notes.append(tests_conflict)

    sample_payload = _sample_payload(resource)
    direct_create_kwargs = "organization=test_organization, " if resource.tenant_scoped else ""
    owner_scoped = any(m.__name__ == "OwnerScopedViewSetMixin" for m in resource.mixins)
    test_code = _render(
        "test_api.py.jinja",
        model_name=model_name,
        url_prefix=url_prefix,
        sample_payload=repr(sample_payload),
        has_permissions=bool(resource.permissions),
        tenant_scoped=resource.tenant_scoped,
        owner_scoped=owner_scoped,
        direct_create_kwargs=direct_create_kwargs,
    )
    test_path = app_dir / "tests" / f"test_{model_name.lower()}_api.py"
    if _write_new(test_path, test_code, force=force):
        notes.append(f"created {test_path}")
    else:
        notes.append(f"skipped {test_path} (already has content, use --force to overwrite)")

    # --- RBAC tests -----------------------------------------------------
    if resource.permissions:
        permission_tests = _build_permission_tests(resource, sample_payload, url_prefix)
        if permission_tests:
            rbac_test_code = _render(
                "test_permissions.py.jinja",
                model_name=model_name,
                sample_payload=repr(sample_payload),
                tests=permission_tests,
                tenant_scoped=resource.tenant_scoped,
                owner_scoped=owner_scoped,
                direct_create_kwargs=direct_create_kwargs,
            )
            rbac_test_path = app_dir / "tests" / f"test_{model_name.lower()}_permissions.py"
            if _write_new(rbac_test_path, rbac_test_code, force=force):
                notes.append(f"created {rbac_test_path}")
            else:
                notes.append(f"skipped {rbac_test_path} (already has content, use --force to overwrite)")

    # --- tenancy isolation tests -----------------------------------------
    if resource.tenant_scoped:
        tenancy_test_code = _render(
            "test_tenancy.py.jinja",
            model_name=model_name,
            url_prefix=url_prefix,
            sample_payload=repr(sample_payload),
            sample_payload_b=repr(_sample_payload(resource, variant="-b")),
            view_requires_auth=resource.permissions.get("view") not in (None, "public"),
        )
        tenancy_test_path = app_dir / "tests" / f"test_{model_name.lower()}_tenancy.py"
        if _write_new(tenancy_test_path, tenancy_test_code, force=force):
            notes.append(f"created {tenancy_test_path}")
        else:
            notes.append(f"skipped {tenancy_test_path} (already has content, use --force to overwrite)")

    return notes


def _build_permission_tests(resource, sample_payload, url_prefix) -> list[dict]:
    """One entry per protected action ("public" actions need no test --
    there's nothing to deny). Each entry carries ready-to-render Python
    source snippets rather than pushing this logic into the template.
    """
    action_config = {
        "create": {
            "needs_instance": False,
            "needs_payload": True,
            "call": f'api_client.post(reverse("{url_prefix}-list"), payload, format="json")',
        },
        "update": {
            "needs_instance": True,
            "needs_payload": True,
            "call": f'api_client.patch(reverse("{url_prefix}-detail", args=[instance.id]), payload, format="json")',
        },
        "delete": {
            "needs_instance": True,
            "needs_payload": False,
            "call": f'api_client.delete(reverse("{url_prefix}-detail", args=[instance.id]))',
        },
        "view": {
            "needs_instance": False,
            "needs_payload": False,
            "call": f'api_client.get(reverse("{url_prefix}-list"))',
        },
    }

    tests = []
    for action, rule in resource.permissions.items():
        if rule in ("public", None, ""):
            continue
        if action not in action_config:
            continue
        tests.append(
            {
                "action": action,
                "rule": rule,
                "is_codename": rule != "authenticated",
                **action_config[action],
            }
        )
    return tests


def _sample_payload(resource, variant: str = "") -> dict:
    """Best-effort dummy value per writable field, so the generated test
    file has something plausible to POST without the developer having to
    fill it in by hand for the common field types.

    `variant` is appended to string values -- pass a second variant when
    a test needs two distinct rows (e.g. one per organization), so it
    doesn't trip a unique constraint (like a Coupon's `code`) by creating
    both from the exact same literal payload.
    """
    payload = {}
    for field_name in resource.fields:
        if field_name in resource.read_only_fields:
            continue
        try:
            field = resource.model._meta.get_field(field_name)
        except Exception:
            continue
        payload[field_name] = _dummy_value_for(field, variant)
    return payload


def _dummy_value_for(field, variant: str = ""):
    internal_type = field.get_internal_type()
    if internal_type in ("CharField", "TextField", "SlugField", "EmailField"):
        return f"test-{field.name}{variant}"
    if internal_type in (
        "IntegerField",
        "PositiveIntegerField",
        "PositiveSmallIntegerField",
        "PositiveBigIntegerField",
        "SmallIntegerField",
        "BigIntegerField",
    ):
        return 1
    if internal_type == "DecimalField":
        return "9.99"
    if internal_type == "FloatField":
        return 1.0
    if internal_type == "BooleanField":
        return True
    if internal_type == "DateField":
        return "2026-01-01"
    if internal_type == "DateTimeField":
        return "2026-01-01T00:00:00Z"
    return None
