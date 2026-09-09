"""suggest.py had zero test coverage before this -- everything here was
previously only verified by hand, once, during development. Covers the
three separately-testable steps: parsing a provider's response into
ProposedChange objects, diffing them against what's on disk, and
actually writing them (apply_changes) -- the one function that touches
disk, and the only thing `forge ai --apply` calls after a human types
"y".
"""

import pytest
from django.test import override_settings

from django_anvil.ai.suggest import (
    ProposedChange,
    _parse_response,
    apply_changes,
    build_diff,
    suggest_feature,
)

_TWO_FILE_RESPONSE = """===FILE: products/models.py===
class Tag(models.Model):
    name = models.CharField(max_length=50)
===ENDFILE===
===FILE: products/resources.py===
class TagResource(Resource):
    model = Tag
===ENDFILE===
"""


def test_parse_response_extracts_every_file_block(tmp_path):
    with override_settings(BASE_DIR=tmp_path):
        changes = _parse_response(_TWO_FILE_RESPONSE)

    assert [c.relative_path for c in changes] == ["products/models.py", "products/resources.py"]
    assert changes[0].new_content == "class Tag(models.Model):\n    name = models.CharField(max_length=50)\n"


def test_parse_response_adds_missing_trailing_newline(tmp_path):
    response = "===FILE: a.py===\nno_trailing_newline_here\n===ENDFILE===\n"
    with override_settings(BASE_DIR=tmp_path):
        changes = _parse_response(response)
    assert changes[0].new_content.endswith("\n")


def test_parse_response_raises_when_no_file_blocks_found(tmp_path):
    with override_settings(BASE_DIR=tmp_path):
        with pytest.raises(ValueError, match="didn't contain any"):
            _parse_response("Sure, here's some code:\n\nclass Tag: pass\n")


def test_parse_response_reads_existing_file_as_old_content(tmp_path):
    existing = tmp_path / "products" / "models.py"
    existing.parent.mkdir(parents=True)
    existing.write_text("class Product(models.Model): pass\n")

    with override_settings(BASE_DIR=tmp_path):
        changes = _parse_response(_TWO_FILE_RESPONSE)

    models_change = next(c for c in changes if c.relative_path == "products/models.py")
    assert models_change.old_content == "class Product(models.Model): pass\n"
    assert not models_change.is_new_file

    resources_change = next(c for c in changes if c.relative_path == "products/resources.py")
    assert resources_change.old_content == ""
    assert resources_change.is_new_file


def test_build_diff_marks_new_files_against_dev_null():
    change = ProposedChange(relative_path="products/models.py", new_content="class Tag: pass\n", old_content="")
    diff = build_diff([change])
    assert "--- /dev/null" in diff
    assert "+++ b/products/models.py" in diff
    assert "+class Tag: pass" in diff


def test_build_diff_shows_real_changes_against_existing_file():
    change = ProposedChange(
        relative_path="products/models.py",
        new_content="class Product(models.Model):\n    name = models.CharField(max_length=200)\n",
        old_content="class Product(models.Model):\n    pass\n",
    )
    diff = build_diff([change])
    assert "--- a/products/models.py" in diff
    assert "-    pass" in diff
    assert "+    name = models.CharField(max_length=200)" in diff


def test_apply_changes_writes_files_and_creates_parent_dirs(tmp_path):
    change = ProposedChange(
        relative_path="products/models.py", new_content="class Tag: pass\n", old_content=""
    )
    with override_settings(BASE_DIR=tmp_path):
        notes = apply_changes([change])

    written = tmp_path / "products" / "models.py"
    assert written.read_text() == "class Tag: pass\n"
    assert notes == [f"created {written}"]


def test_apply_changes_reports_updated_for_an_existing_file(tmp_path):
    existing = tmp_path / "products.py"
    existing.write_text("old content\n")
    change = ProposedChange(relative_path="products.py", new_content="new content\n", old_content="old content\n")

    with override_settings(BASE_DIR=tmp_path):
        notes = apply_changes([change])

    assert existing.read_text() == "new content\n"
    assert notes == [f"updated {existing}"]


def test_suggest_feature_uses_configured_provider_and_parses_its_response(tmp_path):
    with override_settings(
        BASE_DIR=tmp_path,
        FORGE_AI_PROVIDER="django_anvil.ai.providers.StaticProvider",
        FORGE_AI_STATIC_RESPONSE=_TWO_FILE_RESPONSE,
    ):
        changes = suggest_feature("add a Tag model", "products")

    assert [c.relative_path for c in changes] == ["products/models.py", "products/resources.py"]
