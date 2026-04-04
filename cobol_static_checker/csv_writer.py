"""CSV出力モジュール

警告リストをCSVファイルとしてUTF-8（BOM付き: utf-8-sig）エンコーディングで出力する。
複数ファイルの結果を1つのCSVに集約し、警告0件時はヘッダー行のみ出力する。
"""

import csv

from cobol_static_checker import Warning

# CSVヘッダー定義
CSV_HEADER = ["ファイル名", "行番号", "変数名", "警告種別", "メッセージ"]


def write_csv(
    warnings: list[Warning], output_path: str, encoding: str = "utf-8-sig"
) -> None:
    """警告リストをCSVファイルに出力する。

    Args:
        warnings: 出力対象の警告リスト
        output_path: 出力先CSVファイルパス
        encoding: 出力エンコーディング（デフォルト: cp932）
    """
    with open(output_path, "w", newline="", encoding=encoding) as f:
        writer = csv.writer(f)
        # ヘッダー行を出力
        writer.writerow(CSV_HEADER)
        # 各警告をデータ行として出力
        for w in warnings:
            writer.writerow([
                w.file_name,
                w.line_number,
                w.variable_name,
                w.warning_type,
                w.message,
            ])
