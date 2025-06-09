"""FormattedHunk: 프롬프트 사용을 위해 가공된 Hunk 데이터 클래스 모듈"""

from dataclasses import dataclass

from selvage.src.diff_parser.models import Hunk


@dataclass
class FormattedHunk:
    """프롬프트 사용을 위해 가공된 Hunk 데이터 클래스"""

    hunk_idx: str
    before_code: str
    after_code: str
    after_code_start_line_number: int
    after_code_line_numbers: list[int]

    def __init__(
        self,
        hunk: Hunk,
        hunk_idx: int,
        language: str,
    ) -> None:
        """FormattedHunk 객체를 초기화합니다.

        Args:
            hunk: 원본 Hunk 객체
            hunk_idx: Hunk의 인덱스
            language: 코드 언어
        """
        self.hunk_idx = str(hunk_idx + 1)
        self.before_code = f"```{language}\n{hunk.get_before_code()}\n```"
        self.after_code = f"```{language}\n{hunk.get_after_code()}\n```"
        self.after_code_start_line_number = hunk.start_line_modified
        self.after_code_line_numbers = list(
            range(
                hunk.start_line_modified,
                hunk.start_line_modified + hunk.line_count_modified,
            )
        )
