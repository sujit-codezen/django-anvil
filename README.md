# Django Forge

Declarative `Resource` classes that generate a DRF serializer, viewset,
router urls, admin registration, RBAC enforcement, tenant scoping, and
tests from one model definition — for existing Django + DRF projects,
not a replacement for either. Free, open-source, no hosted service.

## Status

All four planned phases are built and demo-verified: Resource core, RBAC,
shared-schema multi-tenancy, and an AI suggestion engine, plus doctor/
audit polish. See `demo/` for a working example (four resources —
`Product`, `Coupon`, `Review`, `Tag` — sharing one app).

## Install into a project

```bash
pip install django-anvil
```

Installing from a local checkout instead (for contributing to Forge itself):

```bash
pip install -e /path/to/django-forge
```

One install, everything included — the AI providers (OpenAI, Anthropic,
Gemini) and `django-simple-history` (for `audited = True`) are plain
dependencies of django-forge itself, not opt-in extras. Nothing extra to
remember; `FORGE_AI_PROVIDER` just picks which AI provider is actually
*used*.

```python
# settings.py
INSTALLED_APPS = [
    ...,
    "rest_framework",
    "django_filters",
    "django_forge",
    "django_forge.rbac",      # optional: only if you use permissions
    "django_forge.tenancy",   # optional: only if you use tenant_scoped
    "simple_history",         # optional: only if you use audited=True
    "your_app",
]

MIDDLEWARE = [
    ...,
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_forge.tenancy.middleware.CurrentOrganizationMiddleware",  # optional
    ...,
]
```

## Usage

1. Define a `Resource` next to your model, in `your_app/resources.py`:

    ```python
    from django_forge.core.resource import Resource
    from django_forge.mixins import SoftDeleteViewSetMixin, TimestampedSerializerMixin
    from .models import Product

    class ProductResource(Resource):
        model = Product
        fields = ["id", "name", "price", "stock", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]
        searchable = ["name"]
        filters = ["is_active"]
        sortable = ["price", "created_at"]
        mixins = [SoftDeleteViewSetMixin, TimestampedSerializerMixin]

        # optional, see below:
        permissions = {}       # RBAC
        tenant_scoped = False  # multi-tenancy
        audited = False        # change history
    ```

2. Generate everything:

    ```bash
    python manage.py forge resource Product
    ```

   This writes/merges into `your_app/api/serializers.py`,
   `your_app/api/views.py`, `your_app/api/urls.py`, registers the model
   in `your_app/admin.py`, and writes `your_app/tests/test_product_api.py`
   (plus RBAC/tenancy test files if those are enabled). Multiple
   Resources in the same app share these files correctly — a second
   `forge resource Coupon` adds its own classes alongside `Product`'s,
   the way a person would by hand. Re-running is safe by default: it
   never overwrites a Resource's existing block unless you pass
   `--force` (which regenerates only that Resource's block, not
   anyone else's, and never touches admin.py's registration — see
   below).

3. Wire the generated router into your project urls (only needed once
   per app, the first time you generate a resource in it):

    ```python
    path("api/", include("your_app.api.urls")),
    ```

4. See every registered Resource, or check the project for common
   mistakes:

    ```bash
    python manage.py forge list
    python manage.py forge doctor
    ```

## RBAC

`permissions` maps an action (`view`, `create`, `update`, `delete`) to
either `"public"`, `"authenticated"`, or a real Django permission
codename (`"<app_label>.<codename>"` — the four Django auto-creates per
model, `add_x`/`change_x`/`delete_x`/`view_x`, or one you declare
yourself in the model's `Meta.permissions`):

```python
permissions = {
    "view": "public",
    "create": "products.add_product",
    "update": "products.change_product",
    "delete": "products.delete_product",
}
```

**Fails closed**: an action with no rule listed is denied to everyone,
not allowed. Roles are just Django's own `Group`/`Permission` system,
exposed as `django_forge.rbac.models.Role` (a friendlier-named proxy for
`Group`) with a `.grant("app_label.codename")` helper — manage them from
the normal Django admin "Roles" section, no new UI to learn. Generating
a Resource with `permissions` set also writes an
`RBAC test file (test_<model>_permissions.py)` proving each protected
action really is denied/allowed as declared, using real HTTP requests.

## Multi-tenancy

Shared-schema: every tenant's rows live in the same tables, tagged with
an `organization_id` and auto-scoped. Opt in per model by inheriting
`TenantScopedModel` (adds the `organization` FK) and setting
`tenant_scoped = True` on the Resource:

```python
from django_forge.tenancy.models import TenantScopedModel

class Product(TenantScopedModel):
    ...
```

**Fails closed**: `Model.objects` (the default manager) returns nothing
if there's no organization in context for the current request — never
"every organization's rows." `Model.all_objects` is the same queryset
unfiltered, for the deliberate cases (Django admin, scripts) that need
everything; generated `ModelAdmin`s already use it, since admin is a
global surface. The current organization is resolved from an `X-Org-Id`
header (only honored if the user is really a member) or automatically if
the user belongs to exactly one organization — resolved inside the DRF
ViewSet itself (`TenantScopedViewSetMixin`), not via Django middleware,
because DRF's own authentication (tokens, `force_authenticate` in tests)
runs later than Django's middleware chain. Generating a `tenant_scoped`
Resource also writes a tenancy isolation test file proving one
organization can't see or query another's rows through the API.

RBAC and tenancy compose: a role check happens first, then the
tenant-scoped queryset filters what that role is allowed to see.

## AI engine (analyze + suggest, apply only with your approval)

```bash
python manage.py forge ai "add a coupon system with percent or fixed-amount \
discounts, an optional expiry date, and a usage limit" --app products --output coupon.patch
```

Reads your project's models/Resources for context, asks the configured
LLM provider for complete `models.py`/`resources.py` file contents (not
a diff — LLMs write whole files far more reliably than correct diff
syntax), and computes the unified diff itself. **By default, nothing is
ever written** — review the diff, apply it by hand (`git apply
coupon.patch` or `patch -p1 < coupon.patch`), then run `forge resource
<NewModel>` yourself.

Add `--apply` to be asked, after seeing the diff, whether to write the
files directly:

```bash
python manage.py forge ai "add a coupon system..." --app products --apply
```
```
--- a/products/models.py
+++ b/products/models.py
...
Write 2 file(s) now (products/models.py, products/resources.py)? [y/N]:
```

`--apply` never writes without that typed confirmation — it isn't a
"trust the AI" flag, it's "let me approve without leaving the
terminal." It still only ever writes `models.py`/`resources.py`; it
never runs `makemigrations` or `forge resource` for you — those stay
separate, deliberate steps you run yourself once you've looked at what
changed. In a non-interactive session (no TTY — CI, a piped command),
`--apply` always declines and writes nothing, rather than guessing.

Four providers ship, chosen via `FORGE_AI_PROVIDER` (a dotted path — nothing
in the AI engine itself is hard-locked to one vendor). All three real
providers' SDKs come with a plain `pip install django-forge` — no
extras needed:

| Provider | API key |
|---|---|
| `OpenAIProvider` *(default)* | `OPENAI_API_KEY` |
| `AnthropicProvider` | `ANTHROPIC_API_KEY` |
| `GeminiProvider` | `GOOGLE_API_KEY` |
| `StaticProvider` | none — fixed response, for tests/CI |

Switching providers is exactly this — no installing anything else, ever:

```python
# settings.py
FORGE_AI_PROVIDER = "django_forge.ai.providers.AnthropicProvider"  # or OpenAIProvider / GeminiProvider
FORGE_AI_MODEL = "claude-sonnet-5"  # optional override, per-provider default otherwise
FORGE_AI_API_KEY = env("MY_KEY")    # optional; falls back to each SDK's own env var
```

`GeminiProvider` uses the current `google-genai` package, not the
end-of-lifed `google-generativeai`. Writing your own provider (a
self-hosted model, an internal proxy, a vendor not listed above) is one
class with one method — see `CustomProviderExample` in
`django_forge/ai/providers.py` for a working template, and
`tests/test_ai_providers.py` for how each shipped provider is verified
against a mocked SDK (no real API key needed to run those tests).

## Audit history

Set `audited = True` on a Resource and add
`history = HistoricalRecords()` to the model yourself (Forge wires up
the *admin* integration — `SimpleHistoryAdmin`, giving a full change
log in the admin UI — but never edits your model file for you, the same
policy as `TenantScopedModel`). `django-simple-history` is already
installed as part of django-forge — just add `"simple_history"` to
`INSTALLED_APPS`. `forge doctor` flags a Resource that says
`audited = True` but whose model doesn't have the field yet.

## `forge doctor`

Static checks, no database needed — safe to run in CI before `migrate`:

- `DEBUG=True`, an unreplaced default `SECRET_KEY`, empty `ALLOWED_HOSTS`
  with `DEBUG=False`.
- A `tenant_scoped` Resource whose model isn't actually a
  `TenantScopedModel`.
- A mixin used without the field it needs (`SoftDeleteViewSetMixin`
  needs `is_deleted`, `OwnerScopedViewSetMixin` needs `owner`).
- A permission codename that doesn't match any real permission on the
  model — RBAC fails closed, so a typo there silently locks *everyone*
  out of that action with no error to point at the cause.
- A field that's filtered/sorted on a lot with no database index.

## Mixins

`django_forge.mixins` ships real, reusable behavior — not just codegen
templates. A Resource opts in by listing them; the generator wires the
matching one into the serializer or the viewset base classes based on
its name (`...SerializerMixin` vs `...ViewSetMixin`):

- `SoftDeleteViewSetMixin` — requires an `is_deleted` field; excludes
  soft-deleted rows and turns `DELETE` into a soft delete.
- `OwnerScopedViewSetMixin` — requires an `owner` FK; scopes *every*
  action (including list/retrieve) to `request.user`'s own rows and
  auto-assigns it on create — "your own stuff only", like a private
  notes/wishlist feature. Fails closed (empty, not a crash) for
  anonymous requests. Don't pair it with `permissions = {"view": "public"}`
  expecting a public-reads/private-writes feed — that needs a different
  `get_queryset` than this mixin provides; see its docstring.
- `TenantScopedViewSetMixin` — auto-injected when `tenant_scoped = True`;
  don't add it yourself.
- `TimestampedSerializerMixin` — marks `created_at`/`updated_at`
  read-only if present.

Write your own the same way: a plain class following the same naming
convention, mixed into the generated `ModelViewSet`/`ModelSerializer`.

## Developing Forge itself

Two separate test suites, for two separate things:

```bash
pip install -e ".[dev]"
python -m pytest -v          # this package's own code -- providers, indexer, diff/apply logic (17 tests)
cd demo && python -m pytest products/tests/ -v   # the generated code the package produces (49 tests)
```

They're kept apart on purpose: `demo/` is its own Django project with
its own settings, and Django only allows one process-global settings
object — a bare `pytest` from the repo root only collects `./tests/`
(see `testpaths` in `pyproject.toml`), so it never tries to load both.

## Demo

`demo/` is a throwaway Django project proving every feature end to end,
via four Resources in one app:

| Resource | Demonstrates |
|---|---|
| `Product` | RBAC (mixed `public`/codename rules), tenancy, `SoftDeleteViewSetMixin`, `TimestampedSerializerMixin` |
| `Coupon` | RBAC (all codenames, no `public`), tenancy, audit history (`SimpleHistoryAdmin`) |
| `Review` | `OwnerScopedViewSetMixin`, the `"authenticated"` permission rule, deliberately *not* tenant-scoped |
| `Tag` | Added live via `forge ai --apply` during development — proof the propose→approve→write loop produces a genuinely working Resource |

To run it yourself:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cd demo
python manage.py migrate
python -m pytest products/ -v      # 49 tests
python manage.py forge doctor
python manage.py seed_demo          # orgs, roles, users, sample data -- safe to re-run
python manage.py runserver
```

Then, e.g.:

```bash
curl http://127.0.0.1:8000/api/products/                                    # [] -- anonymous, no org context
curl -u alice:demo-pass-1234 http://127.0.0.1:8000/api/products/            # Acme's products only
curl -u bob:demo-pass-1234 http://127.0.0.1:8000/api/products/              # Globex's only
curl -u carol:demo-pass-1234 -X POST http://127.0.0.1:8000/api/products/ \
  -d 'name=Test&price=1&stock=1&is_active=true'                             # 403 -- Staff, view-only
```

Or open `http://127.0.0.1:8000/admin/` (`admin` / `demo-pass-1234`) to
browse Roles, Organizations, Products, Coupons (with a "History" button
from audit logging), Reviews, and Tags directly. `seed_demo` prints the
full list of demo accounts and what each one can do.
