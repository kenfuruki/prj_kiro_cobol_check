"""GUIエントリポイント

tkinterファイル選択ダイアログによるGUI。
EXEバイナリ用エントリポイント。

処理:
1. tkinter.filedialog.askopenfilenames() で複数ファイル選択ダイアログを表示
2. ファイルフィルタ: COBOLファイル (*.cbl, *.cob)
3. 選択された全ファイルに対してチェックパイプラインを実行（cli.pyのrun_pipelineを再利用）
4. 全ファイルの結果を1つのCSVに集約
5. CSV出力先: EXE実行時はsys.executableの親ディレクトリ、Python実行時はカレントディレクトリ
"""

import os
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

from cobol_static_checker.cli import run_pipeline
from cobol_static_checker.csv_writer import write_csv

# CSV出力ファイル名
OUTPUT_CSV_NAME = "check_result.csv"


def get_output_dir() -> Path:
    """CSV出力先ディレクトリを取得する。

    EXE実行時（PyInstallerでビルドされた場合）はsys.executableの親ディレクトリ、
    通常のPython実行時はカレントディレクトリを返す。

    Returns:
        出力先ディレクトリのPath
    """
    if getattr(sys, "frozen", False):
        # EXE実行時: sys.executableの親ディレクトリ
        return Path(sys.executable).parent
    else:
        # 通常のPython実行時: カレントディレクトリ
        return Path(os.getcwd())


def main() -> None:
    """GUIメインエントリポイント。

    ファイル選択ダイアログを表示し、選択されたCOBOLファイルに対して
    チェックパイプラインを実行、結果をCSVに出力する。
    """
    # tkinterルートウィンドウを非表示で作成
    root = tk.Tk()
    root.withdraw()

    # ファイル選択ダイアログを表示
    selected_files = filedialog.askopenfilenames(
        title="チェック対象のCOBOLファイルを選択してください",
        filetypes=[
            ("COBOLファイル", "*.cbl *.cob"),
            ("すべてのファイル", "*.*"),
        ],
    )

    # キャンセルまたは未選択の場合
    if not selected_files:
        messagebox.showinfo("COBOL静的チェッカー", "ファイルが選択されませんでした。")
        root.destroy()
        return

    # 選択ファイルをPathオブジェクトに変換
    file_paths = [Path(f) for f in selected_files]

    # チェックパイプラインを実行（cli.pyのrun_pipelineを再利用）
    all_warnings = run_pipeline(file_paths)

    # CSV出力先を決定
    output_dir = get_output_dir()
    output_path = str(output_dir / OUTPUT_CSV_NAME)

    # CSV出力
    try:
        write_csv(all_warnings, output_path)
    except Exception as e:
        messagebox.showerror(
            "COBOL静的チェッカー",
            f"CSV出力に失敗しました:\n{e}",
        )
        root.destroy()
        return

    # 完了メッセージを表示
    messagebox.showinfo(
        "COBOL静的チェッカー",
        f"チェック完了\n\n"
        f"対象ファイル数: {len(file_paths)}\n"
        f"検出された警告: {len(all_warnings)}件\n"
        f"出力先: {output_path}",
    )

    root.destroy()


if __name__ == "__main__":
    main()
