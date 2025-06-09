"""프롬프트 생성기"""

import importlib.resources
from functools import lru_cache

from selvage.src.utils.base_console import console
from selvage.src.utils.file_utils import is_ignore_file
from selvage.src.utils.token.models import ReviewRequest

from .models import (
    ReviewPrompt,
    ReviewPromptWithFileContent,
    SystemPrompt,
    UserPrompt,
    UserPromptWithFileContent,
)

PROMPT_PATH = "selvage.resources.prompt"
PROMPT_FILE_NAME = "code_review_system_prompt"
VERSION = "v3"


class PromptGenerator:
    """프롬프트 생성기 클래스"""

    @classmethod
    @lru_cache(maxsize=1)
    def _get_code_review_system_prompt(cls) -> str:
        """코드 리뷰 시스템 프롬프트를 불러옵니다.

        Returns:
            str: 코드 리뷰 시스템 프롬프트
        """
        try:
            file_ref = importlib.resources.files(f"{PROMPT_PATH}.{VERSION}").joinpath(
                f"{PROMPT_FILE_NAME}_{VERSION}.txt"
            )
            with importlib.resources.as_file(file_ref) as file_path:
                return file_path.read_text(encoding="utf-8")
        except Exception as e:
            error_message = f"시스템 프롬프트 파일을 찾을 수 없습니다 (경로: '{PROMPT_PATH}.{VERSION}/{PROMPT_FILE_NAME}_{VERSION}.txt'). 원본 오류: {e}"
            console.error(error_message, exception=e)
            raise FileNotFoundError(error_message) from e

    def create_code_review_prompt(
        self, review_request: ReviewRequest
    ) -> ReviewPrompt | ReviewPromptWithFileContent:
        """코드 리뷰 요청으로부터 프롬프트를 생성합니다.

        use_full_context 플래그에 따라 적절한 프롬프트 생성 메소드를 호출합니다.

        Args:
            review_request: 리뷰 요청 객체

        Returns:
            ReviewPrompt | ReviewPromptWithFileContent: 생성된 리뷰 프롬프트 객체
        """
        if review_request.use_full_context:
            return self._create_full_context_code_review_prompt(review_request)
        else:
            return self._create_simple_code_review_prompt(review_request)

    def _create_simple_code_review_prompt(
        self, review_request: ReviewRequest
    ) -> ReviewPrompt:
        """기본 코드 리뷰 프롬프트를 생성합니다.

        Args:
            review_request: 리뷰 요청 객체

        Returns:
            ReviewPrompt: 생성된 리뷰 프롬프트 객체
        """
        system_prompt_content = self._get_code_review_system_prompt()
        system_prompt = SystemPrompt(role="system", content=system_prompt_content)
        user_prompts = []

        for file in review_request.processed_diff.files:
            # 바이너리 파일인지 먼저 확인
            if is_ignore_file(file.filename):
                # 바이너리 파일은 처리하지 않고 건너뜁니다
                continue

            file_name = file.filename
            if file_name not in review_request.file_paths:
                review_request.file_paths.append(file_name)

            for hunk_idx, hunk in enumerate(file.hunks):
                safe_original = hunk.get_before_code()
                safe_modified = hunk.get_after_code()
                user_prompt = UserPrompt(
                    hunk_idx=str(hunk_idx + 1),
                    file_name=file_name,
                    before_code=f"```{file.language}\n{safe_original}\n```",
                    after_code=f"```{file.language}\n{safe_modified}\n```",
                    after_code_start_line_number=hunk.start_line_modified,
                    language=file.language,
                )
                user_prompts.append(user_prompt)

        return ReviewPrompt(system_prompt=system_prompt, user_prompts=user_prompts)

    def _create_full_context_code_review_prompt(
        self, review_request: ReviewRequest
    ) -> ReviewPromptWithFileContent:
        """코드 리뷰 요청으로부터 파일 내용을 포함한 프롬프트를 생성합니다.

        Args:
            review_request: 리뷰 요청 객체

        Returns:
            ReviewPromptWithFileContent: 생성된 파일 내용 포함 리뷰 프롬프트 객체
        """
        if not review_request.use_full_context:
            raise ValueError("full context 플래그가 켜져있어야 합니다.")

        system_prompt_content = self._get_code_review_system_prompt()

        # 시스템 프롬프트 생성
        system_prompt = SystemPrompt(role="system", content=system_prompt_content)
        user_prompts: list[UserPromptWithFileContent] = []

        for file in review_request.processed_diff.files:
            # 바이너리 파일인지 먼저 확인
            if is_ignore_file(file.filename):
                # 바이너리 파일은 처리하지 않고 건너뜁니다
                continue

            try:
                # 파일 내용 읽기 시도
                if not file.file_content:
                    console.warning(f"파일 내용이 없습니다. 파일 경로: {file.filename}")
                    file_content = ""
                else:
                    file_content = file.file_content

                # user_prompt 생성
                user_prompt = UserPromptWithFileContent(
                    file_name=file.filename,
                    file_content=file_content,
                    hunks=file.hunks,
                    language=file.language,
                )
                user_prompts.append(user_prompt)

            except FileNotFoundError:
                # 파일을 찾을 수 없는 경우도 건너뜁니다
                continue

        review_prompt_with_file_content = ReviewPromptWithFileContent(
            system_prompt=system_prompt,
            user_prompts=user_prompts,
        )

        return review_prompt_with_file_content
