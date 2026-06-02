from evocode_orchard_lite.models.base import Model

__all__ = ["Model", "LiteLLMChatModel", "LocalOpenAIModel"]


def __getattr__(name: str):
    if name == "LiteLLMChatModel":
        from evocode_orchard_lite.models.litellm_chat_model import LiteLLMChatModel

        return LiteLLMChatModel
    if name == "LocalOpenAIModel":
        from evocode_orchard_lite.models.local_openai_model import LocalOpenAIModel

        return LocalOpenAIModel
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
