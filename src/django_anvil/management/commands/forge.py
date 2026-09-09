import sys

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError

from django_anvil.core.generator import generate
from django_anvil.core.registry import registry


class Command(BaseCommand):
    help = (
        "Django Anvil: turn a declarative Resource into a full DRF API + admin + "
        "tests (`resource`), list what's registered (`list`), propose a feature as "
        "a reviewable diff (`ai`), or check the project for common problems (`doctor`)."
    )

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest="subcommand", required=True)

        resource_parser = subparsers.add_parser(
            "resource", help="Generate serializer/viewset/urls/admin/tests for a model."
        )
        resource_parser.add_argument(
            "model", help="Model name, e.g. Product, or app_label.Product if ambiguous."
        )
        resource_parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite previously generated serializer/viewset/urls/tests files.",
        )

        subparsers.add_parser("list", help="List every registered Resource.")

        ai_parser = subparsers.add_parser(
            "ai", help="Propose a models.py/resources.py change for a feature."
        )
        ai_parser.add_argument("description", help="Plain-English description of the feature to add.")
        ai_parser.add_argument("--app", required=True, help="App label the feature should live in.")
        ai_parser.add_argument("--output", help="Also write the diff to this file.")
        ai_parser.add_argument(
            "--apply",
            action="store_true",
            help="After showing the diff, ask for typed confirmation, then write the files if approved. "
            "Without this flag, nothing is ever written.",
        )

        subparsers.add_parser(
            "doctor", help="Check settings and registered Resources for common problems."
        )

    def handle(self, *args, **options):
        subcommand = options["subcommand"]
        if subcommand == "resource":
            self._handle_resource(options["model"], force=options["force"])
        elif subcommand == "list":
            self._handle_list()
        elif subcommand == "ai":
            self._handle_ai(options["description"], options["app"], options["output"], options["apply"])
        elif subcommand == "doctor":
            self._handle_doctor()

    def _resolve_model(self, name):
        if "." in name:
            app_label, model_name = name.split(".", 1)
            try:
                return apps.get_model(app_label, model_name)
            except LookupError as exc:
                raise CommandError(str(exc)) from exc

        matches = [
            model
            for model in apps.get_models()
            if model.__name__.lower() == name.lower()
        ]
        if not matches:
            raise CommandError(f"No installed model named '{name}'.")
        if len(matches) > 1:
            options = ", ".join(f"{m._meta.app_label}.{m.__name__}" for m in matches)
            raise CommandError(
                f"'{name}' is ambiguous across apps ({options}). "
                f"Specify it as app_label.{name} instead."
            )
        return matches[0]

    def _handle_resource(self, model_name, force=False):
        model = self._resolve_model(model_name)
        try:
            resource = registry.get_for_model(model)
        except LookupError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(f"Generating from {resource.__name__} ...")
        for note in generate(resource, force=force):
            self.stdout.write(f"  {note}")
        self.stdout.write(self.style.SUCCESS("Done."))

    def _handle_list(self):
        resources = registry.all()
        if not resources:
            self.stdout.write("No Resources registered yet. Define one in <app>/resources.py.")
            return

        for resource in resources:
            self.stdout.write(f"{resource.__name__} -> {resource.app_label()}.{resource.model_name()}")

    def _handle_ai(self, description, app_label, output_path, apply):
        from django_anvil.ai.suggest import apply_changes, build_diff, suggest_feature

        self.stdout.write("Asking the AI provider for a suggestion ...")
        try:
            changes = suggest_feature(description, app_label)
        except Exception as exc:
            raise CommandError(str(exc)) from exc

        diff_text = build_diff(changes)
        self.stdout.write(diff_text)

        if output_path:
            with open(output_path, "w") as f:
                f.write(diff_text)
            self.stdout.write(self.style.SUCCESS(f"Wrote proposed diff to {output_path}"))

        if not apply:
            self.stdout.write(
                self.style.WARNING(
                    "Nothing was written. Review the diff above, then apply it yourself "
                    "(e.g. `patch -p1 < file.patch`), or re-run with --apply to be asked to write it directly."
                )
            )
            return

        self.stdout.write("")
        file_list = ", ".join(change.relative_path for change in changes)
        if not self._confirm(f"Write {len(changes)} file(s) now ({file_list})? [y/N]: "):
            self.stdout.write("Not applied. Nothing was written.")
            return

        for note in apply_changes(changes):
            self.stdout.write(self.style.SUCCESS(note))
        self.stdout.write(
            self.style.WARNING(
                "Files written. This does not run makemigrations or forge resource for you -- "
                "review the changes, then run those yourself, e.g.:"
            )
        )
        self.stdout.write(f"  python manage.py makemigrations {app_label}")
        self.stdout.write("  python manage.py forge resource <NewModel>")

    def _confirm(self, prompt):
        if not sys.stdin.isatty():
            self.stdout.write(
                self.style.WARNING("Not an interactive terminal -- treating as 'no'. Run --apply from a real TTY.")
            )
            return False
        return input(prompt).strip().lower() in ("y", "yes")

    def _handle_doctor(self):
        from django_anvil.doctor.checks import run_checks

        style_by_level = {
            "ok": self.style.SUCCESS,
            "info": lambda s: s,
            "warning": self.style.WARNING,
            "error": self.style.ERROR,
        }
        icon_by_level = {"ok": "OK", "info": "INFO", "warning": "WARN", "error": "ERROR"}

        results = run_checks()
        counts = {"ok": 0, "info": 0, "warning": 0, "error": 0}
        for result in results:
            counts[result.level] += 1
            style = style_by_level[result.level]
            self.stdout.write(style(f"[{icon_by_level[result.level]}] {result.category}: {result.message}"))

        self.stdout.write("")
        summary = f"{counts['error']} error(s), {counts['warning']} warning(s), {counts['info']} suggestion(s)"
        if counts["error"]:
            self.stdout.write(self.style.ERROR(summary))
        elif counts["warning"]:
            self.stdout.write(self.style.WARNING(summary))
        else:
            self.stdout.write(self.style.SUCCESS(summary))
