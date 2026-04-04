"""COBOL静的チェッカー パッケージ

COBOLソースコードの静的解析を行い、VALUE値上書き（Override）と
未初期化変数参照（Uninitialized）の2種類の警告を検出する。
"""

from dataclasses import dataclass, field


@dataclass
class NormalizedLine:
    """正規化済み行

    COBOLソースの1行を正規化した結果を表すデータクラス。
    継続行が結合された場合は、開始行の行番号を保持する。
    """

    line_number: int  # 元ソースの行番号（継続行の場合は開始行番号）
    content: str  # 7カラム目以降の内容（継続行結合済み）
    is_continuation: bool  # 継続行結合の結果かどうか


@dataclass
class VariableDefinition:
    """変数定義

    WORKING-STORAGE SECTIONで定義された変数の情報を保持するデータクラス。
    """

    level: int  # レベル番号（01, 02, ..., 49, 77, 88）
    name: str  # 変数名（FILLERを含む、全角文字対応）
    has_value: bool  # VALUE句の有無
    is_group: bool  # グループ項目かどうか（PIC句なし）
    has_copy: bool  # COPY句の有無
    parent_name: str | None  # 親グループ項目の変数名
    line_number: int  # 定義行番号


@dataclass
class StatementRecord:
    """文解析レコード

    PROCEDURE DIVISIONの各文を解析した結果を保持するデータクラス。
    代入対象と参照対象の変数名をそれぞれリストで管理する。
    """

    line_number: int  # 文の行番号
    statement_type: str  # 文の種別（MOVE, COMPUTE, ADD, ...）
    assigned_vars: list[str] = field(default_factory=list)  # 代入対象の変数名リスト
    referenced_vars: list[str] = field(default_factory=list)  # 参照対象の変数名リスト


@dataclass
class Warning:
    """警告

    チェッカーが検出した警告情報を保持するデータクラス。
    Override（VALUE値上書き）またはUninitialized（未初期化変数参照）の
    いずれかの警告種別を持つ。
    """

    file_name: str  # ファイル名
    line_number: int  # 行番号
    variable_name: str  # 変数名
    warning_type: str  # "Override" または "Uninitialized"
    message: str  # 警告メッセージ


__all__ = [
    "NormalizedLine",
    "VariableDefinition",
    "StatementRecord",
    "Warning",
]
