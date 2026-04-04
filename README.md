# COBOL静的チェッカー

COBOLソースコードの静的解析を行い、以下の2種類の警告を検出するツールです。

- **Override警告**: VALUE句で初期値が設定された変数がPROCEDURE DIVISIONで上書きされている
- **Uninitialized警告**: VALUE句も代入もない変数がPROCEDURE DIVISIONで参照されている

## 使い方

### EXE版（Python不要）

`dist/cobol_checker.exe` をダブルクリックすると、ファイル選択ダイアログが開きます。
チェック対象のCOBOLファイル（*.cbl, *.cob）を1つまたは複数選択してください。
結果はEXEと同じフォルダに `check_result.csv` として出力されます。

### CLI版（Python環境あり）

```bash
# 仮想環境のセットアップ
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt

# 実行
.venv/Scripts/python -m cobol_static_checker.cli [対象ディレクトリ]

# プレフィックスフィルタ付き
.venv/Scripts/python -m cobol_static_checker.cli [対象ディレクトリ] -p QB71,QB72

# 出力先指定
.venv/Scripts/python -m cobol_static_checker.cli [対象ディレクトリ] -o result.csv
```

### Kiro Skills連携

Kiro上で「静的チェックして」と指示すると、チェッカーの実行とAIによる結果精査が自動で行われます。

## Kiroプロジェクトへの導入方法

COBOLの開発プロジェクトにこのツールを組み込む場合、以下のようにファイルを配置してください。

```
your-cobol-project/                  ← COBOLプロジェクトのルート
├── .kiro/
│   ├── skills/
│   │   └── cobol-check.md           ← ① Skills定義（本リポジトリからコピー）
│   └── steering/
│       └── (プロジェクト固有のルール)
├── tools/
│   └── cobol_static_checker/        ← ② チェッカー本体（本リポジトリからコピー）
│       ├── __init__.py
│       ├── normalizer.py
│       ├── variable_parser.py
│       ├── statement_analyzer.py
│       ├── checker.py
│       ├── csv_writer.py
│       ├── cli.py
│       └── gui.py
├── cobol_src/                        ← COBOLソースコード
│   ├── PGM001.cbl
│   ├── PGM002.cbl
│   └── ...
└── dist/
    └── cobol_checker.exe             ← ③ EXE版（Kiro未導入の端末向け）
```

### 配置手順

1. `.kiro/skills/cobol-check.md` を配置し、コマンドパスをプロジェクトに合わせて修正する
   - 例: `python tools/cobol_static_checker/cli.py [対象ディレクトリ]`
2. `tools/cobol_static_checker/` にチェッカー本体を配置する
3. EXE版が必要な場合は `dist/cobol_checker.exe` を配置する（Python不要の端末向け）

### Skills定義のコマンドパス修正例

`tools/` 配下に配置した場合、Skills定義内のコマンドを以下のように変更してください:

```bash
# tools/ 配下に配置した場合
python -m tools.cobol_static_checker.cli cobol_src -o check_result.csv

# または PYTHONPATH を指定して実行
PYTHONPATH=tools python -m cobol_static_checker.cli cobol_src -o check_result.csv
```

## 対応するCOBOL文

- MOVE, COMPUTE, ADD, SUBTRACT, MULTIPLY, DIVIDE
- INITIALIZE, ACCEPT, READ INTO
- STRING INTO, UNSTRING INTO
- DISPLAY, CALL USING, PERFORM VARYING
- IF, EVALUATE WHEN, UNTIL（条件参照）

## 入力ファイル

- エンコーディング: cp932（Shift_JIS）
- 形式: COBOL固定形式（72カラム）
- 拡張子: *.cbl, *.cob

## 出力ファイル

- エンコーディング: UTF-8（BOM付き）
- 形式: CSV（ファイル名, 行番号, 変数名, 警告種別, メッセージ）

## EXEのビルド方法

```bash
.venv/Scripts/pip install pyinstaller
.venv/Scripts/python build_exe.py
```

`dist/cobol_checker.exe` が生成されます。

## テスト

```bash
.venv/Scripts/python -m pytest tests/ -v
```
