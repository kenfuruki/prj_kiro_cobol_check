"""チェッカーのユニットテスト

Override警告・Uninitialized警告の発行条件と除外条件をテストする。
"""

import pytest

from cobol_static_checker import StatementRecord, VariableDefinition, Warning
from cobol_static_checker.checker import (
    _build_children_map,
    _get_all_descendants,
    _has_subordinate_with_value,
    _is_checkable,
    _mark_initialized_with_children,
    _propagate_group_value,
    check,
)


# --- ヘルパー関数 ---

def _var(
    name: str,
    level: int = 5,
    has_value: bool = False,
    is_group: bool = False,
    has_copy: bool = False,
    parent_name: str | None = None,
    line_number: int = 10,
) -> VariableDefinition:
    """テスト用のVariableDefinitionを簡易生成する。"""
    return VariableDefinition(
        level=level,
        name=name,
        has_value=has_value,
        is_group=is_group,
        has_copy=has_copy,
        parent_name=parent_name,
        line_number=line_number,
    )


def _stmt(
    line_number: int = 100,
    statement_type: str = "MOVE",
    assigned_vars: list[str] | None = None,
    referenced_vars: list[str] | None = None,
) -> StatementRecord:
    """テスト用のStatementRecordを簡易生成する。"""
    return StatementRecord(
        line_number=line_number,
        statement_type=statement_type,
        assigned_vars=assigned_vars or [],
        referenced_vars=referenced_vars or [],
    )


# --- _build_children_map テスト ---

class TestBuildChildrenMap:
    """親→子マッピングの構築テスト。"""

    def test_empty(self):
        assert _build_children_map([]) == {}

    def test_no_parent(self):
        """親なしの変数のみの場合、空の辞書を返す。"""
        variables = [_var("WK-A"), _var("WK-B")]
        assert _build_children_map(variables) == {}

    def test_parent_child(self):
        """親子関係がある場合、正しくマッピングされる。"""
        variables = [
            _var("WK-GROUP", level=1, is_group=True),
            _var("WK-A", level=5, parent_name="WK-GROUP"),
            _var("WK-B", level=5, parent_name="WK-GROUP"),
        ]
        result = _build_children_map(variables)
        assert result == {"WK-GROUP": ["WK-A", "WK-B"]}


# --- _get_all_descendants テスト ---

class TestGetAllDescendants:
    """全子孫取得テスト。"""

    def test_no_children(self):
        assert _get_all_descendants("WK-A", {}) == []

    def test_nested(self):
        """ネストされた子孫を全て取得する。"""
        children_map = {
            "WK-GROUP": ["WK-SUB"],
            "WK-SUB": ["WK-ITEM"],
        }
        result = _get_all_descendants("WK-GROUP", children_map)
        assert set(result) == {"WK-SUB", "WK-ITEM"}


# --- _propagate_group_value テスト ---

class TestPropagateGroupValue:
    """グループ項目の初期化波及テスト。"""

    def test_value_propagation(self):
        """親グループにVALUE句がある場合、子孫も初期化済みになる。"""
        variables = [
            _var("WK-GROUP", level=1, is_group=True, has_value=True),
            _var("WK-A", level=5, parent_name="WK-GROUP"),
            _var("WK-B", level=5, parent_name="WK-GROUP"),
        ]
        children_map = _build_children_map(variables)
        initialized = _propagate_group_value(variables, children_map)
        assert "WK-GROUP" in initialized
        assert "WK-A" in initialized
        assert "WK-B" in initialized

    def test_no_propagation_without_value(self):
        """親グループにVALUE句がない場合、子は初期化されない。"""
        variables = [
            _var("WK-GROUP", level=1, is_group=True, has_value=False),
            _var("WK-A", level=5, parent_name="WK-GROUP"),
        ]
        children_map = _build_children_map(variables)
        initialized = _propagate_group_value(variables, children_map)
        assert "WK-GROUP" not in initialized
        assert "WK-A" not in initialized


# --- _is_checkable テスト ---

class TestIsCheckable:
    """チェック対象判定テスト。"""

    def test_elementary_item(self):
        """基本項目はチェック対象。"""
        assert _is_checkable(_var("WK-A")) is True

    def test_group_item_excluded(self):
        """グループ項目はチェック対象外。"""
        assert _is_checkable(_var("WK-GROUP", is_group=True)) is False


# --- check関数の統合テスト ---

class TestCheckOverride:
    """Override警告のテスト。"""

    def test_override_warning(self):
        """VALUE句あり + 代入あり → Override警告。"""
        variables = [_var("WK-A", has_value=True)]
        statements = [_stmt(assigned_vars=["WK-A"])]
        result = check(variables, statements, "test.cbl")
        assert len(result) == 1
        assert result[0].warning_type == "Override"
        assert result[0].variable_name == "WK-A"
        assert result[0].file_name == "test.cbl"
        assert result[0].line_number == 100

    def test_no_override_without_value(self):
        """VALUE句なし + 代入あり → Override警告なし。"""
        variables = [_var("WK-A", has_value=False)]
        statements = [_stmt(assigned_vars=["WK-A"])]
        result = check(variables, statements)
        overrides = [w for w in result if w.warning_type == "Override"]
        assert len(overrides) == 0

    def test_no_override_for_group(self):
        """グループ項目はOverride警告対象外。"""
        variables = [_var("WK-GROUP", is_group=True, has_value=True)]
        statements = [_stmt(assigned_vars=["WK-GROUP"])]
        result = check(variables, statements)
        assert len(result) == 0

    def test_no_override_for_unknown_var(self):
        """変数定義にない変数への代入は警告なし。"""
        variables = [_var("WK-A")]
        statements = [_stmt(assigned_vars=["WK-UNKNOWN"])]
        result = check(variables, statements)
        assert len(result) == 0


class TestCheckUninitialized:
    """Uninitialized警告のテスト。"""

    def test_uninitialized_warning(self):
        """VALUE句なし + 代入なし + 参照あり → Uninitialized警告。"""
        variables = [_var("WK-A", has_value=False)]
        statements = [_stmt(referenced_vars=["WK-A"])]
        result = check(variables, statements, "test.cbl")
        assert len(result) == 1
        assert result[0].warning_type == "Uninitialized"
        assert result[0].variable_name == "WK-A"
        assert result[0].file_name == "test.cbl"

    def test_no_uninitialized_with_value(self):
        """VALUE句あり → Uninitialized警告なし。"""
        variables = [_var("WK-A", has_value=True)]
        statements = [_stmt(referenced_vars=["WK-A"])]
        result = check(variables, statements)
        uninit = [w for w in result if w.warning_type == "Uninitialized"]
        assert len(uninit) == 0

    def test_no_uninitialized_after_assignment(self):
        """代入後の参照 → Uninitialized警告なし。"""
        variables = [_var("WK-A", has_value=False)]
        statements = [
            _stmt(line_number=100, assigned_vars=["WK-A"]),
            _stmt(line_number=200, referenced_vars=["WK-A"]),
        ]
        result = check(variables, statements)
        uninit = [w for w in result if w.warning_type == "Uninitialized"]
        assert len(uninit) == 0

    def test_no_uninitialized_with_copy(self):
        """COPY句あり → Uninitialized警告なし。"""
        variables = [_var("WK-A", has_copy=True)]
        statements = [_stmt(referenced_vars=["WK-A"])]
        result = check(variables, statements)
        uninit = [w for w in result if w.warning_type == "Uninitialized"]
        assert len(uninit) == 0

    def test_no_uninitialized_for_group(self):
        """グループ項目はUninitialized警告対象外。"""
        variables = [_var("WK-GROUP", is_group=True)]
        statements = [_stmt(referenced_vars=["WK-GROUP"])]
        result = check(variables, statements)
        assert len(result) == 0

    def test_no_uninitialized_subordinate_with_value(self):
        """グループ項目の従属項目にVALUE句がある場合、同じ親の他の子は除外。"""
        variables = [
            _var("WK-GROUP", level=1, is_group=True),
            _var("WK-A", level=5, parent_name="WK-GROUP", has_value=True),
            _var("WK-B", level=5, parent_name="WK-GROUP", has_value=False),
        ]
        statements = [_stmt(referenced_vars=["WK-B"])]
        result = check(variables, statements)
        uninit = [w for w in result if w.warning_type == "Uninitialized"]
        assert len(uninit) == 0


class TestCheckGroupPropagation:
    """集団項目の初期化波及テスト。"""

    def test_group_value_propagates_to_children(self):
        """親グループにVALUE句がある場合、子は初期化済みとして扱われる。"""
        variables = [
            _var("WK-GROUP", level=1, is_group=True, has_value=True),
            _var("WK-A", level=5, parent_name="WK-GROUP"),
            _var("WK-B", level=5, parent_name="WK-GROUP"),
        ]
        statements = [_stmt(referenced_vars=["WK-A", "WK-B"])]
        result = check(variables, statements)
        uninit = [w for w in result if w.warning_type == "Uninitialized"]
        assert len(uninit) == 0

    def test_assignment_propagates_to_children(self):
        """親グループへの代入後、子も初期化済みになる。"""
        variables = [
            _var("WK-GROUP", level=1, is_group=True),
            _var("WK-A", level=5, parent_name="WK-GROUP"),
        ]
        statements = [
            _stmt(line_number=100, assigned_vars=["WK-GROUP"]),
            _stmt(line_number=200, referenced_vars=["WK-A"]),
        ]
        result = check(variables, statements)
        uninit = [w for w in result if w.warning_type == "Uninitialized"]
        assert len(uninit) == 0


class TestCheckCombined:
    """複合シナリオのテスト。"""

    def test_both_warnings(self):
        """Override警告とUninitialized警告が同時に発行される。"""
        variables = [
            _var("WK-A", has_value=True),
            _var("WK-B", has_value=False),
        ]
        statements = [
            _stmt(line_number=100, assigned_vars=["WK-A"], referenced_vars=["WK-B"]),
        ]
        result = check(variables, statements, "test.cbl")
        overrides = [w for w in result if w.warning_type == "Override"]
        uninit = [w for w in result if w.warning_type == "Uninitialized"]
        assert len(overrides) == 1
        assert overrides[0].variable_name == "WK-A"
        assert len(uninit) == 1
        assert uninit[0].variable_name == "WK-B"

    def test_empty_inputs(self):
        """空の入力では警告なし。"""
        result = check([], [])
        assert result == []

    def test_no_statements(self):
        """文がない場合は警告なし。"""
        variables = [_var("WK-A")]
        result = check(variables, [])
        assert result == []

    def test_warning_message_contains_variable_name(self):
        """警告メッセージに変数名が含まれる。"""
        variables = [_var("WK-TEST", has_value=True)]
        statements = [_stmt(assigned_vars=["WK-TEST"])]
        result = check(variables, statements, "sample.cbl")
        assert len(result) == 1
        assert "WK-TEST" in result[0].message
        assert result[0].file_name == "sample.cbl"
