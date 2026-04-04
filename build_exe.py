"""PyInstallerビルドスクリプト

cobol_static_checker/gui.py をエントリポイントとして、
単一EXEファイル（cobol_checker.exe）をビルドする。

使用方法:
    python build_exe.py

ビルドオプション:
    --onefile: 単一EXEファイルとして出力
    --noconsole: コンソールウィンドウを非表示
"""

import PyInstaller.__main__

# PyInstallerビルド実行
PyInstaller.__main__.run([
    "cobol_static_checker/gui.py",  # エントリポイント
    "--onefile",                     # 単一EXEファイル
    "--noconsole",                   # コンソールウィンドウ非表示
    "--name=cobol_checker",          # 出力ファイル名
])
