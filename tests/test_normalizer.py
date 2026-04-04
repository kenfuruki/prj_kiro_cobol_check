"""正規化エンジンのユニットテスト

normalizer.pyの基本機能をテストする。
- 72カラム切り詰め
- コメント行除外
- 継続行結合
- 行番号保持
- cp932エンコーディング対応
"""

import os
import tempfile

import pytest

from cobol_static_checker import NormalizedLine
from cobol_static_checker.normalizer import _normalize_raw_lines, normalize_lines


class TestNormalizeRawLines:
    """_normalize_raw_lines関数のテスト"""

    def test_通常行の正規化(self):
        """7カラム目以降の内容が正しく抽出される"""
        # 6桁行番号 + スペース(インジケータ) + 内容
        raw = ["000100 MOVE A TO B.                                                    \n"]
        result = _normalize_raw_lines(raw)
        assert len(result) == 1
        assert result[0].line_number == 1
        assert result[0].content.strip() == "MOVE A TO B."
        assert result[0].is_continuation is False

    def test_72カラム切り詰め(self):
        """72カラムを超える部分は切り詰められる"""
        # 72カラム + 余分な文字列
        line = "000100 CONTENT" + " " * 58 + "EXTRA_BEYOND_72"
        raw = [line + "\n"]
        result = _normalize_raw_lines(raw)
        assert len(result) == 1
        # 72カラム以降の内容は含まれない
        assert "EXTRA_BEYOND_72" not in result[0].content

    def test_コメント行_アスタリスク(self):
        """インジケータが*の行はコメントとして除外される"""
        raw = ["000100*これはコメントです                                                \n"]
        result = _normalize_raw_lines(raw)
        assert len(result) == 0

    def test_コメント行_スラッシュ(self):
        """インジケータが/の行はコメントとして除外される"""
        raw = ["000100/ページ送りコメント                                               \n"]
        result = _normalize_raw_lines(raw)
        assert len(result) == 0

    def test_コメント行_D(self):
        """インジケータがDの行はデバッグ行として除外される"""
        raw = ["000100DDEBUG LINE                                                       \n"]
        result = _normalize_raw_lines(raw)
        assert len(result) == 0

    def test_コメント行_d小文字(self):
        """インジケータがdの行もデバッグ行として除外される"""
        raw = ["000100ddebug line                                                       \n"]
        result = _normalize_raw_lines(raw)
        assert len(result) == 0

    def test_7カラム未満の行はスキップ(self):
        """7カラム未満の短い行はスキップされる"""
        raw = ["SHORT\n", "AB\n", "\n"]
        result = _normalize_raw_lines(raw)
        assert len(result) == 0

    def test_空のリスト(self):
        """空のリストを渡した場合は空のリストが返る"""
        result = _normalize_raw_lines([])
        assert result == []

    def test_継続行の結合(self):
        """インジケータが-の行は直前の行と結合される"""
        raw = [
            "000100 MOVE LONG-VARIABLE-NAME                                          \n",
            "000200-    TO TARGET-VAR.                                                \n",
        ]
        result = _normalize_raw_lines(raw)
        assert len(result) == 1
        assert result[0].line_number == 1  # 開始行の行番号を保持
        assert result[0].is_continuation is True
        assert "LONG-VARIABLE-NAME" in result[0].content
        assert "TO TARGET-VAR." in result[0].content

    def test_継続行が先頭にある場合(self):
        """直前の行がない状態で継続行が来た場合はそのまま追加"""
        raw = ["000100-    ORPHAN CONTINUATION                                        \n"]
        result = _normalize_raw_lines(raw)
        assert len(result) == 1
        assert result[0].is_continuation is False

    def test_複数の継続行(self):
        """複数の継続行が連続する場合も正しく結合される"""
        raw = [
            "000100 MOVE VERY-LONG                                                   \n",
            "000200-    -VARIABLE-NAME                                                \n",
            "000300-    TO TARGET.                                                    \n",
        ]
        result = _normalize_raw_lines(raw)
        assert len(result) == 1
        assert result[0].line_number == 1  # 最初の行番号を保持
        assert result[0].is_continuation is True

    def test_行番号の保持(self):
        """各行の行番号が正しく保持される"""
        raw = [
            "000100 FIRST LINE.                                                      \n",
            "000200*コメント行                                                        \n",
            "000300 THIRD LINE.                                                      \n",
        ]
        result = _normalize_raw_lines(raw)
        assert len(result) == 2
        assert result[0].line_number == 1
        assert result[1].line_number == 3  # コメント行をスキップしても行番号は元のまま

    def test_混合パターン(self):
        """通常行、コメント行、継続行が混在するケース"""
        raw = [
            "000100 IDENTIFICATION DIVISION.                                         \n",
            "000200*コメント                                                          \n",
            "000300 PROGRAM-ID. TEST-PROG                                            \n",
            "000400-    RAM.                                                          \n",
            "000500/ページ送り                                                        \n",
            "000600 DATA DIVISION.                                                    \n",
        ]
        result = _normalize_raw_lines(raw)
        assert len(result) == 3
        # 1行目: IDENTIFICATION DIVISION.
        assert result[0].line_number == 1
        assert result[0].is_continuation is False
        # 2行目: PROGRAM-ID. TEST-PROGRAM. (継続行結合)
        assert result[1].line_number == 3
        assert result[1].is_continuation is True
        # 3行目: DATA DIVISION.
        assert result[2].line_number == 6
        assert result[2].is_continuation is False


class TestNormalizeLines:
    """normalize_lines関数のテスト（ファイル読み込み含む）"""

    def test_cp932ファイルの読み込み(self):
        """cp932エンコーディングのファイルを正しく読み込める"""
        content = "000100 全角文字テスト。                                                  \n"
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="cp932", suffix=".cbl", delete=False
        ) as f:
            f.write(content)
            tmp_path = f.name

        try:
            result = normalize_lines(tmp_path, encoding="cp932")
            assert len(result) == 1
            assert "全角文字テスト。" in result[0].content
        finally:
            os.unlink(tmp_path)

    def test_cp932で全角カナと漢字(self):
        """cp932エンコーディングで全角カナ・漢字が文字化けしない"""
        content = "000100 顧客名カナＡＢＣ。                                                \n"
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="cp932", suffix=".cbl", delete=False
        ) as f:
            f.write(content)
            tmp_path = f.name

        try:
            result = normalize_lines(tmp_path, encoding="cp932")
            assert len(result) == 1
            assert "顧客名カナＡＢＣ。" in result[0].content
        finally:
            os.unlink(tmp_path)

    def test_空ファイル(self):
        """空ファイルの場合は空リストが返る"""
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="cp932", suffix=".cbl", delete=False
        ) as f:
            tmp_path = f.name

        try:
            result = normalize_lines(tmp_path, encoding="cp932")
            assert result == []
        finally:
            os.unlink(tmp_path)
