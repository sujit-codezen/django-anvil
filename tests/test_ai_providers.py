"""No real API keys or network here -- each provider's underlying SDK
client is mocked, so what's actually verified is the provider's own
logic: does it call the SDK with the right model/system/prompt shape,
and does it correctly pull the text back out of that SDK's particular
response shape. That boundary is exactly what can't be verified any
other way without a real, paid API call.
"""

from types import SimpleNamespace
from unittest import mock

import pytest
from django.test import override_settings

from django_anvil.ai.providers import (
    AnthropicProvider,
    GeminiProvider,
    OpenAIProvider,
    StaticProvider,
    get_provider,
)


def test_anthropic_provider_shapes_request_and_extracts_text():
    fake_response = SimpleNamespace(
        content=[
            SimpleNamespace(type="text", text="hello "),
            SimpleNamespace(type="text", text="world"),
        ]
    )
    fake_client = mock.Mock()
    fake_client.messages.create.return_value = fake_response

    with mock.patch("anthropic.Anthropic", return_value=fake_client) as mock_anthropic:
        provider = AnthropicProvider(model="claude-test", api_key="fake-key")
        result = provider.complete(system="be helpful", prompt="say hi")

    mock_anthropic.assert_called_once_with(api_key="fake-key")
    fake_client.messages.create.assert_called_once_with(
        model="claude-test",
        max_tokens=4096,
        system="be helpful",
        messages=[{"role": "user", "content": "say hi"}],
    )
    assert result == "hello world"


def test_openai_provider_shapes_request_and_extracts_text():
    fake_response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="hello from gpt"))]
    )
    fake_client = mock.Mock()
    fake_client.chat.completions.create.return_value = fake_response

    with mock.patch("openai.OpenAI", return_value=fake_client) as mock_openai:
        provider = OpenAIProvider(model="gpt-test", api_key="fake-key")
        result = provider.complete(system="be helpful", prompt="say hi")

    mock_openai.assert_called_once_with(api_key="fake-key")
    fake_client.chat.completions.create.assert_called_once_with(
        model="gpt-test",
        max_tokens=4096,
        messages=[
            {"role": "system", "content": "be helpful"},
            {"role": "user", "content": "say hi"},
        ],
    )
    assert result == "hello from gpt"


def test_gemini_provider_shapes_request_and_extracts_text():
    fake_response = SimpleNamespace(text="hello from gemini")
    fake_client = mock.Mock()
    fake_client.models.generate_content.return_value = fake_response

    with mock.patch("google.genai.Client", return_value=fake_client) as mock_client:
        provider = GeminiProvider(model="gemini-test", api_key="fake-key")
        result = provider.complete(system="be helpful", prompt="say hi")

    mock_client.assert_called_once_with(api_key="fake-key")
    call_kwargs = fake_client.models.generate_content.call_args.kwargs
    assert call_kwargs["model"] == "gemini-test"
    assert call_kwargs["contents"] == "say hi"
    assert call_kwargs["config"].system_instruction == "be helpful"
    assert result == "hello from gemini"


def test_provider_raises_actionable_error_when_sdk_missing():
    with mock.patch.dict("sys.modules", {"anthropic": None}):
        with pytest.raises(RuntimeError, match=r"pip install anthropic"):
            AnthropicProvider()


def test_static_provider_returns_configured_response():
    with override_settings(ANVIL_AI_STATIC_RESPONSE="canned response"):
        assert StaticProvider().complete(system="x", prompt="y") == "canned response"


def test_static_provider_without_configured_response_raises():
    with pytest.raises(RuntimeError, match="ANVIL_AI_STATIC_RESPONSE"):
        StaticProvider().complete(system="x", prompt="y")


def test_get_provider_resolves_dotted_path_from_settings():
    with override_settings(
        ANVIL_AI_PROVIDER="django_anvil.ai.providers.StaticProvider",
        ANVIL_AI_STATIC_RESPONSE="ok",
    ):
        provider = get_provider()
    assert isinstance(provider, StaticProvider)


def test_get_provider_defaults_to_openai():
    with mock.patch("openai.OpenAI"):
        provider = get_provider()
    assert isinstance(provider, OpenAIProvider)
