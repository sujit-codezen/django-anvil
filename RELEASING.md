# Releasing django-anvil to PyPI

Publishing uses PyPI's **Trusted Publishing** (OIDC) via
`.github/workflows/publish.yml` — no API token is ever created, stored,
or typed anywhere. This is a one-time setup, done once by whoever owns
the PyPI project.

## One-time setup (do this before the first release)

1. Log in to [pypi.org](https://pypi.org) (create an account first if you
   don't have one — email verification required).
2. Go to **Your account → Publishing** (or directly:
   <https://pypi.org/manage/account/publishing/>).
3. Under "Add a new pending publisher", fill in exactly:

   | Field | Value |
   |---|---|
   | PyPI Project Name | `django-anvil` |
   | Owner | `sujit-codezen` |
   | Repository name | `django-forge` |
   | Workflow name | `publish.yml` |
   | Environment name | `pypi` |

4. Click **Add**. PyPI now trusts this exact GitHub Actions workflow to
   publish `django-anvil` — the project doesn't need to exist on PyPI yet
   for this step ("pending publisher").

That's the only step that needs a human at a keyboard with a PyPI
login. Everything after this is just pushing a git tag.

## Every release after that

```bash
# bump the version in pyproject.toml first, then:
git tag v0.1.0
git push origin v0.1.0
```

Pushing a tag matching `v*` triggers `.github/workflows/publish.yml`,
which builds the sdist + wheel and uploads them to PyPI automatically.
Watch it run under the repo's **Actions** tab.

## Verifying a release

```bash
pip index versions django-anvil   # or just check https://pypi.org/project/django-anvil/
```
