"""FormattedHunk 클래스 테스트 모듈"""

from unittest.mock import MagicMock

import pytest

from selvage.src.diff_parser.models import Hunk
from selvage.src.utils.prompts.models.formatted_hunk import FormattedHunk


@pytest.fixture
def mock_hunk() -> Hunk:
    """테스트용 Hunk 객체 fixture"""
    hunk = MagicMock(spec=Hunk)
    hunk.get_before_code.return_value = "before code line1\nbefore code line2"
    hunk.get_after_code.return_value = (
        "after code line1\nafter code line2\nafter code line3"
    )
    hunk.start_line_modified = 10
    hunk.line_count_modified = 3
    return hunk


def test_formatted_hunk_creation(mock_hunk: Hunk):
    """FormattedHunk 객체 생성 및 속성 값 검증 테스트"""
    hunk_idx = 0
    language = "python"

    # 미리 호출 결과를 저장
    expected_before_code_str = mock_hunk.get_before_code()
    expected_after_code_str = mock_hunk.get_after_code()

    formatted_hunk = FormattedHunk(
        hunk=mock_hunk,
        hunk_idx=hunk_idx,
        language=language,
    )

    assert formatted_hunk.hunk_idx == str(hunk_idx + 1)
    assert (
        formatted_hunk.before_code
        == f"```{language}\n{expected_before_code_str}\n```"  # 저장된 변수 사용
    )
    assert (
        formatted_hunk.after_code
        == f"```{language}\n{expected_after_code_str}\n```"  # 저장된 변수 사용
    )
    assert formatted_hunk.after_code_start_line_number == mock_hunk.start_line_modified
    assert formatted_hunk.after_code_line_numbers == list(
        range(
            mock_hunk.start_line_modified,
            mock_hunk.start_line_modified + mock_hunk.line_count_modified,
        )
    )

    # get_before_code와 get_after_code 호출 여부만 확인
    assert mock_hunk.get_before_code.called
    assert mock_hunk.get_after_code.called


def test_formatted_hunk_line_numbers(mock_hunk: Hunk):
    """FormattedHunk의 after_code_line_numbers가 정확한지 검증하는 테스트"""
    mock_hunk.start_line_modified = 5
    mock_hunk.line_count_modified = 4
    formatted_hunk = FormattedHunk(hunk=mock_hunk, hunk_idx=0, language="java")

    expected_line_numbers = [5, 6, 7, 8]
    assert formatted_hunk.after_code_line_numbers == expected_line_numbers


def test_formatted_hunk_empty_code(mock_hunk: Hunk):
    """get_before_code 또는 get_after_code가 빈 문자열을 반환할 때의 동작 검증"""
    mock_hunk.get_before_code.return_value = ""
    mock_hunk.get_after_code.return_value = "single line"
    mock_hunk.start_line_modified = 1
    mock_hunk.line_count_modified = 1
    language = "text"

    formatted_hunk = FormattedHunk(hunk=mock_hunk, hunk_idx=0, language=language)

    assert (
        formatted_hunk.before_code == f"```{language}\n\n```"
    )  # 빈 줄이 포함되어야 함
    assert formatted_hunk.after_code == f"```{language}\nsingle line\n```"
    assert formatted_hunk.after_code_start_line_number == 1
    assert formatted_hunk.after_code_line_numbers == [1]
