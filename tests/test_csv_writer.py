"""CSV出力モジュールのユニットテスト

要件6.1, 6.2, 6.3, 6.4に対応するテストケースを実装する。
"""

import csv

from cobol_static_checker import Warning
from cobol_static_checker.csv_writer import CSV_HEADER, write_csv


class TestWriteCsv:
    """write_csv関数のテスト"""

    def test_empty_warnings_outputs_header_only(self, tmp_path):
        """警告0件時はヘッダー行のみ出力される（要件6.2）"""
        output = tmp_path / "result.csv"
        write_csv([], str(output))

        with open(output, encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            rows = list(reader)

        assert len(rows) == 1
        assert rows[0] == CSV_HEADER

    def test_single_warning_output(self, tmp_path):
        """単一の警告が正しくCSV出力される（要件6.1）"""
        warnings = [
            Warning(
                file_name="TEST.cbl",
                line_number=10,
                variable_name="WK-VAR",
                warning_type="Override",
                message="VALUE句で設定された値が上書きされています",
            )
        ]
        output = tmp_path / "result.csv"
        write_csv(warnings, str(output))

        with open(output, encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            rows = list(reader)

        assert len(rows) == 2
        assert rows[0] == CSV_HEADER
        assert rows[1] == [
            "TEST.cbl",
            "10",
            "WK-VAR",
            "Override",
            "VALUE句で設定された値が上書きされています",
        ]

    def test_multiple_files_aggregated(self, tmp_path):
        """複数ファイルの結果が1つのCSVに集約される（要件6.3）"""
        warnings = [
            Warning("FILE-A.cbl", 5, "VAR-A", "Override", "上書き警告"),
            Warning("FILE-B.cbl", 20, "VAR-B", "Uninitialized", "未初期化警告"),
            Warning("FILE-A.cbl", 30, "VAR-C", "Override", "上書き警告2"),
        ]
        output = tmp_path / "result.csv"
        write_csv(warnings, str(output))

        with open(output, encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            rows = list(reader)

        assert len(rows) == 4
        file_names = [row[0] for row in rows[1:]]
        assert "FILE-A.cbl" in file_names
        assert "FILE-B.cbl" in file_names

    def test_utf8_sig_encoding(self, tmp_path):
        """UTF-8 BOM付きエンコーディングで正しく出力される（要件6.4）"""
        warnings = [
            Warning("テスト.cbl", 1, "全角変数", "Override", "日本語メッセージ")
        ]
        output = tmp_path / "result.csv"
        write_csv(warnings, str(output))

        with open(output, encoding="utf-8-sig") as f:
            content = f.read()

        assert "テスト.cbl" in content
        assert "全角変数" in content
        assert "日本語メッセージ" in content

    def test_header_columns(self, tmp_path):
        """ヘッダー行が仕様通りの5カラムである（要件6.2）"""
        output = tmp_path / "result.csv"
        write_csv([], str(output))

        with open(output, encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            header = next(reader)

        assert header == ["ファイル名", "行番号", "変数名", "警告種別", "メッセージ"]

    def test_custom_encoding(self, tmp_path):
        """encoding引数でエンコーディングを変更できる"""
        warnings = [
            Warning("test.cbl", 1, "VAR1", "Override", "message")
        ]
        output = tmp_path / "result.csv"
        write_csv(warnings, str(output), encoding="utf-8")

        with open(output, encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)

        assert len(rows) == 2
        assert rows[1][0] == "test.cbl"

    def test_bom_present(self, tmp_path):
        """BOM（Byte Order Mark）が先頭に付与されている"""
        output = tmp_path / "result.csv"
        write_csv([], str(output))

        with open(output, "rb") as f:
            first_bytes = f.read(3)

        assert first_bytes == b"\xef\xbb\xbf"
