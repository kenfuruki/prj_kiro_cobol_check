"""CLIエントリポイント

argparseによるコマンドライン引数処理と、
パイプライン全体の結合（正規化 → 変数定義パース → 文解析 → チェック → CSV出力）を行う。

- 入力ディレクトリ、プレフィックスフィルタ、出力CSVパスの指定
- デフォルト値: 入力ディレクトリはスクリプトと同階層の cobol_src_Psan、出力CSVは check_result.csv
- 対象ファイル拡張子: *.cbl, *.cob, *.CBL, *.COB
- ファイルプレフィックスフィルタリング（大文字小文字不問、カンマ区切り複数指定可）
- 存在しないディレクトリ指定時のエラーハンドリング（終了コード1）
- ファイル読み込みエラー時のスキップ処理
"""

import argparse
import os
import sys
from pathlib import Path

from cobol_static_checker import Warning
from cobol_static_checker.checker import check
from cobol_static_checker.csv_writer import write_csv
from cobol_static_checker.normalizer import normalize_lines
from cobol_static_checker.statement_analyzer import analyze_statements
from cobol_static_checker.variable_parser import parse_variables

# 対象ファイル拡張子
COBOL_EXTENSIONS = {".cbl", ".cob"}


def build_parser() -> argparse.ArgumentParser:
    """argparseパーサーを構築する。

    Returns:
        設定済みのArgumentParser
    """
    # デフォルトの入力ディレクトリ: スクリプトと同階層の cobol_src_Psan
    default_input_dir = str(
        Path(__file__).resolve().parent / "cobol_src_Psan"
    )

    parser = argparse.ArgumentParser(
        description="COBOL静的チェッカー: VALUE値上書きと未初期化変数参照を検出する",
    )
    parser.add_argument(
        "input_dir",
        nargs="?",
        default=default_input_dir,
        help="チェック対象のCOBOLソースディレクトリ（デフォルト: cobol_src_Psan）",
    )
    parser.add_argument(
        "-p", "--prefix",
        default=None,
        help="ファイル名プレフィックスフィルタ（カンマ区切りで複数指定可、大文字小文字不問）",
    )
    parser.add_argument(
        "-o", "--output",
        default="check_result.csv",
        help="出力CSVファイルパス（デフォルト: check_result.csv）",
    )
    return parser


def collect_cobol_files(
    input_dir: str, prefixes: list[str] | None = None,
) -> list[Path]:
    """指定ディレクトリからCOBOLファイルを収集する。

    Args:
        input_dir: 入力ディレクトリパス
        prefixes: ファイル名プレフィックスフィルタ（大文字小文字不問）

    Returns:
        対象ファイルパスのリスト（ソート済み）
    """
    dir_path = Path(input_dir)
    files: list[Path] = []

    for f in sorted(dir_path.iterdir()):
        if not f.is_file():
            continue
        # 拡張子チェック（大文字小文字不問）
        if f.suffix.lower() not in COBOL_EXTENSIONS:
            continue
        # プレフィックスフィルタ
        if prefixes:
            name_lower = f.name.lower()
            if not any(name_lower.startswith(p.lower()) for p in prefixes):
                continue
        files.append(f)

    return files


def run_pipeline(
    files: list[Path],
) -> list[Warning]:
    """全ファイルに対してチェックパイプラインを実行する。

    各ファイルに対して:
    1. normalize_lines で正規化
    2. parse_variables で変数定義解析
    3. analyze_statements で文解析
    4. check でチェック

    ファイル読み込みエラー時はスキップして処理を継続する。

    Args:
        files: チェック対象ファイルパスのリスト

    Returns:
        全ファイルの警告を集約したリスト
    """
    all_warnings: list[Warning] = []

    for file_path in files:
        try:
            # 1. 正規化
            normalized = normalize_lines(str(file_path))
            # 2. 変数定義解析
            variables = parse_variables(normalized)
            # 3. 文解析
            statements = analyze_statements(normalized)
            # 4. チェック
            warnings = check(variables, statements, file_path.name)
            all_warnings.extend(warnings)
        except Exception as e:
            # ファイル読み込みエラー時はスキップ
            print(f"警告: {file_path.name} の処理中にエラーが発生しました: {e}",
                  file=sys.stderr)
            continue

    return all_warnings


def main(args: list[str] | None = None) -> None:
    """CLIメインエントリポイント。

    Args:
        args: コマンドライン引数（テスト用にオーバーライド可能）
    """
    parser = build_parser()
    parsed = parser.parse_args(args)

    input_dir = parsed.input_dir
    output_path = parsed.output
    prefixes: list[str] | None = None
    if parsed.prefix:
        prefixes = [p.strip() for p in parsed.prefix.split(",") if p.strip()]

    # 入力ディレクトリの存在チェック
    if not os.path.isdir(input_dir):
        print(f"エラー: 入力ディレクトリが存在しません: {input_dir}",
              file=sys.stderr)
        sys.exit(1)

    # COBOLファイルの収集
    files = collect_cobol_files(input_dir, prefixes)

    # パイプライン実行
    all_warnings = run_pipeline(files)

    # CSV出力
    try:
        write_csv(all_warnings, output_path)
    except Exception as e:
        print(f"エラー: CSV出力に失敗しました: {e}", file=sys.stderr)
        sys.exit(1)

    # 完了メッセージ
    print(f"チェック完了: {len(files)}ファイル, {len(all_warnings)}件の警告")
    print(f"出力先: {output_path}")


if __name__ == "__main__":
    main()
