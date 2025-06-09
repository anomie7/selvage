"""모델 제공자 enum 정의 모듈"""

from enum import Enum

from selvage.src.exceptions.unsupported_provider_error import UnsupportedProviderError


class ModelProvider(Enum):
    """모델 제공자 enum"""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"

    @classmethod
    def from_string(cls, provider_str: str) -> "ModelProvider":
        """문자열을 ModelProvider enum으로 변환합니다.

        Args:
            provider_str: provider 문자열

        Returns:
            ModelProvider: 해당하는 enum 값

        Raises:
            UnsupportedProviderError: 지원하지 않는 provider인 경우
        """
        for provider in cls:
            if provider.value == provider_str.lower():
                return provider

        valid_providers = [p.value for p in cls]
        raise UnsupportedProviderError(
            f"지원하지 않는 provider '{provider_str}'. 유효한 값: {valid_providers}"
        )

    def get_display_name(self) -> str:
        """사용자에게 표시할 provider 이름을 반환합니다."""
        display_names = {
            ModelProvider.OPENAI: "OpenAI",
            ModelProvider.ANTHROPIC: "Anthropic",
            ModelProvider.GOOGLE: "Gemini",
        }
        return display_names[self]

    def get_env_var_name(self) -> str:
        """해당 provider의 환경 변수 이름을 반환합니다."""
        env_vars = {
            ModelProvider.OPENAI: "OPENAI_API_KEY",
            ModelProvider.ANTHROPIC: "ANTHROPIC_API_KEY",
            ModelProvider.GOOGLE: "GEMINI_API_KEY",
        }
        return env_vars[self]

    def get_api_key_command_name(self) -> str:
        """해당 provider의 API 키 설정 명령어 이름을 반환합니다."""
        command_names = {
            ModelProvider.OPENAI: "openai",
            ModelProvider.ANTHROPIC: "claude",
            ModelProvider.GOOGLE: "google",
        }
        return command_names[self]
