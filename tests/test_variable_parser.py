"""変数定義パーサーのユニットテスト

variable_parser.pyの基本機能をテストする。
- WORKING-STORAGE SECTIONの検出
- レベル番号、変数名、VALUE句、PIC句、COPY句の解析
- グループ項目の親子関係構築
- 全角文字を含む識別子の認識
- FILLER項目とレベル88条件名のスキップ
- COPY句のみの集団項目の除外
"""

import pytest

from cobol_static_checker import NormalizedLine, VariableDefinition
from cobol_static_checker.variable_parser import parse_variables


def _make_line(line_number: int, content: str) -> NormalizedLine:
    """テスト用のNormalizedLineを生成するヘルパー"""
    return NormalizedLine(
        line_number=line_number,
        content=content,
        is_continuation=False,
    )


class TestWorkingStorageDetection:
    """WORKING-STORAGE SECTIONの検出テスト"""

    def test_セクションが存在しない場合は空リスト(self):
        """WORKING-STORAGE SECTIONがない場合は空リストを返す"""
        lines = [
            _make_line(1, "       IDENTIFICATION DIVISION."),
            _make_line(2, "       PROGRAM-ID. TEST."),
        ]
        result = parse_variables(lines)
        assert result == []

    def test_セクション内の変数を解析(self):
        """WORKING-STORAGE SECTION内の変数定義を正しく解析する"""
        lines = [
            _make_line(1, "       WORKING-STORAGE SECTION."),
            _make_line(2, "       01 WK-AREA."),
            _make_line(3, "         05 WK-NAME PIC X(10)."),
            _make_line(4, "       PROCEDURE DIVISION."),
        ]
        result = parse_variables(lines)
        assert len(result) == 2
        assert result[0].name == "WK-AREA"
        assert result[1].name == "WK-NAME"

    def test_PROCEDURE_DIVISIONでセクション終了(self):
        """PROCEDURE DIVISIONでWORKING-STORAGE SECTIONが終了する"""
        lines = [
            _make_line(1, "       WORKING-STORAGE SECTION."),
            _make_line(2, "       01 WK-VAR PIC X(5)."),
            _make_line(3, "       PROCEDURE DIVISION."),
            _make_line(4, "       01 NOT-A-VAR PIC X(5)."),
        ]
        result = parse_variables(lines)
        assert len(result) == 1
        assert result[0].name == "WK-VAR"


class TestVariableParsing:
    """変数定義の解析テスト"""

    def test_PIC句ありの基本変数(self):
        """PIC句を持つ基本変数が正しく解析される"""
        lines = [
            _make_line(1, "       WORKING-STORAGE SECTION."),
            _make_line(2, "       01 WK-CODE PIC X(10)."),
        ]
        result = parse_variables(lines)
        assert len(result) == 1
        assert result[0].level == 1
        assert result[0].name == "WK-CODE"
        assert result[0].is_group is False
        assert result[0].has_value is False
        assert result[0].has_copy is False

    def test_VALUE句ありの変数(self):
        """VALUE句を持つ変数が正しく解析される"""
        lines = [
            _make_line(1, "       WORKING-STORAGE SECTION."),
            _make_line(2, "       01 WK-FLAG PIC X(1) VALUE 'Y'."),
        ]
        result = parse_variables(lines)
        assert len(result) == 1
        assert result[0].has_value is True

    def test_グループ項目の判定(self):
        """PIC句なしの変数はグループ項目として判定される"""
        lines = [
            _make_line(1, "       WORKING-STORAGE SECTION."),
            _make_line(2, "       01 WK-GROUP."),
            _make_line(3, "         05 WK-ITEM PIC X(5)."),
        ]
        result = parse_variables(lines)
        assert result[0].is_group is True
        assert result[1].is_group is False

    def test_COPY句ありの変数(self):
        """COPY句を持つ変数が正しく解析される"""
        lines = [
            _make_line(1, "       WORKING-STORAGE SECTION."),
            _make_line(2, "       01 WK-COPY-AREA."),
            _make_line(3, "         COPY CPYBOOK1."),
        ]
        # COPY句のみの集団項目は除外されるが、COPY句の検出自体をテスト
        # COPY句は変数定義行内にある場合に検出される
        result = parse_variables(lines)
        # WK-COPY-AREAはCOPY句のみの集団項目（子孫なし）なので除外される
        assert len(result) == 0

    def test_PICTURE句の認識(self):
        """PICTUREキーワードも正しく認識される"""
        lines = [
            _make_line(1, "       WORKING-STORAGE SECTION."),
            _make_line(2, "       01 WK-FULL PICTURE X(10)."),
        ]
        result = parse_variables(lines)
        assert len(result) == 1
        assert result[0].is_group is False


class TestFillerAndLevel88:
    """FILLER項目とレベル88条件名のテスト"""

    def test_FILLER項目はスキップ(self):
        """FILLER項目は結果に含まれない"""
        lines = [
            _make_line(1, "       WORKING-STORAGE SECTION."),
            _make_line(2, "       01 WK-REC."),
            _make_line(3, "         05 FILLER PIC X(5)."),
            _make_line(4, "         05 WK-DATA PIC X(10)."),
        ]
        result = parse_variables(lines)
        names = [v.name for v in result]
        assert "FILLER" not in names
        assert "WK-DATA" in names

    def test_レベル88条件名はスキップ(self):
        """レベル88の条件名は結果に含まれない"""
        lines = [
            _make_line(1, "       WORKING-STORAGE SECTION."),
            _make_line(2, "       01 WK-STATUS PIC X(1)."),
            _make_line(3, "         88 STATUS-OK VALUE 'Y'."),
            _make_line(4, "         88 STATUS-NG VALUE 'N'."),
        ]
        result = parse_variables(lines)
        assert len(result) == 1
        assert result[0].name == "WK-STATUS"


class TestHierarchy:
    """親子関係構築のテスト"""

    def test_基本的な親子関係(self):
        """グループ項目と従属項目の親子関係が正しく構築される"""
        lines = [
            _make_line(1, "       WORKING-STORAGE SECTION."),
            _make_line(2, "       01 WK-GROUP."),
            _make_line(3, "         05 WK-CHILD1 PIC X(5)."),
            _make_line(4, "         05 WK-CHILD2 PIC 9(3)."),
        ]
        result = parse_variables(lines)
        assert result[0].name == "WK-GROUP"
        assert result[0].parent_name is None
        assert result[1].parent_name == "WK-GROUP"
        assert result[2].parent_name == "WK-GROUP"

    def test_ネストした親子関係(self):
        """複数レベルのネストした親子関係が正しく構築される"""
        lines = [
            _make_line(1, "       WORKING-STORAGE SECTION."),
            _make_line(2, "       01 WK-TOP."),
            _make_line(3, "         05 WK-MID."),
            _make_line(4, "           10 WK-LEAF PIC X(5)."),
        ]
        result = parse_variables(lines)
        assert result[0].name == "WK-TOP"
        assert result[0].parent_name is None
        assert result[1].name == "WK-MID"
        assert result[1].parent_name == "WK-TOP"
        assert result[2].name == "WK-LEAF"
        assert result[2].parent_name == "WK-MID"

    def test_レベル番号の戻り(self):
        """レベル番号が戻った場合に親が正しく切り替わる"""
        lines = [
            _make_line(1, "       WORKING-STORAGE SECTION."),
            _make_line(2, "       01 WK-GROUP1."),
            _make_line(3, "         05 WK-A PIC X(5)."),
            _make_line(4, "       01 WK-GROUP2."),
            _make_line(5, "         05 WK-B PIC X(5)."),
        ]
        result = parse_variables(lines)
        assert result[0].name == "WK-GROUP1"
        assert result[0].parent_name is None
        assert result[1].name == "WK-A"
        assert result[1].parent_name == "WK-GROUP1"
        assert result[2].name == "WK-GROUP2"
        assert result[2].parent_name is None
        assert result[3].name == "WK-B"
        assert result[3].parent_name == "WK-GROUP2"

    def test_レベル77は独立項目(self):
        """レベル77は独立項目として親なしになる"""
        lines = [
            _make_line(1, "       WORKING-STORAGE SECTION."),
            _make_line(2, "       77 WK-STANDALONE PIC X(10)."),
        ]
        result = parse_variables(lines)
        assert len(result) == 1
        assert result[0].level == 77
        assert result[0].parent_name is None


class TestZenkakuIdentifiers:
    """全角文字を含む識別子のテスト"""

    def test_漢字変数名(self):
        """漢字を含む変数名が正しく認識される"""
        lines = [
            _make_line(1, "       WORKING-STORAGE SECTION."),
            _make_line(2, "       01 顧客名 PIC X(20)."),
        ]
        result = parse_variables(lines)
        assert len(result) == 1
        assert result[0].name == "顧客名"

    def test_カタカナ変数名(self):
        """カタカナを含む変数名が正しく認識される"""
        lines = [
            _make_line(1, "       WORKING-STORAGE SECTION."),
            _make_line(2, "       01 カナ名称 PIC X(20)."),
        ]
        result = parse_variables(lines)
        assert len(result) == 1
        assert result[0].name == "カナ名称"

    def test_全角英数混在変数名(self):
        """全角英数字を含む変数名が正しく認識される"""
        lines = [
            _make_line(1, "       WORKING-STORAGE SECTION."),
            _make_line(2, "       01 ＷＫ項目１ PIC X(10)."),
        ]
        result = parse_variables(lines)
        assert len(result) == 1
        assert result[0].name == "ＷＫ項目１"


class TestCopyOnlyGroupExclusion:
    """COPY句のみの集団項目除外テスト"""

    def test_COPY句のみの集団項目は除外(self):
        """COPY句のみで子孫がない集団項目は除外される"""
        lines = [
            _make_line(1, "       WORKING-STORAGE SECTION."),
            _make_line(2, "       01 COPY-ONLY-GROUP."),
            _make_line(3, "         COPY CPYBOOK."),
        ]
        result = parse_variables(lines)
        # COPY-ONLY-GROUPはCOPY句のみの集団項目で子孫なし → 除外
        assert len(result) == 0

    def test_子孫ありのグループ項目は保持(self):
        """子孫を持つグループ項目はCOPY句があっても保持される"""
        lines = [
            _make_line(1, "       WORKING-STORAGE SECTION."),
            _make_line(2, "       01 WK-GROUP."),
            _make_line(3, "         05 WK-CHILD PIC X(5)."),
        ]
        result = parse_variables(lines)
        assert len(result) == 2
        assert result[0].name == "WK-GROUP"

    def test_COPY句なしのグループ項目は保持(self):
        """COPY句がないグループ項目は子孫がなくても保持される"""
        lines = [
            _make_line(1, "       WORKING-STORAGE SECTION."),
            _make_line(2, "       01 WK-EMPTY-GROUP."),
        ]
        result = parse_variables(lines)
        assert len(result) == 1
        assert result[0].name == "WK-EMPTY-GROUP"


class TestStatementBuffering:
    """文のバッファリング（ピリオド区切り）テスト"""

    def test_複数行にまたがる文(self):
        """ピリオドで区切られるまで複数行が1つの文として処理される"""
        lines = [
            _make_line(1, "       WORKING-STORAGE SECTION."),
            _make_line(2, "       01 WK-LONG-NAME"),
            _make_line(3, "           PIC X(100)"),
            _make_line(4, "           VALUE SPACES."),
        ]
        result = parse_variables(lines)
        assert len(result) == 1
        assert result[0].name == "WK-LONG-NAME"
        assert result[0].has_value is True
        assert result[0].is_group is False
