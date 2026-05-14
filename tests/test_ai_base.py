"""Tests for AI Provider abstract base class"""

from filepilot.ai.base import AIProvider


class TestAIProvider:
    """AIProvider is an ABC — test its default method implementations"""

    def test_cannot_instantiate_directly(self):
        """AIProvider is abstract — must be subclassed"""
        import pytest
        with pytest.raises(TypeError):
            AIProvider()  # type: ignore

    def test_concrete_subclass(self):
        """Subclass implementing abstract methods can be instantiated"""

        class ConcreteProvider(AIProvider):
            @property
            def is_available(self) -> bool:
                return True

            @property
            def provider_name(self) -> str:
                return "Test"

            def generate(self, prompt, system_prompt=None, temperature=0.7,
                         max_tokens=2048, stream=False, on_token=None) -> str:
                return "generated"

        provider = ConcreteProvider()
        assert provider.is_available is True
        assert provider.provider_name == "Test"

    def test_chat_default_implementation(self):
        """Default chat() concatenates messages into a single prompt"""

        class ConcreteProvider(AIProvider):
            @property
            def is_available(self) -> bool:
                return True

            @property
            def provider_name(self) -> str:
                return "Test"

            def generate(self, prompt, system_prompt=None, temperature=0.7,
                         max_tokens=2048, stream=False, on_token=None) -> str:
                return f"PROMPT:{prompt}|SYS:{system_prompt}"

        provider = ConcreteProvider()
        messages = [
            {"role": "system", "content": "Be helpful"},
            {"role": "user", "content": "Hello"},
        ]
        result = provider.chat(messages, temperature=0.5, max_tokens=100)
        assert "[System] Be helpful" in result
        assert "Hello" in result
        assert "PROMPT:" in result
        assert "SYS:None" in result  # chat() doesn't pass system_prompt to generate()

    def test_embed_default_returns_empty_list(self):
        """Default embed() returns an empty list"""

        class ConcreteProvider(AIProvider):
            @property
            def is_available(self) -> bool:
                return True

            @property
            def provider_name(self) -> str:
                return "Test"

            def generate(self, prompt, system_prompt=None, temperature=0.7,
                         max_tokens=2048, stream=False, on_token=None) -> str:
                return ""

        provider = ConcreteProvider()
        assert provider.embed("hello") == []

    def test_get_available_models_default_returns_empty_list(self):
        """Default get_available_models() returns an empty list"""

        class ConcreteProvider(AIProvider):
            @property
            def is_available(self) -> bool:
                return True

            @property
            def provider_name(self) -> str:
                return "Test"

            def generate(self, prompt, system_prompt=None, temperature=0.7,
                         max_tokens=2048, stream=False, on_token=None) -> str:
                return ""

        provider = ConcreteProvider()
        assert provider.get_available_models() == []

    def test_generate_with_stream_callback(self):
        """Stream callback is forwarded correctly"""

        class ConcreteProvider(AIProvider):
            @property
            def is_available(self) -> bool:
                return True

            @property
            def provider_name(self) -> str:
                return "Test"

            def generate(self, prompt, system_prompt=None, temperature=0.7,
                         max_tokens=2048, stream=False, on_token=None) -> str:
                if stream and on_token:
                    for token in ["Hel", "lo", " World"]:
                        on_token(token)
                return "Hello World"

        provider = ConcreteProvider()
        tokens = []

        def on_token(t: str):
            tokens.append(t)

        result = provider.generate("hi", stream=True, on_token=on_token)
        assert result == "Hello World"
        assert tokens == ["Hel", "lo", " World"]
