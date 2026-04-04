"""文解析エンジンのユニットテスト

statement_analyzer.pyの各文解析機能をテストする。
"""

import pytest

from cobol_static_checker import NormalizedLine, StatementRecord
from cobol_static_checker.statement_analyzer import (
    _extract_var_names,
    analyze_statements,
)


def _make_lines(contents: list[str]) -> list[NormalizedLine]:
    """テスト用のNormalizedLineリストを生成するヘルパー。"""
    return [
        NormalizedLine(line_number=i + 1, content=c, is_continuation=False)
        for i, c in enumerate(contents)
    ]


class TestExtractVarNames:
    """_extract_var_names関数のテスト"""

    def test_simple_variable(self):
        """単純な変数名を抽出できる"""
        result = _extract_var_names("WS-COUNT")
        assert result == ["WS-COUNT"]

    def test_excludes_keywords(self):
        """COBOLキーワードを除外する"""
        result = _extract_var_names("MOVE WS-A TO WS-B")
        assert "MOVE" not in result
        assert "TO" not in result
        assert "WS-A" in result
        assert "WS-B" in result

    def test_excludes_literals(self):
        """リテラルを除外する"""
        result = _extract_var_names("ZERO SPACES WS-VAR")
        assert "ZERO" not in result
        assert "SPACES" not in result
        assert "WS-VAR" in result

    def test_excludes_numbers(self):
        """数値を除外する"""
        result = _extract_var_names("123 WS-VAR")
        assert "WS-VAR" in result
        assert len(result) == 1


class TestProcedureDivisionDetection:
    """PROCEDURE DIVISION検出のテスト"""

    def test_no_procedure_division(self):
        """PROCEDURE DIVISIONがない場合は空リストを返す"""
        lines = _make_lines([
            "       WORKING-STORAGE SECTION.",
            "       01 WS-VAR PIC X.",
        ])
        result = analyze_statements(lines)
        assert result == []

    def test_procedure_division_detected(self):
        """PROCEDURE DIVISIONを検出して文を解析する"""
        lines = _make_lines([
            "       PROCEDURE DIVISION.",
            "           MOVE WS-A TO WS-B.",
        ])
        result = analyze_statements(lines)
        assert len(result) > 0


class TestMoveStatement:
    """MOVE文の解析テスト"""

    def test_simple_move(self):
        """単純なMOVE文を解析する"""
        lines = _make_lines([
            "       PROCEDURE DIVISION.",
            "           MOVE WS-SRC TO WS-DST.",
        ])
        result = analyze_statements(lines)
        move_recs = [r for r in result if r.statement_type == "MOVE"]
        assert len(move_recs) == 1
        assert "WS-DST" in move_recs[0].assigned_vars
        assert "WS-SRC" in move_recs[0].referenced_vars

    def test_move_multiple_destinations(self):
        """複数の送り先を持つMOVE文を解析する"""
        lines = _make_lines([
            "       PROCEDURE DIVISION.",
            "           MOVE WS-SRC TO WS-A WS-B.",
        ])
        result = analyze_statements(lines)
        move_recs = [r for r in result if r.statement_type == "MOVE"]
        assert len(move_recs) == 1
        assert "WS-A" in move_recs[0].assigned_vars
        assert "WS-B" in move_recs[0].assigned_vars

    def test_move_literal_source(self):
        """リテラルを送り元とするMOVE文"""
        lines = _make_lines([
            "       PROCEDURE DIVISION.",
            "           MOVE SPACES TO WS-DST.",
        ])
        result = analyze_statements(lines)
        move_recs = [r for r in result if r.statement_type == "MOVE"]
        assert len(move_recs) == 1
        assert "WS-DST" in move_recs[0].assigned_vars
        # SPACESはリテラルなので参照変数に含まれない
        assert move_recs[0].referenced_vars == []


class TestComputeStatement:
    """COMPUTE文の解析テスト"""

    def test_simple_compute(self):
        """単純なCOMPUTE文を解析する"""
        lines = _make_lines([
            "       PROCEDURE DIVISION.",
            "           COMPUTE WS-RESULT = WS-A + WS-B.",
        ])
        result = analyze_statements(lines)
        comp_recs = [r for r in result if r.statement_type == "COMPUTE"]
        assert len(comp_recs) == 1
        assert "WS-RESULT" in comp_recs[0].assigned_vars
        assert "WS-A" in comp_recs[0].referenced_vars
        assert "WS-B" in comp_recs[0].referenced_vars


class TestArithmeticStatements:
    """算術文（ADD, SUBTRACT, MULTIPLY, DIVIDE）の解析テスト"""

    def test_add_to(self):
        """ADD ... TO文を解析する"""
        lines = _make_lines([
            "       PROCEDURE DIVISION.",
            "           ADD WS-A TO WS-B.",
        ])
        result = analyze_statements(lines)
        add_recs = [r for r in result if r.statement_type == "ADD"]
        assert len(add_recs) == 1
        assert "WS-B" in add_recs[0].assigned_vars

    def test_add_giving(self):
        """ADD ... GIVING文を解析する"""
        lines = _make_lines([
            "       PROCEDURE DIVISION.",
            "           ADD WS-A WS-B GIVING WS-C.",
        ])
        result = analyze_statements(lines)
        add_recs = [r for r in result if r.statement_type == "ADD"]
        assert len(add_recs) == 1
        assert "WS-C" in add_recs[0].assigned_vars
        assert "WS-A" in add_recs[0].referenced_vars
        assert "WS-B" in add_recs[0].referenced_vars

    def test_subtract_from(self):
        """SUBTRACT ... FROM文を解析する"""
        lines = _make_lines([
            "       PROCEDURE DIVISION.",
            "           SUBTRACT WS-A FROM WS-B.",
        ])
        result = analyze_statements(lines)
        # SUBTRACTのFROMはTOと同様に扱われないため、
        # 算術文として解析される
        sub_recs = [r for r in result if r.statement_type == "SUBTRACT"]
        assert len(sub_recs) >= 1


class TestInitializeStatement:
    """INITIALIZE文の解析テスト"""

    def test_initialize(self):
        """INITIALIZE文を解析する"""
        lines = _make_lines([
            "       PROCEDURE DIVISION.",
            "           INITIALIZE WS-RECORD.",
        ])
        result = analyze_statements(lines)
        init_recs = [r for r in result if r.statement_type == "INITIALIZE"]
        assert len(init_recs) == 1
        assert "WS-RECORD" in init_recs[0].assigned_vars


class TestAcceptStatement:
    """ACCEPT文の解析テスト"""

    def test_accept(self):
        """ACCEPT文を解析する"""
        lines = _make_lines([
            "       PROCEDURE DIVISION.",
            "           ACCEPT WS-INPUT FROM CONSOLE.",
        ])
        result = analyze_statements(lines)
        acc_recs = [r for r in result if r.statement_type == "ACCEPT"]
        assert len(acc_recs) == 1
        assert "WS-INPUT" in acc_recs[0].assigned_vars


class TestReadIntoStatement:
    """READ INTO文の解析テスト"""

    def test_read_into(self):
        """READ INTO文を解析する"""
        lines = _make_lines([
            "       PROCEDURE DIVISION.",
            "           READ INPUT-FILE INTO WS-RECORD.",
        ])
        result = analyze_statements(lines)
        read_recs = [r for r in result if r.statement_type == "READ"]
        assert len(read_recs) == 1
        assert "WS-RECORD" in read_recs[0].assigned_vars


class TestStringUnstringStatements:
    """STRING/UNSTRING文の解析テスト"""

    def test_string_into(self):
        """STRING INTO文を解析する"""
        lines = _make_lines([
            "       PROCEDURE DIVISION.",
            "           STRING WS-A DELIMITED BY SPACE",
            "               INTO WS-RESULT.",
        ])
        result = analyze_statements(lines)
        str_recs = [r for r in result if r.statement_type == "STRING"]
        assert len(str_recs) == 1
        assert "WS-RESULT" in str_recs[0].assigned_vars

    def test_unstring_into(self):
        """UNSTRING INTO文を解析する"""
        lines = _make_lines([
            "       PROCEDURE DIVISION.",
            "           UNSTRING WS-INPUT DELIMITED BY SPACE",
            "               INTO WS-PART1 WS-PART2.",
        ])
        result = analyze_statements(lines)
        uns_recs = [r for r in result if r.statement_type == "UNSTRING"]
        assert len(uns_recs) == 1
        assert "WS-PART1" in uns_recs[0].assigned_vars
        assert "WS-PART2" in uns_recs[0].assigned_vars


class TestDisplayStatement:
    """DISPLAY文の解析テスト"""

    def test_display(self):
        """DISPLAY文を解析する"""
        lines = _make_lines([
            "       PROCEDURE DIVISION.",
            "           DISPLAY WS-MSG.",
        ])
        result = analyze_statements(lines)
        disp_recs = [r for r in result if r.statement_type == "DISPLAY"]
        assert len(disp_recs) == 1
        assert "WS-MSG" in disp_recs[0].referenced_vars
        assert disp_recs[0].assigned_vars == []


class TestCallUsingStatement:
    """CALL USING文の解析テスト"""

    def test_call_using(self):
        """CALL USING文を解析する"""
        lines = _make_lines([
            "       PROCEDURE DIVISION.",
            "           CALL 'SUBPROG' USING WS-PARAM1 WS-PARAM2.",
        ])
        result = analyze_statements(lines)
        call_recs = [r for r in result if r.statement_type == "CALL"]
        assert len(call_recs) == 1
        assert "WS-PARAM1" in call_recs[0].referenced_vars
        assert "WS-PARAM2" in call_recs[0].referenced_vars


class TestPerformVaryingStatement:
    """PERFORM VARYING文の解析テスト"""

    def test_perform_varying(self):
        """PERFORM VARYING文を解析する"""
        lines = _make_lines([
            "       PROCEDURE DIVISION.",
            "           PERFORM VARYING WS-IDX FROM 1 BY 1",
            "               UNTIL WS-IDX > 10.",
        ])
        result = analyze_statements(lines)
        perf_recs = [r for r in result if r.statement_type == "PERFORM"]
        assert len(perf_recs) == 1
        assert "WS-IDX" in perf_recs[0].assigned_vars


class TestConditionReferences:
    """条件参照変数の抽出テスト"""

    def test_if_condition(self):
        """IF文の条件変数を参照として抽出する"""
        lines = _make_lines([
            "       PROCEDURE DIVISION.",
            "           IF WS-FLAG = 1.",
        ])
        result = analyze_statements(lines)
        cond_recs = [r for r in result if r.statement_type == "CONDITION"]
        assert len(cond_recs) >= 1
        all_refs = []
        for r in cond_recs:
            all_refs.extend(r.referenced_vars)
        assert "WS-FLAG" in all_refs

    def test_until_condition(self):
        """UNTIL句の条件変数を参照として抽出する"""
        lines = _make_lines([
            "       PROCEDURE DIVISION.",
            "           PERFORM VARYING WS-I FROM 1 BY 1",
            "               UNTIL WS-DONE = 'Y'.",
        ])
        result = analyze_statements(lines)
        cond_recs = [r for r in result if r.statement_type == "CONDITION"]
        all_refs = []
        for r in cond_recs:
            all_refs.extend(r.referenced_vars)
        assert "WS-DONE" in all_refs
