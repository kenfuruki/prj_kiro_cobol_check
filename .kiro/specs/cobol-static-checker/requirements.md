# 要件定義書

## はじめに

本ドキュメントは、COBOLソースコードの静的チェックを行うPythonスクリプトの作成、AWS Kiro用Skills定義の整備、およびEXE化による非Kiro環境への展開を目的とした「COBOL静的チェッカー」機能の要件を定義する。

本機能は以下の3つの成果物で構成される:
1. COBOLの静的チェックを行うPythonスクリプト
2. AWS Kiro用のSkills定義（スクリプトを活用したAIレビュー連携）
3. PythonスクリプトのEXE化（Kiro未導入環境向けの過渡期対応）

## 用語集

- **チェッカー (Checker)**: COBOLソースコードを解析し、コーディング規約違反や潜在的な問題を検出するPythonスクリプト
- **正規化エンジン (Normalizer)**: COBOL固定形式ソースの72カラム制限、継続行結合、コメント行除外を行う前処理モジュール
- **変数定義パーサー (Variable_Parser)**: WORKING-STORAGE SECTIONの変数定義（レベル番号、変数名、VALUE句、グループ項目、COPY句）を解析するモジュール
- **文解析エンジン (Statement_Analyzer)**: PROCEDURE DIVISIONの各文（MOVE, COMPUTE, 算術文, INITIALIZE, ACCEPT, READ INTO, STRING/UNSTRING, DISPLAY, CALL USING等）を解析するモジュール
- **Override警告**: VALUE句で初期値が設定された変数がPROCEDURE DIVISIONで上書きされている場合に発行される警告
- **Uninitialized警告**: VALUE句もPROCEDURE DIVISION内での値設定もない変数が参照された場合に発行される警告
- **Skills定義 (Skills)**: AWS Kiroにおいて、AIアシスタントの振る舞いや手順を定義するMarkdownファイル
- **トリアージ**: Skills定義内でAIが静的チェック結果を精査し、真の問題と過剰検知に分類する工程
- **EXEバイナリ (EXE_Binary)**: PyInstallerを用いてPythonスクリプトを単一実行ファイルに変換した成果物

## 要件

### 要件1: COBOL行の正規化処理

**ユーザーストーリー:** 開発者として、COBOL固定形式ソースを正しく前処理したい。これにより後続の解析処理が正確に動作する。

#### 受け入れ基準

1. WHEN COBOLソースファイルが入力された場合、THE 正規化エンジン SHALL 各行を72カラムで切り詰めた上で7カラム目以降の内容を抽出する
2. WHEN 7カラム目のインジケータが「*」「/」「D」「d」のいずれかである場合、THE 正規化エンジン SHALL 該当行をコメント行として除外する
3. WHEN 7カラム目のインジケータが「-」（継続行）である場合、THE 正規化エンジン SHALL 直前の行と結合して1つの論理行として返却する
4. THE 正規化エンジン SHALL 各論理行に対して元ソースの行番号を保持する
5. WHEN ソースファイルのエンコーディングがcp932である場合、THE 正規化エンジン SHALL 文字化けなく正しく読み込む

### 要件2: WORKING-STORAGE SECTION の変数定義解析

**ユーザーストーリー:** 開発者として、WORKING-STORAGE SECTIONの変数定義を正確に解析したい。これにより変数の初期化状態を把握できる。

#### 受け入れ基準

1. WHEN WORKING-STORAGE SECTIONが検出された場合、THE 変数定義パーサー SHALL レベル番号、変数名、VALUE句の有無、グループ項目の判定、COPY句の有無を解析する
2. WHEN 変数定義にVALUE句が含まれる場合、THE 変数定義パーサー SHALL 該当変数を「初期値あり」として記録する
3. WHEN レベル番号が01または集団項目である場合、THE 変数定義パーサー SHALL 該当変数を「グループ項目」として識別する
4. WHEN COPY句が検出された場合、THE 変数定義パーサー SHALL 該当変数を「COPY句あり」として記録する
5. THE 変数定義パーサー SHALL 各変数の親子関係（グループ項目と従属項目の関係）を正しく構築する
6. THE 変数定義パーサー SHALL 全角文字を含むCOBOL識別子（ひらがな、カタカナ、漢字、全角英数）を正しく認識する

### 要件3: PROCEDURE DIVISION の文解析

**ユーザーストーリー:** 開発者として、PROCEDURE DIVISIONの各文を解析し、変数の代入・参照関係を把握したい。これにより静的チェックの判定が可能になる。

#### 受け入れ基準

1. WHEN MOVE文が検出された場合、THE 文解析エンジン SHALL 送り先変数を「代入あり」として記録し、送り元変数を「参照あり」として記録する
2. WHEN COMPUTE文または算術文（ADD, SUBTRACT, MULTIPLY, DIVIDE）が検出された場合、THE 文解析エンジン SHALL 結果格納変数を「代入あり」として記録する
3. WHEN INITIALIZE文が検出された場合、THE 文解析エンジン SHALL 対象変数を「初期化済み」として記録する
4. WHEN ACCEPT文が検出された場合、THE 文解析エンジン SHALL 対象変数を「代入あり」として記録する
5. WHEN READ INTO文が検出された場合、THE 文解析エンジン SHALL INTO句の対象変数を「代入あり」として記録する
6. WHEN STRING文またはUNSTRING文が検出された場合、THE 文解析エンジン SHALL INTO句の対象変数を「代入あり」として記録する
7. WHEN DISPLAY文が検出された場合、THE 文解析エンジン SHALL 対象変数を「参照あり」として記録する
8. WHEN CALL USING文が検出された場合、THE 文解析エンジン SHALL USING句の変数を「参照あり」として記録する

### 要件4: VALUE値上書きチェック（Override警告）

**ユーザーストーリー:** 開発者として、VALUE句で初期値設定された変数が不必要に上書きされている箇所を検出したい。これにより意図しない値の変更を防止できる。

#### 受け入れ基準

1. WHEN VALUE句で初期値が設定された変数がPROCEDURE DIVISIONで代入対象となっている場合、THE チェッカー SHALL Override警告を発行する
2. THE チェッカー SHALL Override警告にファイル名、行番号、変数名、警告種別「Override」、および警告メッセージを含める
3. WHEN FILLER項目またはレベル番号88の条件名が検出された場合、THE チェッカー SHALL Override警告の対象から除外する

### 要件5: 未初期化変数参照チェック（Uninitialized警告）

**ユーザーストーリー:** 開発者として、初期化されていない変数が参照されている箇所を検出したい。これにより未定義値の使用によるバグを防止できる。

#### 受け入れ基準

1. WHEN VALUE句もPROCEDURE DIVISION内での代入もない変数がPROCEDURE DIVISIONで参照された場合、THE チェッカー SHALL Uninitialized警告を発行する
2. THE チェッカー SHALL Uninitialized警告にファイル名、行番号、変数名、警告種別「Uninitialized」、および警告メッセージを含める
3. WHEN グループ項目の従属項目にVALUE句がある場合、THE チェッカー SHALL 該当従属項目をUninitialized警告の対象から除外する
4. WHEN COPY句を含む変数が検出された場合、THE チェッカー SHALL 該当変数をUninitialized警告の対象から除外する

### 要件6: CSV結果出力

**ユーザーストーリー:** 開発者として、チェック結果をCSV形式で出力したい。これにより結果の確認や他ツールとの連携が容易になる。

#### 受け入れ基準

1. THE チェッカー SHALL チェック結果をCSVファイルとして出力する
2. THE チェッカー SHALL CSVファイルにヘッダー行（ファイル名、行番号、変数名、警告種別、メッセージ）を含める
3. WHEN チェック対象ファイルが複数存在する場合、THE チェッカー SHALL すべてのファイルの結果を1つのCSVファイルに集約する
4. THE チェッカー SHALL CSV出力時にUTF-8（BOM付き: utf-8-sig）エンコーディングで書き出す

### 要件7: コマンドライン引数とファイルフィルタリング

**ユーザーストーリー:** 開発者として、チェック対象のディレクトリやファイルをコマンドライン引数で指定したい。これにより柔軟な運用が可能になる。

#### 受け入れ基準

1. THE チェッカー SHALL コマンドライン引数で入力ディレクトリパスを受け付ける
2. THE チェッカー SHALL コマンドライン引数で出力CSVファイルパスを受け付ける
3. WHEN ファイルプレフィックスフィルタが指定された場合、THE チェッカー SHALL 指定プレフィックスに一致するファイルのみをチェック対象とする
4. WHEN 引数が省略された場合、THE チェッカー SHALL デフォルトの入力ディレクトリおよび出力CSVパスを使用する
5. IF 指定された入力ディレクトリが存在しない場合、THEN THE チェッカー SHALL エラーメッセージを表示して終了する

### 要件8: AWS Kiro Skills定義

**ユーザーストーリー:** 開発者として、Kiro上で「静的チェックして」と指示するだけでCOBOL静的チェックとAIによる結果精査を実行したい。これにより手動でのスクリプト実行とレビューの手間を削減できる。

#### 受け入れ基準

1. THE Skills定義 SHALL Markdownファイルとして `.kiro/skills/` ディレクトリに配置される
2. THE Skills定義 SHALL フロントマターのdescriptionフィールドに、起動トリガーとなるキーワード（「静的チェック」「バグ確認」等）を含める
3. WHEN Skills定義が実行された場合、THE Skills定義 SHALL チェッカーをPythonスクリプトとして実行する手順を含める
4. WHEN チェッカーの実行結果が得られた場合、THE Skills定義 SHALL AIに対して結果のトリアージ（真の問題と過剰検知の分類）を指示する
5. THE Skills定義 SHALL トリアージ結果を「修正を推奨する項目」と「確認事項（過剰検知の可能性）」の2カテゴリで報告する形式を定義する
6. THE Skills定義 SHALL 報告後にユーザーへ最終判断を仰ぐ手順を含める

### 要件9: EXEバイナリの生成（過渡期対応）

**ユーザーストーリー:** 開発者として、Kiro未導入のWindows環境でもCOBOL静的チェックを実行したい。これによりPython環境がない端末でもGUIからファイルを選択してチェックが可能になる。

#### 受け入れ基準

1. THE EXEバイナリ SHALL PyInstallerを使用してPythonスクリプトから単一実行ファイルとして生成される
2. THE EXEバイナリ SHALL Python実行環境がインストールされていないWindows端末で動作する
3. WHEN EXEバイナリが実行された場合、THE EXEバイナリ SHALL Windowsのファイル選択ダイアログを表示し、ユーザーがチェック対象のCOBOLファイルを1つまたは複数指定できる
4. THE EXEバイナリ SHALL ファイル選択ダイアログでCOBOLファイル（*.cbl, *.cob）をフィルタ表示する
5. WHEN 複数のCOBOLファイルが選択された場合、THE EXEバイナリ SHALL すべての選択ファイルのチェック結果を1つのCSVファイルに集約して出力する
6. THE EXEバイナリ SHALL チェック結果のCSVファイルをEXEファイルの実行ディレクトリと同じ場所に出力する
7. THE EXEバイナリ SHALL Pythonスクリプト版と同一のチェック結果を出力する
7. THE EXEバイナリ SHALL ビルド手順をドキュメントとして提供する
8. WHEN Windows環境でEXEバイナリが実行された場合、THE EXEバイナリ SHALL cp932エンコーディングのCOBOLソースを正しく処理する

### 要件10: 正規化処理の整合性検証（ラウンドトリップ）

**ユーザーストーリー:** 開発者として、正規化処理が元のCOBOLソースの意味を損なわないことを検証したい。これにより解析結果の信頼性を担保できる。

#### 受け入れ基準

1. FOR ALL 有効なCOBOL固定形式ソース行について、THE 正規化エンジン SHALL コメント行と空行を除いたすべての実行行の内容を保持する
2. FOR ALL 継続行を含むCOBOL論理行について、THE 正規化エンジン SHALL 結合後の論理行が元の分割前の内容と等価である
3. FOR ALL 正規化された論理行について、THE 正規化エンジン SHALL 元ソースの行番号との対応関係を正しく維持する
