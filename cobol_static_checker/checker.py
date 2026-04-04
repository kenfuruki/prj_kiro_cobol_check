"""チェッカー

変数定義と文解析の結果を突合し、Override警告とUninitialized警告を検出する。

- Override警告: VALUE句あり + PROCEDURE DIVISIONで代入あり → 警告発行
- Override除外: FILLER項目、レベル88条件名（パーサーで除外済み）
- Uninitialized警告: VALUE句なし + 代入なし + COPY句なし + 参照あり → 警告発行
- Uninitialized除外: COPY句あり、グループ項目の従属項目にVALUE句あり
- 集団項目の初期化波及（親が初期化されたら子も初期化済みとする）
- グループ項目自体はチェック対象外
"""

from cobol_static_checker import StatementRecord, VariableDefinition, Warning


def _build_children_map(
    variables: list[VariableDefinition],
) -> dict[str, list[str]]:
    """親変数名から子変数名リストへのマッピングを構築する。

    Args:
        variables: 変数定義リスト

    Returns:
        親変数名 → 子変数名リストの辞書
    """
    children: dict[str, list[str]] = {}
    for var in variables:
        if var.parent_name is not None:
            children.setdefault(var.parent_name, []).append(var.name)
    return children


def _get_all_descendants(
    name: str, children_map: dict[str, list[str]]
) -> list[str]:
    """指定した変数の全子孫変数名を再帰的に取得する。

    Args:
        name: 起点の変数名
        children_map: 親→子のマッピング

    Returns:
        全子孫変数名のリスト
    """
    result: list[str] = []
    stack = list(children_map.get(name, []))
    while stack:
        child = stack.pop()
        result.append(child)
        stack.extend(children_map.get(child, []))
    return result


def _propagate_group_value(
    variables: list[VariableDefinition],
    children_map: dict[str, list[str]],
) -> set[str]:
    """VALUE句ありの変数を初期化済みセットに追加し、グループ項目の初期化を子に波及する。

    Args:
        variables: 変数定義リスト
        children_map: 親→子のマッピング

    Returns:
        初期化済み変数名のセット
    """
    initialized: set[str] = set()

    # VALUE句ありの変数を初期化済みに追加
    for var in variables:
        if var.has_value:
            initialized.add(var.name)

    # グループ項目の初期化を子孫に波及
    for var in variables:
        if var.is_group and var.name in initialized:
            for desc in _get_all_descendants(var.name, children_map):
                initialized.add(desc)

    return initialized


def _mark_initialized_with_children(
    name: str,
    initialized: set[str],
    children_map: dict[str, list[str]],
) -> None:
    """変数とその全子孫を初期化済みセットに追加する。

    Args:
        name: 初期化する変数名
        initialized: 初期化済みセット（破壊的に更新）
        children_map: 親→子のマッピング
    """
    initialized.add(name)
    for desc in _get_all_descendants(name, children_map):
        initialized.add(desc)


def _is_checkable(var: VariableDefinition) -> bool:
    """チェック対象の変数かどうかを判定する。

    グループ項目はチェック対象外。
    FILLER項目とレベル88条件名はパーサーで除外済みのため、ここでは判定不要。

    Args:
        var: 変数定義

    Returns:
        チェック対象ならTrue
    """
    # グループ項目はチェック対象外
    if var.is_group:
        return False
    return True


def _has_subordinate_with_value(
    var: VariableDefinition,
    variables: list[VariableDefinition],
) -> bool:
    """変数の親グループ自体にVALUE句があるかを判定する。

    親グループにVALUE句がある場合、その従属項目は
    _propagate_group_valueで初期化済みセットに追加されるため、
    ここでは親グループ自体のVALUE句のみを確認する。

    注意: 兄弟変数にVALUE句があるだけでは除外しない。
    親グループ全体がVALUE句で初期化されている場合のみ除外対象。

    Args:
        var: 対象の変数定義
        variables: 全変数定義リスト

    Returns:
        親グループにVALUE句があればTrue
    """
    if var.parent_name is None:
        return False

    # 親グループ自体にVALUE句があるか確認
    for v in variables:
        if v.name == var.parent_name and v.has_value:
            return True

    return False


def check(
    variables: list[VariableDefinition],
    statements: list[StatementRecord],
    file_name: str = "",
) -> list[Warning]:
    """Override警告とUninitialized警告を検出する。

    処理フロー:
    1. 変数定義からVALUE句ありの変数を「初期化済み」セットに追加
    2. グループ項目の初期化を子に波及
    3. PROCEDURE DIVISIONの各文を順に処理:
       - 参照変数が初期化済みセットにない → Uninitialized警告
       - 代入変数がVALUE句あり → Override警告
       - 代入後、変数とその子を初期化済みに追加

    Args:
        variables: 変数定義リスト
        statements: 文解析レコードリスト
        file_name: ファイル名（警告メッセージに含める）

    Returns:
        検出された警告のリスト
    """
    # 変数名→変数定義のマッピング
    var_map: dict[str, VariableDefinition] = {v.name: v for v in variables}

    # 親→子のマッピング
    children_map = _build_children_map(variables)

    # 初期化済みセットの構築（VALUE句 + グループ波及）
    initialized = _propagate_group_value(variables, children_map)

    # COPY句ありの変数名セット
    copy_vars: set[str] = {v.name for v in variables if v.has_copy}

    # VALUE句ありの変数名セット
    value_vars: set[str] = {v.name for v in variables if v.has_value}

    warnings: list[Warning] = []

    # 各文を順に処理
    for stmt in statements:
        # 参照変数のチェック（Uninitialized警告）
        for ref_var in stmt.referenced_vars:
            vdef = var_map.get(ref_var)
            if vdef is None:
                continue
            if not _is_checkable(vdef):
                continue
            if ref_var in initialized:
                continue
            # COPY句ありは除外
            if ref_var in copy_vars:
                continue
            # グループ項目の従属項目にVALUE句がある場合は除外
            if _has_subordinate_with_value(vdef, variables):
                continue
            warnings.append(
                Warning(
                    file_name=file_name,
                    line_number=stmt.line_number,
                    variable_name=ref_var,
                    warning_type="Uninitialized",
                    message=f"変数 {ref_var} はVALUE句も代入もなく参照されています",
                )
            )

        # 代入変数のチェック（Override警告）+ 初期化済みへの追加
        for asgn_var in stmt.assigned_vars:
            vdef = var_map.get(asgn_var)
            if vdef is not None and _is_checkable(vdef):
                if asgn_var in value_vars:
                    warnings.append(
                        Warning(
                            file_name=file_name,
                            line_number=stmt.line_number,
                            variable_name=asgn_var,
                            warning_type="Override",
                            message=f"変数 {asgn_var} はVALUE句で初期化済みですが上書きされています",
                        )
                    )
            # 代入後、変数とその子を初期化済みに追加
            _mark_initialized_with_children(asgn_var, initialized, children_map)

    return warnings
