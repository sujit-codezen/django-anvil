"""Pluggable LLM backends for the AI engine. Nothing in django_anvil.ai
hard-codes a vendor -- `get_provider()` reads the class to use from
Django settings, so swapping providers never touches suggest.py.

Ships four: OpenAI (default), Anthropic, Gemini, and a Static one for
tests/CI. All three real providers' SDKs are plain dependencies of
django-anvil itself -- `pip install django-anvil` alone gets you all of
them, no extras to remember. FORGE_AI_PROVIDER just picks which one is
actually *used* at runtime; the other two sit there unused rather than
unavailable. Writing your own provider is exactly this shape -- see
CustomProviderExample at the bottom for a template.
"""

import abc

from django.conf import settings
from django.utils.module_loading import import_string


class AIProvider(abc.ABC):
    @abc.abstractmethod
    def complete(self, system: str, prompt: str) -> str:
        """Return the model's raw text response to `prompt`."""


class AnthropicProvider(AIProvider):
    """Needs an ANTHROPIC_API_KEY (or FORGE_AI_API_KEY in settings/env;
    falls back to the SDK's own env var if neither is set). The
    'anthropic' package itself ships as a plain django-anvil dependency,
    so a normal `pip install django-anvil` already has it.
    """

    def __init__(self, model: str | None = None, api_key: str | None = None):
        try:
            import anthropic
        except ImportError as exc:
            # Shouldn't normally happen -- 'anthropic' is a plain
            # dependency of django-anvil itself. Only hit via --no-deps,
            # a manually pruned environment, or similar.
            raise RuntimeError(
                "The Anthropic provider needs the 'anthropic' package, which should already be "
                "installed as part of django-anvil. Try: pip install anthropic"
            ) from exc

        self._client = anthropic.Anthropic(api_key=api_key or getattr(settings, "FORGE_AI_API_KEY", None))
        self._model = model or getattr(settings, "FORGE_AI_MODEL", "claude-sonnet-5")

    def complete(self, system: str, prompt: str) -> str:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(block.text for block in response.content if block.type == "text")


class OpenAIProvider(AIProvider):
    """Default provider. Needs an OPENAI_API_KEY (or FORGE_AI_API_KEY).
    Override the model via FORGE_AI_MODEL -- the default below is just a
    reasonable starting point, not a promise it's OpenAI's current best
    model by the time you're reading this. The 'openai' package itself
    ships as a plain django-anvil dependency.
    """

    def __init__(self, model: str | None = None, api_key: str | None = None):
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError(
                "The OpenAI provider needs the 'openai' package, which should already be "
                "installed as part of django-anvil. Try: pip install openai"
            ) from exc

        self._client = OpenAI(api_key=api_key or getattr(settings, "FORGE_AI_API_KEY", None))
        self._model = model or getattr(settings, "FORGE_AI_MODEL", "gpt-4o")

    def complete(self, system: str, prompt: str) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            max_tokens=4096,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content


class GeminiProvider(AIProvider):
    """Needs a GOOGLE_API_KEY (or FORGE_AI_API_KEY). Override the model
    via FORGE_AI_MODEL -- same caveat as OpenAIProvider's default above.

    Uses the `google-genai` package, not the older `google-generativeai`
    -- Google has end-of-lifed the latter (it printed a deprecation
    warning pointing at this one during development), so this wraps the
    package Google actually wants new code to use. Ships as a plain
    django-anvil dependency, same as the other two real providers.
    """

    def __init__(self, model: str | None = None, api_key: str | None = None):
        try:
            from google import genai
        except ImportError as exc:
            raise RuntimeError(
                "The Gemini provider needs the 'google-genai' package, which should already be "
                "installed as part of django-anvil. Try: pip install google-genai"
            ) from exc

        resolved_key = api_key or getattr(settings, "FORGE_AI_API_KEY", None)
        self._client = genai.Client(api_key=resolved_key) if resolved_key else genai.Client()
        self._model = model or getattr(settings, "FORGE_AI_MODEL", "gemini-2.0-flash")

    def complete(self, system: str, prompt: str) -> str:
        from google.genai import types

        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
            config=types.GenerateContentConfig(system_instruction=system, max_output_tokens=4096),
        )
        return response.text


class StaticProvider(AIProvider):
    """Returns a fixed, pre-set response instead of calling anything.
    For tests and CI -- set FORGE_AI_PROVIDER to this and FORGE_AI_STATIC_RESPONSE
    to what it should return, so the rest of the pipeline (indexing,
    prompting, diff-building) can be exercised with no network and no
    API key.
    """

    def complete(self, system: str, prompt: str) -> str:
        response = getattr(settings, "FORGE_AI_STATIC_RESPONSE", None)
        if response is None:
            raise RuntimeError("StaticProvider needs settings.FORGE_AI_STATIC_RESPONSE to be set.")
        return response


class CustomProviderExample(AIProvider):
    """Not registered anywhere, not used by default -- a template. Any
    class with this one method (`complete(system, prompt) -> str`) works;
    point FORGE_AI_PROVIDER at its dotted path. Useful for a self-hosted
    model, an internal proxy, or a vendor Forge doesn't ship a wrapper
    for yet.
    """

    def __init__(self):
        self._endpoint = getattr(settings, "FORGE_AI_ENDPOINT", "http://localhost:11434/api/generate")

    def complete(self, system: str, prompt: str) -> str:
        import json
        import urllib.request

        body = json.dumps({"prompt": f"{system}\n\n{prompt}", "stream": False}).encode()
        request = urllib.request.Request(self._endpoint, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read())["response"]


def get_provider() -> AIProvider:
    dotted_path = getattr(settings, "FORGE_AI_PROVIDER", "django_anvil.ai.providers.OpenAIProvider")
    provider_cls = import_string(dotted_path)
    return provider_cls()
