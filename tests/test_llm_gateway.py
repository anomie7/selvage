import unittest
from unittest.mock import patch

from selvage.src.exceptions.api_key_not_found_error import APIKeyNotFoundError
from selvage.src.exceptions.invalid_model_provider_error import (
    InvalidModelProviderError,
)
from selvage.src.exceptions.unsupported_model_error import UnsupportedModelError
from selvage.src.llm_gateway import (
    ClaudeGateway,
    GatewayFactory,
    GoogleGateway,
    OpenAIGateway,
)
from selvage.src.model_config import ModelInfoDict, ModelProvider, get_model_info


class TestOpenAIGateway(unittest.TestCase):
    @patch("selvage.src.llm_gateway.openai_gateway.get_api_key")
    def test_init_with_valid_model(self, mock_get_api_key):
        """API 키와 유효한 모델로 OpenAIGateway 초기화를 테스트합니다."""
        # API 키 모킹
        mock_get_api_key.return_value = "fake-api-key"

        # 테스트할 모델 가져오기
        model_info = get_model_info("gpt-4o")
        self.assertIsNotNone(model_info)

        # 게이트웨이 생성
        gateway = OpenAIGateway(model_info)

        # 검증
        self.assertEqual(gateway.get_model_name(), "gpt-4o")
        self.assertEqual(gateway.model, model_info)
        mock_get_api_key.assert_called_once_with(ModelProvider.OPENAI)

    @patch("selvage.src.llm_gateway.openai_gateway.get_api_key")
    def test_init_with_invalid_model_provider(self, mock_get_api_key):
        """잘못된 모델 제공자로 OpenAIGateway 초기화 시 예외 발생을 테스트합니다."""
        # API 키 모킹
        mock_get_api_key.return_value = "fake-api-key"

        # 실제 존재하는 Claude 모델 정보를 반환하도록 모킹
        claude_model_info: ModelInfoDict = {
            "full_name": "claude-sonnet-4-20250514",
            "aliases": ["claude-sonnet-4"],
            "description": "Claude 모델",
            "provider": ModelProvider.ANTHROPIC,  # OpenAI가 아닌 다른 제공자
            "params": {
                "temperature": 0.0,
            },
            "thinking_mode": False,
            "pricing": {
                "input": 0.0,
                "output": 0.0,
                "description": "Claude 모델",
            },
            "context_limit": 100000,
        }

        # 예외 발생 확인
        with self.assertRaises(InvalidModelProviderError) as context:
            OpenAIGateway(claude_model_info)

        # 예외 속성 검증
        self.assertEqual(context.exception.model_name, "claude-sonnet-4-20250514")
        self.assertEqual(context.exception.expected_provider, ModelProvider.OPENAI)

    @patch("selvage.src.llm_gateway.openai_gateway.get_api_key")
    def test_init_without_api_key(self, mock_get_api_key):
        """API 키 없이 OpenAIGateway 초기화 시 예외 발생을 테스트합니다."""
        # API 키 없음 모킹
        mock_get_api_key.return_value = None

        # 테스트할 모델 가져오기
        model_info = get_model_info("gpt-4o")
        self.assertIsNotNone(model_info)

        # 예외 발생 확인
        with self.assertRaises(APIKeyNotFoundError) as context:
            OpenAIGateway(model_info)

        # 예외 속성 검증
        self.assertEqual(context.exception.provider, ModelProvider.OPENAI)


class TestClaudeGateway(unittest.TestCase):
    @patch("selvage.src.llm_gateway.claude_gateway.get_api_key")
    def test_init_with_valid_model(self, mock_get_api_key):
        """API 키와 유효한 모델로 ClaudeGateway 초기화를 테스트합니다."""
        # API 키 모킹
        mock_get_api_key.return_value = "fake-api-key"

        # 테스트할 모델 가져오기
        model_info = get_model_info("claude-sonnet-4")
        self.assertIsNotNone(model_info)

        # 게이트웨이 생성
        gateway = ClaudeGateway(model_info)

        # 검증
        self.assertEqual(gateway.get_model_name(), "claude-sonnet-4-20250514")
        self.assertEqual(gateway.model, model_info)
        mock_get_api_key.assert_called_once_with(ModelProvider.ANTHROPIC)

    @patch("selvage.src.llm_gateway.claude_gateway.get_api_key")
    def test_init_with_invalid_model_provider(self, mock_get_api_key):
        """잘못된 모델 제공자로 ClaudeGateway 초기화 시 예외 발생을 테스트합니다."""
        # API 키 모킹
        mock_get_api_key.return_value = "fake-api-key"

        # 실제 존재하는 OpenAI 모델 정보를 반환하도록 모킹
        openai_model_info: ModelInfoDict = {
            "full_name": "gpt-4o",
            "aliases": [],
            "description": "OpenAI 모델",
            "provider": ModelProvider.OPENAI,  # Claude가 아닌 다른 제공자
            "params": {
                "temperature": 0.0,
            },
            "thinking_mode": False,
            "pricing": {
                "input": 0.0,
                "output": 0.0,
                "description": "OpenAI 모델",
            },
            "context_limit": 100000,
        }

        # 예외 발생 확인
        with self.assertRaises(InvalidModelProviderError) as context:
            ClaudeGateway(openai_model_info)

        # 예외 속성 검증
        self.assertEqual(context.exception.model_name, "gpt-4o")
        self.assertEqual(context.exception.expected_provider, ModelProvider.ANTHROPIC)

    @patch("selvage.src.llm_gateway.claude_gateway.get_api_key")
    def test_init_without_api_key(self, mock_get_api_key):
        """API 키 없이 ClaudeGateway 초기화 시 예외 발생을 테스트합니다."""
        # API 키 없음 모킹
        mock_get_api_key.return_value = None

        # 테스트할 모델 가져오기
        model_info = get_model_info("claude-sonnet-4")
        self.assertIsNotNone(model_info)

        # 예외 발생 확인
        with self.assertRaises(APIKeyNotFoundError) as context:
            ClaudeGateway(model_info)

        # 예외 속성 검증
        self.assertEqual(context.exception.provider, ModelProvider.ANTHROPIC)


class TestGoogleGateway(unittest.TestCase):
    @patch("selvage.src.llm_gateway.google_gateway.get_api_key")
    def test_init_with_valid_model(self, mock_get_api_key):
        """API 키와 유효한 모델로 GoogleGateway 초기화를 테스트합니다."""
        # API 키 모킹
        mock_get_api_key.return_value = "fake-api-key"

        model_info = get_model_info("gemini-2.5-pro")
        self.assertIsNotNone(model_info)

        # 게이트웨이 생성
        gateway = GoogleGateway(model_info)

        # 검증
        self.assertEqual(gateway.get_model_name(), model_info["full_name"])
        self.assertEqual(gateway.model, model_info)
        mock_get_api_key.assert_called_once_with(ModelProvider.GOOGLE)

    @patch("selvage.src.llm_gateway.google_gateway.get_api_key")
    def test_init_with_invalid_model_provider(self, mock_get_api_key):
        """잘못된 모델 제공자로 GoogleGateway 초기화 시 예외 발생을 테스트합니다."""
        # API 키 모킹
        mock_get_api_key.return_value = "fake-api-key"

        # 실제 존재하는 OpenAI 모델 정보를 반환하도록 모킹 (Claude 테스트와 유사)
        openai_model_info: ModelInfoDict = {
            "full_name": "gpt-4o",
            "aliases": [],
            "description": "OpenAI 모델",
            "provider": ModelProvider.OPENAI,  # Google이 아닌 다른 제공자
            "params": {
                "temperature": 0.0,
            },
            "thinking_mode": False,
            "pricing": {
                "input": 0.0,
                "output": 0.0,
                "description": "OpenAI 모델",
            },
            "context_limit": 100000,
        }

        # 예외 발생 확인
        with self.assertRaises(InvalidModelProviderError) as context:
            GoogleGateway(openai_model_info)

        # 예외 속성 검증
        self.assertEqual(context.exception.model_name, "gpt-4o")
        self.assertEqual(context.exception.expected_provider, ModelProvider.GOOGLE)

    @patch("selvage.src.llm_gateway.google_gateway.get_api_key")
    def test_init_without_api_key(self, mock_get_api_key):
        """API 키 없이 GoogleGateway 초기화 시 예외 발생을 테스트합니다."""
        # API 키 없음 모킹
        mock_get_api_key.return_value = None

        # 테스트할 모델 가져오기 (test_init_with_valid_model과 동일 로직)
        try:
            model_info = get_model_info("gemini-pro")
        except UnsupportedModelError:
            model_info: ModelInfoDict = {
                "full_name": "gemini-2.5-pro",
                "aliases": [],
                "description": "Google 모델",
                "provider": ModelProvider.GOOGLE,
                "params": {"temperature": 0.0},
                "thinking_mode": False,
                "pricing": {
                    "input": 0.0,
                    "output": 0.0,
                    "description": "Google 모델",
                },
                "context_limit": 100000,
            }
            print(
                "Warning: 'gemini-2.5-pro' model not found in available_models. Using mock data for TestGoogleGateway."
            )
        self.assertIsNotNone(model_info)

        # 예외 발생 확인
        with self.assertRaises(APIKeyNotFoundError) as context:
            GoogleGateway(model_info)

        # 예외 속성 검증
        self.assertEqual(context.exception.provider, ModelProvider.GOOGLE)


class TestCreateLLMGateway(unittest.TestCase):
    @patch("selvage.src.llm_gateway.openai_gateway.get_api_key")
    def test_create_openai_gateway(self, mock_get_api_key):
        """OpenAI 모델명으로 get_llm_gateway 호출 시 실제 OpenAIGateway 반환을 테스트합니다."""
        mock_get_api_key.return_value = "fake-api-key"

        gateway = GatewayFactory.create("gpt-4o")

        # 검증 - 실제 OpenAIGateway 인스턴스인지 확인
        self.assertIsInstance(gateway, OpenAIGateway)
        self.assertEqual(gateway.get_model_name(), "gpt-4o")

    @patch("selvage.src.llm_gateway.claude_gateway.get_api_key")
    def test_create_claude_gateway(self, mock_get_api_key):
        """Claude 모델명으로 get_llm_gateway 호출 시 ClaudeGateway 반환을 테스트합니다."""
        mock_get_api_key.return_value = "fake-api-key"

        gateway = GatewayFactory.create("claude-sonnet-4")

        # 검증
        self.assertIsInstance(gateway, ClaudeGateway)
        self.assertEqual(gateway.get_model_name(), "claude-sonnet-4-20250514")

    @patch("selvage.src.llm_gateway.google_gateway.get_api_key")
    def test_create_google_gateway(self, mock_get_api_key):
        """Google 모델명으로 get_llm_gateway 호출 시 GoogleGateway 반환을 테스트합니다."""
        mock_get_api_key.return_value = "fake-api-key"

        gateway = GatewayFactory.create("gemini-2.5-pro")

        # 검증
        self.assertIsInstance(gateway, GoogleGateway)
        self.assertEqual(gateway.get_model_name(), "gemini-2.5-pro-preview-05-06")

    # UnsupportedModelError 테스트
    @patch(
        "selvage.src.llm_gateway.gateway_factory.get_model_info",
        side_effect=UnsupportedModelError("unsupported-model"),
    )
    def test_create_gateway_with_unsupported_model(self, mock_get_model_info):
        """지원하지 않는 모델명으로 get_llm_gateway 호출 시 예외 발생을 테스트합니다."""
        # 예외 발생 확인
        with self.assertRaises(UnsupportedModelError) as context:
            GatewayFactory.create("unsupported-model")

        # 예외 속성 검증
        self.assertEqual(context.exception.model_name, "unsupported-model")
        mock_get_model_info.assert_called_once_with("unsupported-model")


if __name__ == "__main__":
    unittest.main()
