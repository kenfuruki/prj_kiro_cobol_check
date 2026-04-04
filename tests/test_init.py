"""__init__.py のデータクラス定義に対するユニットテスト"""

from cobol_static_checker import (
    NormalizedLine,
    StatementRecord,
    VariableDefinition,
    Warning,
)


class TestNormalizedLine:
    """NormalizedLineデータクラスのテスト"""

    def test_基本的なインスタンス生成(self):
        line = NormalizedLine(line_number=1, content="MOVE A TO B", is_continuation=False)
        assert line.line_number == 1
        assert line.content == "MOVE A TO B"
        assert line.is_continuation is False

    def test_継続行フラグ(self):
        line = NormalizedLine(line_number=5, content="長い文の続き", is_continuation=True)
        assert line.is_continuation is True
        assert line.line_number == 5


class TestVariableDefinition:
    """VariableDefinitionデータクラスのテスト"""

    def test_基本的な変数定義(self):
        var = VariableDefinition(
            level=1,
            name="WS-COUNTER",
            has_value=True,
            is_group=False,
            has_copy=False,
            parent_name=None,
            line_number=10,
        )
        assert var.level == 1
        assert var.name == "WS-COUNTER"
        assert var.has_value is True
        assert var.is_group is False
        assert var.has_copy is False
        assert var.parent_name is None
        assert var.line_number == 10

    def test_グループ項目と親子関係(self):
        var = VariableDefinition(
            level=5,
            name="WS-CHILD",
            has_value=False,
            is_group=False,
            has_copy=False,
            parent_name="WS-PARENT",
            line_number=15,
        )
        assert var.parent_name == "WS-PARENT"
        assert var.level == 5

    def test_全角文字の変数名(self):
        var = VariableDefinition(
            level=1,
            name="顧客名カナ",
            has_value=False,
            is_group=False,
            has_copy=False,
            parent_name=None,
            line_number=20,
        )
        assert var.name == "顧客名カナ"

    def test_COPY句あり(self):
        var = VariableDefinition(
            level=1,
            name="COPY-VAR",
            has_value=False,
            is_group=False,
            has_copy=True,
            parent_name=None,
            line_number=25,
        )
        assert var.has_copy is True


class TestStatementRecord:
    """StatementRecordデータクラスのテスト"""

    def test_代入と参照の変数リスト(self):
        stmt = StatementRecord(
            line_number=100,
            statement_type="MOVE",
            assigned_vars=["WS-TARGET"],
            referenced_vars=["WS-SOURCE"],
        )
        assert stmt.line_number == 100
        assert stmt.statement_type == "MOVE"
        assert stmt.assigned_vars == ["WS-TARGET"]
        assert stmt.referenced_vars == ["WS-SOURCE"]

    def test_デフォルトの空リスト(self):
        stmt = StatementRecord(line_number=50, statement_type="DISPLAY")
        assert stmt.assigned_vars == []
        assert stmt.referenced_vars == []

    def test_複数変数の代入(self):
        stmt = StatementRecord(
            line_number=200,
            statement_type="COMPUTE",
            assigned_vars=["WS-RESULT"],
            referenced_vars=["WS-A", "WS-B"],
        )
        assert len(stmt.referenced_vars) == 2


class TestWarning:
    """Warningデータクラスのテスト"""

    def test_Override警告(self):
        w = Warning(
            file_name="test.cbl",
            line_number=10,
            variable_name="WS-VAR",
            warning_type="Override",
            message="VALUE句で設定された値が上書きされています",
        )
        assert w.warning_type == "Override"
        assert w.file_name == "test.cbl"

    def test_Uninitialized警告(self):
        w = Warning(
            file_name="main.cob",
            line_number=50,
            variable_name="WS-UNINIT",
            warning_type="Uninitialized",
            message="未初期化の変数が参照されています",
        )
        assert w.warning_type == "Uninitialized"
        assert w.variable_name == "WS-UNINIT"
