import re
from dataclasses import dataclass


@dataclass
class Hunk:
    """Git diff의 hunk를 나타내는 클래스.

    Hunk는 코드 변경 사항의 단일 덩어리를 나타내며, 변경된 코드의 헤더와 실제 내용,
    변경 전/후의 코드, 그리고 관련 메타데이터를 포함합니다.
    """

    header: str
    content: str
    before_code: str
    after_code: str
    start_line_original: int
    line_count_original: int
    start_line_modified: int
    line_count_modified: int

    def get_before_code(self) -> str:
        """원본 코드를 반환합니다.

        Returns:
            str: 원본 코드
        """
        return self.before_code

    def get_after_code(self) -> str:
        """수정 코드를 반환합니다.

        Returns:
            str: 수정 코드
        """
        return self.after_code

    @staticmethod
    def from_hunk_text(hunk_text: str) -> "Hunk":
        """hunk 텍스트로부터 Hunk 객체를 생성합니다.

        Args:
            hunk_text: git diff 형식의 hunk 텍스트

        Returns:
            Hunk: 생성된 Hunk 객체
        """
        lines = hunk_text.split("\n")
        header = lines[0]
        content = "\n".join(lines[1:])

        (
            start_line_original,
            line_count_original,
            start_line_modified,
            line_count_modified,
        ) = Hunk._parse_header(header)
        before_code, after_code = Hunk._parse_content_to_code(content)

        return Hunk(
            header=header,
            content=content,
            before_code=before_code,
            after_code=after_code,
            start_line_original=start_line_original,
            line_count_original=line_count_original,
            start_line_modified=start_line_modified,
            line_count_modified=line_count_modified,
        )

    @staticmethod
    def _parse_header(header: str) -> tuple[int, int, int, int]:
        """hunk 헤더 문자열을 파싱하여 시작 줄 번호와 줄 수를 추출합니다.

        Args:
            header: git diff 형식의 hunk 헤더 문자열 (예: "@@ -3,6 +40,7 @@")

        Returns:
            tuple[int, int, int, int]: (original 시작 줄, original 줄 수, modified 시작 줄, modified 줄 수)
        """
        match = re.match(r"@@ -(\d+),(\d+) \+(\d+),(\d+) @@", header)
        if match:
            start_line_original = int(match.group(1))
            line_count_original = int(match.group(2))
            start_line_modified = int(match.group(3))
            line_count_modified = int(match.group(4))
        else:
            start_line_original = 0
            line_count_original = 0
            start_line_modified = 0
            line_count_modified = 0
        return (
            start_line_original,
            line_count_original,
            start_line_modified,
            line_count_modified,
        )

    @staticmethod
    def _parse_content_to_code(content: str) -> tuple[str, str]:
        """hunk 내용을 파싱하여 original 코드와 modified 코드로 분리합니다.

        Args:
            content: git diff 형식의 hunk 내용 문자열

        Returns:
            tuple[str, str]: (original 코드, modified 코드)
        """
        original_lines = []
        modified_lines = []

        for line in content.splitlines():
            prefix = line[0] if line else ""
            # diff 접두사 유지: LLM이 추가(+), 삭제(-), 문맥( ) 라인을 구분하여 분석하는 데 사용
            code_part = line if line else ""

            if prefix == "-":  # 제거된 라인
                original_lines.append(code_part)
            elif prefix == "+":  # 추가된 라인
                modified_lines.append(code_part)
            elif prefix == " ":  # 변경되지 않은 컨텍스트 라인
                original_lines.append(code_part)
                modified_lines.append(code_part)
            else:
                # 표준 diff 형식이 아닌 경우 (방어적 코딩)
                original_lines.append(line)
                modified_lines.append(line)

        return "\n".join(original_lines), "\n".join(modified_lines)
