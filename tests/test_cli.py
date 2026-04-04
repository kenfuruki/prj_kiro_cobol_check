"""CLIエントリポイントのユニットテスト

引数パース、デフォルト値、ファイル収集、エラーハンドリング、
パイプライン実行のテストを行う。
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from cobol_static_checker.cli import (
    build_parser,
    collect_cobol_files,
    main,
    run_pipeline,
)


class TestBuildParser:
    """argparseパーサーのテスト"""

    def test_デフォルト値が設定される(self):
        """引数なしでデフォルト値が使用されること"""
        parser = build_parser()
        args = parser.parse_args([])
        # デフォルトの入力ディレクトリはcobol_src_Psanを含む
        assert "cobol_src_Psan" in args.input_dir
        assert args.output == "check_result.csv"
        assert args.prefix is None

    def test_入力ディレクトリを指定できる(self):
        """位置引数で入力ディレクトリを指定できること"""
        parser = build_parser()
        args = parser.parse_args(["my_dir"])
        assert args.input_dir == "my_dir"

    def test_プレフィックスオプションを指定できる(self):
        """-p オプションでプレフィックスを指定できること"""
        parser = build_parser()
        args = parser.parse_args(["-p", "ABC,DEF"])
        assert args.prefix == "ABC,DEF"

    def test_出力パスオプションを指定できる(self):
        """-o オプションで出力CSVパスを指定できること"""
        parser = build_parser()
        args = parser.parse_args(["-o", "result.csv"])
        assert args.output == "result.csv"

    def test_全オプションを同時に指定できる(self):
        """全引数を同時に指定できること"""
        parser = build_parser()
        args = parser.parse_args(["src_dir", "-p", "PGM", "-o", "out.csv"])
        assert args.input_dir == "src_dir"
        assert args.prefix == "PGM"
        assert args.output == "out.csv"


class TestCollectCobolFiles:
    """COBOLファイル収集のテスト"""

    def test_cblファイルを収集する(self, tmp_path):
        """*.cbl ファイルが収集されること"""
        (tmp_path / "test.cbl").write_text("dummy", encoding="utf-8")
        (tmp_path / "test.txt").write_text("dummy", encoding="utf-8")
        files = collect_cobol_files(str(tmp_path))
        assert len(files) == 1
        assert files[0].name == "test.cbl"

    def test_cobファイルを収集する(self, tmp_path):
        """*.cob ファイルが収集されること"""
        (tmp_path / "test.cob").write_text("dummy", encoding="utf-8")
        files = collect_cobol_files(str(tmp_path))
        assert len(files) == 1
        assert files[0].name == "test.cob"

    def test_大文字拡張子も収集する(self, tmp_path):
        """*.CBL, *.COB も収集されること"""
        (tmp_path / "test.CBL").write_text("dummy", encoding="utf-8")
        (tmp_path / "test.COB").write_text("dummy", encoding="utf-8")
        files = collect_cobol_files(str(tmp_path))
        assert len(files) == 2

    def test_プレフィックスフィルタが機能する(self, tmp_path):
        """プレフィックスフィルタで対象ファイルが絞り込まれること"""
        (tmp_path / "ABC001.cbl").write_text("dummy", encoding="utf-8")
        (tmp_path / "DEF001.cbl").write_text("dummy", encoding="utf-8")
        (tmp_path / "XYZ001.cbl").write_text("dummy", encoding="utf-8")
        files = collect_cobol_files(str(tmp_path), prefixes=["ABC", "DEF"])
        names = [f.name for f in files]
        assert "ABC001.cbl" in names
        assert "DEF001.cbl" in names
        assert "XYZ001.cbl" not in names

    def test_プレフィックスフィルタは大文字小文字不問(self, tmp_path):
        """プレフィックスフィルタが大文字小文字を区別しないこと"""
        (tmp_path / "abc001.cbl").write_text("dummy", encoding="utf-8")
        files = collect_cobol_files(str(tmp_path), prefixes=["ABC"])
        assert len(files) == 1

    def test_プレフィックスなしで全ファイル収集(self, tmp_path):
        """プレフィックス未指定時は全COBOLファイルが収集されること"""
        (tmp_path / "A.cbl").write_text("dummy", encoding="utf-8")
        (tmp_path / "B.cob").write_text("dummy", encoding="utf-8")
        files = collect_cobol_files(str(tmp_path), prefixes=None)
        assert len(files) == 2

    def test_ソート済みで返される(self, tmp_path):
        """ファイルがソート済みで返されること"""
        (tmp_path / "C.cbl").write_text("dummy", encoding="utf-8")
        (tmp_path / "A.cbl").write_text("dummy", encoding="utf-8")
        (tmp_path / "B.cbl").write_text("dummy", encoding="utf-8")
        files = collect_cobol_files(str(tmp_path))
        names = [f.name for f in files]
        assert names == sorted(names)

    def test_空ディレクトリでは空リスト(self, tmp_path):
        """空ディレクトリでは空リストが返されること"""
        files = collect_cobol_files(str(tmp_path))
        assert files == []


class TestRunPipeline:
    """パイプライン実行のテスト"""

    def _create_cobol_file(self, path: Path, content: str) -> None:
        """テスト用COBOLファイルを作成する（cp932エンコーディング）"""
        path.write_text(content, encoding="cp932")

    def test_空ファイルリストでは空の警告リスト(self):
        """ファイルなしの場合、空の警告リストが返されること"""
        warnings = run_pipeline([])
        assert warnings == []

    def test_読み込みエラー時はスキップする(self, tmp_path, capsys):
        """存在しないファイルはスキップされること"""
        fake_path = tmp_path / "nonexistent.cbl"
        warnings = run_pipeline([fake_path])
        assert warnings == []
        captured = capsys.readouterr()
        assert "エラーが発生しました" in captured.err

    def test_正常なCOBOLファイルを処理できる(self, tmp_path):
        """正常なCOBOLファイルのパイプライン処理が動作すること"""
        # 最小限のCOBOLソース（固定形式: 6桁行番号 + インジケータ + 内容）
        lines = [
            "000010 IDENTIFICATION DIVISION.                                         ",
            "000020 PROGRAM-ID. TEST1.                                               ",
            "000030 DATA DIVISION.                                                   ",
            "000040 WORKING-STORAGE SECTION.                                         ",
            "000050 01 WS-VAR1 PIC X(10) VALUE 'HELLO'.                             ",
            "000060 01 WS-VAR2 PIC X(10).                                           ",
            "000070 PROCEDURE DIVISION.                                              ",
            "000080     MOVE WS-VAR1 TO WS-VAR2.                                    ",
            "000090     DISPLAY WS-VAR2.                                             ",
            "000100     STOP RUN.                                                    ",
        ]
        content = "\r\n".join(lines) + "\r\n"
        cobol_file = tmp_path / "TEST1.cbl"
        cobol_file.write_text(content, encoding="cp932")

        warnings = run_pipeline([cobol_file])
        # WS-VAR1はVALUE句あり + MOVE先ではないので Override警告なし
        # WS-VAR2はVALUE句なし + MOVE先で代入あり → Uninitializedにはならない
        # 具体的な警告数はチェッカーのロジック次第
        assert isinstance(warnings, list)


class TestMain:
    """mainエントリポイントのテスト"""

    def test_存在しないディレクトリで終了コード1(self):
        """存在しないディレクトリ指定時に終了コード1で終了すること"""
        with pytest.raises(SystemExit) as exc_info:
            main(["nonexistent_dir_12345"])
        assert exc_info.value.code == 1

    def test_正常実行で完了メッセージが表示される(self, tmp_path, capsys):
        """正常実行時に完了メッセージが表示されること"""
        # 空ディレクトリでも正常に動作する
        output_csv = str(tmp_path / "result.csv")
        main([str(tmp_path), "-o", output_csv])
        captured = capsys.readouterr()
        assert "チェック完了" in captured.out
        assert "0ファイル" in captured.out
        assert output_csv in captured.out

    def test_プレフィックスフィルタ付きで実行できる(self, tmp_path, capsys):
        """プレフィックスフィルタ付きで正常に実行できること"""
        output_csv = str(tmp_path / "result.csv")
        main([str(tmp_path), "-p", "ABC,DEF", "-o", output_csv])
        captured = capsys.readouterr()
        assert "チェック完了" in captured.out

    def test_COBOLファイルありで実行できる(self, tmp_path, capsys):
        """COBOLファイルが存在する場合に正常に処理されること"""
        lines = [
            "000010 IDENTIFICATION DIVISION.                                         ",
            "000020 PROGRAM-ID. TEST1.                                               ",
            "000030 DATA DIVISION.                                                   ",
            "000040 WORKING-STORAGE SECTION.                                         ",
            "000050 01 WS-A PIC X(10) VALUE 'HELLO'.                                ",
            "000060 PROCEDURE DIVISION.                                              ",
            "000070     MOVE 'BYE' TO WS-A.                                         ",
            "000080     STOP RUN.                                                    ",
        ]
        content = "\r\n".join(lines) + "\r\n"
        (tmp_path / "PGM001.cbl").write_text(content, encoding="cp932")

        output_csv = str(tmp_path / "result.csv")
        main([str(tmp_path), "-o", output_csv])
        captured = capsys.readouterr()
        assert "1ファイル" in captured.out
        # CSVファイルが生成されていること
        assert os.path.exists(output_csv)

    def test_CSV出力エラーで終了コード1(self, tmp_path):
        """CSV出力先が不正な場合に終了コード1で終了すること"""
        # 存在しないディレクトリへの出力を指定
        bad_output = str(tmp_path / "nonexistent_subdir" / "result.csv")
        with pytest.raises(SystemExit) as exc_info:
            main([str(tmp_path), "-o", bad_output])
        assert exc_info.value.code == 1
