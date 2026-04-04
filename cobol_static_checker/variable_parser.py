"""変数定義パーサー

WORKING-STORAGE SECTIONの変数定義を解析する。
- WORKING-STORAGE SECTIONの開始・終了検出
- レベル番号、変数名、VALUE句、PIC句、COPY句の解析
- グループ項目の親子関係構築
- 全角文字を含む識別子の認識
- FILLER項目とレベル88条件名の処理
- COPY句のみで構成される集団項目（子孫なし）の除外
"""

import re

from cobol_static_checker import NormalizedLine, VariableDefinition

# --- 識別子パターン定義 ---
# 半角英数字とハイフン・アンダースコア
_HAN = r"A-Za-z0-9\-_"
# 全角文字（ひらがな、カタカナ、CJK漢字、全角英数・記号、CJK記号）
_ZEN = (
    r"\u3040-\u309F"  # ひらがな全域
    r"\u30A0-\u30FF"  # カタカナ全域
    r"\u4E00-\u9FFF"  # CJK統合漢字
    r"\uFF01-\uFF9F"  # 全角英数・記号
    r"\u3000-\u303F"  # CJK記号
)
_ID_START = rf"[A-Za-z{_ZEN}]"
_ID_CONT = rf"[{_HAN}{_ZEN}]"
_ID_PAT = rf"(?:{_ID_START}{_ID_CONT}*)"

# --- 正規表現パターン ---
RE_PIC = re.compile(r"\bPIC(?:TURE)?\b", re.IGNORECASE)
RE_VALUE = re.compile(r"\bVALUE\b", re.IGNORECASE)
RE_FILLER = re.compile(r"\bFILLER\b", re.IGNORECASE)
RE_COPY = re.compile(r"^\s*COPY\b", re.IGNORECASE)

# データ項目エントリ: レベル番号(2桁) + 空白 + 変数名
RE_DATA_ENTRY = re.compile(
    rf"^(\d{{2}})\s+({_ID_PAT})",
    re.IGNORECASE,
)

# セクション検出パターン
RE_WORKING_STORAGE = re.compile(
    r"\bWORKING-STORAGE\s+SECTION\b", re.IGNORECASE
)
# WORKING-STORAGE SECTIONの終了を示すパターン
RE_SECTION_END = re.compile(
    r"\b(?:PROCEDURE\s+DIVISION|LINKAGE\s+SECTION|"
    r"LOCAL-STORAGE\s+SECTION|COMMUNICATION\s+SECTION|"
    r"REPORT\s+SECTION|SCREEN\s+SECTION|FILE\s+SECTION)\b",
    re.IGNORECASE,
)


def _collect_statements_in_section(
    lines: list[NormalizedLine],
) -> list[tuple[int, str]]:
    """WORKING-STORAGE SECTION内の文（ピリオド区切り）を収集する。

    Args:
        lines: 正規化済み論理行リスト

    Returns:
        (行番号, 文テキスト) のリスト。行番号は文の開始行。
    """
    in_section = False
    statements: list[tuple[int, str]] = []
    # 文バッファ: ピリオドで区切られるまで蓄積
    buf = ""
    buf_line = 0

    for nline in lines:
        text = nline.content

        if not in_section:
            # WORKING-STORAGE SECTIONの開始を検出
            if RE_WORKING_STORAGE.search(text):
                in_section = True
            continue

        # セクション終了を検出
        if RE_SECTION_END.search(text):
            break

        # 文バッファに追加
        if not buf:
            buf_line = nline.line_number

        buf += " " + text

        # ピリオドで文が終了するか確認
        # ピリオドが文字列リテラル内にある可能性は低いため、単純に末尾のピリオドを検出
        stripped = buf.strip()
        if stripped.endswith("."):
            statements.append((buf_line, stripped))
            buf = ""
            buf_line = 0

    # バッファに残った内容があれば文として追加
    if buf.strip():
        statements.append((buf_line, buf.strip()))

    return statements


def _parse_single_statement(
    line_number: int, stmt: str
) -> VariableDefinition | None:
    """単一の文を解析してVariableDefinitionを返す。

    FILLER項目とレベル88条件名はNoneを返す。

    Args:
        line_number: 文の開始行番号
        stmt: 文テキスト（ピリオド付き）

    Returns:
        VariableDefinition、またはスキップ対象の場合はNone
    """
    m = RE_DATA_ENTRY.match(stmt)
    if not m:
        return None

    level = int(m.group(1))
    name = m.group(2)

    # レベル88条件名はスキップ
    if level == 88:
        return None

    # FILLER項目はスキップ
    if RE_FILLER.match(name):
        return None

    # VALUE句の有無
    has_value = bool(RE_VALUE.search(stmt))

    # PIC句の有無（グループ項目判定に使用）
    has_pic = bool(RE_PIC.search(stmt))

    # COPY句の有無: 変数名以降の残りテキストでCOPY句を検出
    remaining = stmt[m.end():]
    has_copy = bool(RE_COPY.search(remaining))

    # グループ項目: PIC句なしの場合（COPY句のみの場合もグループ扱い）
    is_group = not has_pic

    return VariableDefinition(
        level=level,
        name=name,
        has_value=has_value,
        is_group=is_group,
        has_copy=has_copy,
        parent_name=None,  # 後で親子関係構築時に設定
        line_number=line_number,
    )


def _build_hierarchy(variables: list[VariableDefinition]) -> list[VariableDefinition]:
    """変数リストにレベル番号に基づく親子関係を設定する。

    レベルスタックを使用して、各変数の親グループ項目を決定する。

    Args:
        variables: 解析済みの変数定義リスト（parent_nameは未設定）

    Returns:
        親子関係が設定された変数定義リスト
    """
    # レベルスタック: (レベル番号, 変数名) のリスト
    level_stack: list[tuple[int, str]] = []

    for var in variables:
        # 現在のレベル以上のエントリをスタックからポップ
        while level_stack and level_stack[-1][0] >= var.level:
            level_stack.pop()

        # スタックに親がいれば設定
        if level_stack:
            var.parent_name = level_stack[-1][1]

        # グループ項目の場合はスタックに追加
        if var.is_group:
            level_stack.append((var.level, var.name))

    return variables


def _remove_copy_only_groups(
    variables: list[VariableDefinition],
) -> list[VariableDefinition]:
    """COPY句のみで構成される集団項目（子孫なし）を除外する。

    グループ項目のうち、自身がCOPY句を持ち、子孫となる変数が
    結果リストに存在しないものを除外する。

    Args:
        variables: 親子関係構築済みの変数定義リスト

    Returns:
        COPY句のみの集団項目を除外した変数定義リスト
    """
    # 子を持つ親の名前を収集
    parent_names: set[str] = set()
    for var in variables:
        if var.parent_name is not None:
            parent_names.add(var.parent_name)

    # COPY句のみのグループ項目（子孫なし）を除外
    result: list[VariableDefinition] = []
    for var in variables:
        if var.is_group and var.has_copy and var.name not in parent_names:
            continue
        result.append(var)

    return result


def parse_variables(lines: list[NormalizedLine]) -> list[VariableDefinition]:
    """正規化済み論理行からWORKING-STORAGE SECTIONの変数定義を解析する。

    処理:
    1. WORKING-STORAGE SECTIONの開始・終了を検出
    2. レベル番号、変数名、VALUE句、PIC句、COPY句を解析
    3. グループ項目の親子関係を構築
    4. 全角文字を含む識別子を認識
    5. COPY句のみで構成される集団項目（子孫なし）を除外

    Args:
        lines: 正規化済みのNormalizedLineリスト

    Returns:
        解析済みのVariableDefinitionリスト
    """
    # 1. WORKING-STORAGE SECTION内の文を収集
    statements = _collect_statements_in_section(lines)

    # 2. 各文を解析して変数定義を抽出
    # COPY文が独立行として出現した場合、直前のグループ項目にフラグを立てる
    variables: list[VariableDefinition] = []
    for line_number, stmt in statements:
        # COPY文が独立行として出現した場合の処理
        if RE_COPY.match(stmt.strip()):
            if variables and variables[-1].is_group:
                variables[-1] = VariableDefinition(
                    level=variables[-1].level,
                    name=variables[-1].name,
                    has_value=variables[-1].has_value,
                    is_group=variables[-1].is_group,
                    has_copy=True,
                    parent_name=variables[-1].parent_name,
                    line_number=variables[-1].line_number,
                )
            continue

        var = _parse_single_statement(line_number, stmt)
        if var is not None:
            variables.append(var)

    # 3. 親子関係を構築
    _build_hierarchy(variables)

    # 4. COPY句のみの集団項目を除外
    variables = _remove_copy_only_groups(variables)

    return variables
