"""
API 키가 없을 때 발생하는 예외 클래스 정의 모듈입니다.
"""

from typing import TYPE_CHECKING

from selvage.src.exceptions.llm_gateway_error import LLMGatewayError

if TYPE_CHECKING:
    from selvage.src.models.model_provider import ModelProvider


class APIKeyNotFoundError(LLMGatewayError):
    """API 키가 없을 때 발생하는 예외"""

    def __init__(self, provider: "ModelProvider") -> None:
        self.provider = provider
        super().__init__(
            f"API 키가 제공되지 않았습니다. 'selvage --set-{provider.get_api_key_command_name()}-key' 명령을 사용하여 "
            f"API 키를 설정하세요."
        )
