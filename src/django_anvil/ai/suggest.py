"""Turns a plain-English feature request into a proposed models.py /
resources.py change. `suggest_feature` never writes anything itself --
it only parses what the provider proposed. Diffing (`build_diff`) and
actually writing files (`apply_changes`) are separate, deliberate steps,
so a caller can show the diff and require explicit approval before ever
calling `apply_changes` -- see the `anvil ai --apply` command.

The provider is asked for complete file contents rather than a diff
directly: LLMs are far more reliable at writing a whole file than at
producing correct unified-diff syntax by hand, and diffing is a solved,
deterministic problem we can just do ourselves.
"""

import dataclasses
import difflib
import re
from pathlib import Path

from django.conf import settings

from .indexer import build_project_summary
from .providers import get_provider

_FILE_BLOCK_RE = re.compile(r"===FILE: (?P<path>.+?)===\n(?P<content>.*?)\n===ENDFILE===", re.DOTALL)

_SYSTEM_PROMPT = """You are extending a Django project that uses Django Anvil, a \
toolkit that generates DRF APIs from declarative Resource classes.

Conventions to follow exactly:
- Models are plain Django models, in <app>/models.py.
- Every model that should get a generated API needs a matching Resource
  subclass in <app>/resources.py, for example:

    from django_anvil.core.resource import Resource
    from .models import Coupon

    class CouponResource(Resource):
        model = Coupon
        fields = [...]
        read_only_fields = [...]
        searchable = [...]
        filters = [...]
        sortable = [...]
        permissions = {"view": "public", "create": "<app_label>.add_<model_lower>", ...}
        tenant_scoped = True  # only if the project already uses multi-tenancy

- Do not write serializers.py, views.py, urls.py, or admin.py: running
  `manage.py anvil resource <Model>` generates those from the Resource
  class. Only propose models.py and resources.py.
- If the project's existing models inherit from TenantScopedModel, any
  new model in the same feature area should too, for consistency.
- Output ONLY complete file contents, one block per file, in exactly
  this format, and nothing else -- no explanation before or after:

===FILE: <app_label>/models.py===
<the complete new file content>
===ENDFILE===
===FILE: <app_label>/resources.py===
<the complete new file content>
===ENDFILE===
"""


@dataclasses.dataclass
class ProposedChange:
    relative_path: str
    new_content: str
    old_content: str  # "" if the file doesn't exist yet

    @property
    def path(self) -> Path:
        return settings.BASE_DIR / self.relative_path

    @property
    def is_new_file(self) -> bool:
        return not self.old_content


def suggest_feature(description: str, app_label: str) -> list[ProposedChange]:
    """Asks the configured provider for a feature and parses its response.
    Reads current file contents from disk (to diff against later) but
    never writes anything. Raises ValueError if the response couldn't be
    parsed into any file blocks.
    """
    provider = get_provider()
    project_summary = build_project_summary()

    prompt = (
        f"Existing project models and resources:\n{project_summary}\n\n"
        f"Target app: {app_label}\n\n"
        f"Feature request: {description}\n"
    )

    response_text = provider.complete(system=_SYSTEM_PROMPT, prompt=prompt)
    return _parse_response(response_text)


def _parse_response(response_text: str) -> list[ProposedChange]:
    matches = list(_FILE_BLOCK_RE.finditer(response_text))
    if not matches:
        raise ValueError(
            "The AI provider's response didn't contain any ===FILE: ...=== "
            "blocks -- nothing to propose. Raw response:\n\n" + response_text
        )

    changes = []
    for match in matches:
        relative_path = match.group("path").strip()
        new_content = match.group("content")
        if not new_content.endswith("\n"):
            new_content += "\n"

        file_path = settings.BASE_DIR / relative_path
        old_content = file_path.read_text() if file_path.exists() else ""
        changes.append(ProposedChange(relative_path, new_content, old_content))

    return changes


def build_diff(changes: list[ProposedChange]) -> str:
    diffs = []
    for change in changes:
        diff = difflib.unified_diff(
            change.old_content.splitlines(keepends=True),
            change.new_content.splitlines(keepends=True),
            fromfile=f"a/{change.relative_path}" if change.old_content else "/dev/null",
            tofile=f"b/{change.relative_path}",
        )
        diffs.append("".join(diff))
    return "\n".join(diffs)


def apply_changes(changes: list[ProposedChange]) -> list[str]:
    """Actually writes the proposed files. Only call this after a human
    has reviewed the diff and explicitly approved it -- see `anvil ai
    --apply`, which is the only built-in caller. Does not run
    `makemigrations` or `anvil resource`; those are separate, deliberate
    steps a developer still takes themselves.
    """
    notes = []
    for change in changes:
        change.path.parent.mkdir(parents=True, exist_ok=True)
        change.path.write_text(change.new_content)
        notes.append(f"{'created' if change.is_new_file else 'updated'} {change.path}")
    return notes
