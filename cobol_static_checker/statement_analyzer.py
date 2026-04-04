"""文解析エンジン

PROCEDURE DIVISIONの各文を解析し、変数の代入・参照関係を記録する。
- PROCEDURE DIVISIONの検出
- MOVE文: 送り先=代入、送り元=参照（文中の全MOVE対応）
- COMPUTE文・算術文（ADD, SUBTRACT, MULTIPLY, DIVIDE）: 結果格納変数=代入
- INITIALIZE文: 対象変数=初期化（代入扱い）
- ACCEPT文: 対象変数=代入
- READ INTO文: INTO変数=代入
- STRING/UNSTRING文: INTO変数=代入
- DISPLAY文: 対象変数=参照
- CALL USING文: USING変数=参照
- PERFORM VARYING文: 制御変数=代入
- 条件参照変数の抽出（IF, WHEN, UNTIL, 比較演算子）
"""

import re

from cobol_static_checker import NormalizedLine, StatementRecord

# --- 識別子パターン定義（variable_parser.pyと共通） ---
_HAN = r"A-Za-z0-9\-_"
_ZEN = (
    r"\u3040-\u309F"
    r"\u30A0-\u30FF"
    r"\u4E00-\u9FFF"
    r"\uFF01-\uFF9F"
    r"\u3000-\u303F"
)
_ID_START = rf"[A-Za-z{_ZEN}]"
_ID_CONT = rf"[{_HAN}{_ZEN}]"
_ID_PAT = rf"(?:{_ID_START}{_ID_CONT}*)"

# --- 変数名トークン抽出用パターン ---
RE_VAR_TOKEN = re.compile(_ID_PAT, re.IGNORECASE)

# リテラルパターン（変数名候補から除外するもの）
RE_LITERAL = re.compile(
    r"""^(?:
    '[^']*'|"[^"]*"|[+\-]?\d+\.?\d*|
    ZERO|ZEROS|ZEROES|SPACE|SPACES|
    HIGH-VALUE|HIGH-VALUES|LOW-VALUE|LOW-VALUES|
    QUOTE|QUOTES|ALL|NULL|NULLS
)$""",
    re.IGNORECASE | re.VERBOSE,
)

# COBOLキーワード（変数名候補から除外するもの）
COBOL_KEYWORDS = frozenset({
    "ACCEPT", "ACCESS", "ADD", "ADDRESS", "ADVANCING", "AFTER", "ALL",
    "ALPHABETIC", "ALPHABETIC-LOWER", "ALPHABETIC-UPPER", "ALPHANUMERIC",
    "ALPHANUMERIC-EDITED", "ALSO", "ALTER", "ALTERNATE", "AND", "ANY",
    "APPLY", "ARE", "AREA", "AREAS", "ASCENDING", "ASSIGN", "AT",
    "AUTHOR",
    "BEFORE", "BINARY", "BLANK", "BLOCK", "BOTTOM", "BY",
    "CALL", "CANCEL", "CD", "CF", "CH", "CHARACTER", "CHARACTERS",
    "CLASS", "CLOCK-UNITS", "CLOSE", "COBOL", "CODE", "CODE-SET",
    "COLLATING", "COLUMN", "COMMA", "COMMON", "COMMUNICATION",
    "COMP", "COMP-1", "COMP-2", "COMP-3", "COMP-4", "COMP-5",
    "COMPUTATIONAL", "COMPUTATIONAL-1", "COMPUTATIONAL-2",
    "COMPUTATIONAL-3", "COMPUTATIONAL-4", "COMPUTATIONAL-5",
    "COMPUTE", "CONFIGURATION", "CONTAINS", "CONTENT", "CONTINUE",
    "CONTROL", "CONTROLS", "CONVERTING", "COPY", "CORR",
    "CORRESPONDING", "COUNT", "CURRENCY",
    "DATA", "DATE", "DATE-COMPILED", "DATE-WRITTEN", "DAY",
    "DAY-OF-WEEK", "DE", "DEBUG-CONTENTS", "DEBUG-ITEM",
    "DEBUG-LINE", "DEBUG-NAME", "DEBUG-SUB-1", "DEBUG-SUB-2",
    "DEBUG-SUB-3", "DEBUGGING", "DECIMAL-POINT", "DECLARATIVES",
    "DELETE", "DELIMITED", "DELIMITER", "DEPENDING", "DESCENDING",
    "DESTINATION", "DETAIL", "DISABLE", "DISPLAY", "DIVIDE",
    "DIVISION", "DOWN", "DUPLICATES", "DYNAMIC",
    "EGI", "ELSE", "EMI", "ENABLE", "END", "END-ADD", "END-CALL",
    "END-COMPUTE", "END-DELETE", "END-DIVIDE", "END-EVALUATE",
    "END-IF", "END-MULTIPLY", "END-OF-PAGE", "END-PERFORM",
    "END-READ", "END-RECEIVE", "END-RETURN", "END-REWRITE",
    "END-SEARCH", "END-START", "END-STRING", "END-SUBTRACT",
    "END-UNSTRING", "END-WRITE", "ENTER", "ENVIRONMENT", "EOP",
    "EQUAL", "ERROR", "ESI", "EVALUATE", "EVERY", "EXCEPTION",
    "EXIT", "EXTEND", "EXTERNAL",
    "FALSE", "FD", "FILE", "FILE-CONTROL", "FILLER", "FINAL",
    "FIRST", "FOOTING", "FOR", "FROM", "FUNCTION",
    "GENERATE", "GIVING", "GLOBAL", "GO", "GREATER", "GROUP",
    "HEADING", "HIGH-VALUE", "HIGH-VALUES",
    "I-O", "I-O-CONTROL", "IDENTIFICATION", "IF", "IN", "INDEX",
    "INDEXED", "INDICATE", "INITIAL", "INITIALIZE", "INITIATE",
    "INPUT", "INPUT-OUTPUT", "INSPECT", "INSTALLATION", "INTO",
    "INVALID", "IS",
    "JUST", "JUSTIFIED",
    "KEY",
    "LABEL", "LAST", "LEADING", "LEFT", "LENGTH", "LESS",
    "LIMIT", "LIMITS", "LINAGE", "LINAGE-COUNTER", "LINE",
    "LINE-COUNTER", "LINES", "LINKAGE", "LOCK", "LOW-VALUE",
    "LOW-VALUES",
    "MEMORY", "MERGE", "MESSAGE", "MODE", "MODULES", "MOVE",
    "MULTIPLY",
    "NATIVE", "NEGATIVE", "NEXT", "NO", "NOT", "NULL", "NULLS",
    "NUMBER", "NUMERIC", "NUMERIC-EDITED",
    "OBJECT-COMPUTER", "OCCURS", "OF", "OFF", "OMITTED", "ON",
    "OPEN", "OPTIONAL", "OR", "ORDER", "ORGANIZATION", "OTHER",
    "OUTPUT", "OVERFLOW",
    "PACKED-DECIMAL", "PADDING", "PAGE", "PAGE-COUNTER",
    "PERFORM", "PF", "PH", "PIC", "PICTURE", "PLUS", "POINTER",
    "POSITION", "POSITIVE", "PRINTING", "PROCEDURE", "PROCEDURES",
    "PROCEED", "PROGRAM", "PROGRAM-ID", "PURGE",
    "QUEUE", "QUOTE", "QUOTES",
    "RANDOM", "RD", "READ", "RECEIVE", "RECORD", "RECORDS",
    "REDEFINES", "REEL", "REFERENCE", "REFERENCES", "RELATIVE",
    "RELEASE", "REMAINDER", "REMOVAL", "RENAMES", "REPLACE",
    "REPLACING", "REPORT", "REPORTING", "REPORTS", "RERUN",
    "RESERVE", "RESET", "RETURN", "RETURNING", "REVERSED",
    "REWIND", "REWRITE", "RF", "RH", "RIGHT", "ROUNDED", "RUN",
    "SAME", "SD", "SEARCH", "SECTION", "SECURITY", "SEGMENT",
    "SEGMENT-LIMIT", "SELECT", "SEND", "SENTENCE", "SEPARATE",
    "SEQUENCE", "SEQUENTIAL", "SET", "SIGN", "SIZE", "SORT",
    "SORT-MERGE", "SOURCE", "SOURCE-COMPUTER", "SPACE", "SPACES",
    "SPECIAL-NAMES", "STANDARD", "STANDARD-1", "STANDARD-2",
    "START", "STATUS", "STOP", "STRING", "SUB-QUEUE-1",
    "SUB-QUEUE-2", "SUB-QUEUE-3", "SUBTRACT", "SUM", "SUPPRESS",
    "SYMBOLIC", "SYNC", "SYNCHRONIZED",
    "TABLE", "TALLYING", "TAPE", "TERMINAL", "TERMINATE", "TEST",
    "TEXT", "THAN", "THEN", "THROUGH", "THRU", "TIME", "TIMES",
    "TO", "TOP", "TRAILING", "TRUE", "TYPE",
    "UNIT", "UNSTRING", "UNTIL", "UP", "UPON", "USAGE", "USE",
    "USING",
    "VALUE", "VALUES", "VARYING",
    "WHEN", "WITH", "WORDS", "WORKING-STORAGE", "WRITE",
    "ZERO", "ZEROES", "ZEROS",
    # 追加: 比較演算子関連
    "EQUAL", "GREATER", "LESS", "THAN", "NOT",
})

# --- PROCEDURE DIVISION検出パターン ---
RE_PROC_DIV = re.compile(
    r"\bPROCEDURE\s+DIVISION\b", re.IGNORECASE
)

# --- 文パターン定義 ---
# MOVE文: 文中の全MOVE ... TO ... を抽出（反復対応）
RE_MOVE_ITER = re.compile(
    r"\bMOVE\s+(.*?)\s+TO\s+(.*?)(?=\s+MOVE\s|\.\s*$|$)",
    re.IGNORECASE | re.DOTALL,
)

# COMPUTE文の検出
RE_COMPUTE_KW = re.compile(r"\bCOMPUTE\b", re.IGNORECASE)

# 算術文のGIVING句
RE_ARITH_GIVING = re.compile(
    r"\bGIVING\s+(.*?)(?:\s+ROUNDED|\s+ON\s|\.\s*$|$)",
    re.IGNORECASE,
)

# 算術文のTO句（ADD ... TO ...）
RE_ARITH_TO = re.compile(
    r"\bTO\s+(.*?)(?:\s+GIVING\b|\s+ROUNDED|\s+ON\s|\.\s*$|$)",
    re.IGNORECASE,
)

# READ INTO文
RE_READ_INTO = re.compile(
    r"\bREAD\b.*?\bINTO\s+(.*?)(?:\.\s*$|$)", re.IGNORECASE
)

# INITIALIZE文
RE_INITIALIZE = re.compile(
    r"\bINITIALIZE\s+(.*?)(?:\s+REPLACING\b|\.\s*$|$)",
    re.IGNORECASE,
)

# ACCEPT文
RE_ACCEPT = re.compile(
    r"\bACCEPT\s+(.*?)(?:\s+FROM\b|\.\s*$|$)", re.IGNORECASE
)

# STRING ... INTO文
RE_STRING_INTO = re.compile(
    r"\bSTRING\b.*?\bINTO\s+(.*?)(?:\s+WITH\b|\s+ON\b|\s+POINTER\b|\.\s*$|$)",
    re.IGNORECASE,
)

# UNSTRING ... INTO文
RE_UNSTRING_INTO = re.compile(
    r"\bUNSTRING\b.*?\bINTO\s+(.*?)(?:\s+WITH\b|\s+ON\b|\s+TALLYING\b|\.\s*$|$)",
    re.IGNORECASE,
)

# DISPLAY文
RE_DISPLAY = re.compile(
    r"\bDISPLAY\s+(.*?)(?:\s+UPON\b|\s+WITH\b|\.\s*$|$)",
    re.IGNORECASE,
)

# CALL USING文
RE_CALL_USING = re.compile(
    r"\bCALL\b.*?\bUSING\s+(.*?)(?:\s+RETURNING\b|\.\s*$|$)",
    re.IGNORECASE,
)

# PERFORM VARYING文
RE_VARYING_VAR = re.compile(
    r"\bVARYING\s+(" + _ID_PAT + r")",
    re.IGNORECASE,
)

# 条件文キーワード
RE_IF = re.compile(r"\bIF\s+(.*?)(?:\s+THEN\b|\.\s*$|$)", re.IGNORECASE)
RE_WHEN = re.compile(r"\bWHEN\s+(.*?)(?:\.\s*$|$)", re.IGNORECASE)
RE_UNTIL = re.compile(r"\bUNTIL\s+(.*?)(?:\.\s*$|$)", re.IGNORECASE)

# 比較演算子パターン（条件式内の変数抽出用）
RE_COMPARISON = re.compile(
    r"(" + _ID_PAT + r")"
    r"\s+(?:=|>|<|>=|<=|NOT\s+=|NOT\s+>|NOT\s+<|"
    r"EQUAL|GREATER|LESS)\s+"
    r"(" + _ID_PAT + r")",
    re.IGNORECASE,
)


def _extract_var_names(text: str) -> list[str]:
    """テキストから変数名を抽出する。

    COBOLキーワード、リテラル、数値を除外し、
    変数名候補のみを返す。

    Args:
        text: 変数名を含むテキスト

    Returns:
        変数名のリスト（大文字化済み）
    """
    result: list[str] = []
    for tok in RE_VAR_TOKEN.findall(text):
        upper = tok.upper()
        if upper in COBOL_KEYWORDS:
            continue
        if RE_LITERAL.match(tok):
            continue
        if re.match(r"^\d+$", tok):
            continue
        result.append(upper)
    return result


def _collect_procedure_statements(
    lines: list[NormalizedLine],
) -> list[tuple[int, str]]:
    """PROCEDURE DIVISION内の文（ピリオド区切り）を収集する。

    Args:
        lines: 正規化済み論理行リスト

    Returns:
        (行番号, 文テキスト) のリスト
    """
    in_proc = False
    statements: list[tuple[int, str]] = []
    buf = ""
    buf_line = 0

    for nline in lines:
        text = nline.content
        if not in_proc:
            if RE_PROC_DIV.search(text):
                in_proc = True
            continue

        if not buf:
            buf_line = nline.line_number
        buf += " " + text

        stripped = buf.strip()
        if stripped.endswith("."):
            statements.append((buf_line, stripped))
            buf = ""
            buf_line = 0

    # バッファに残った内容があれば文として追加
    if buf.strip():
        statements.append((buf_line, buf.strip()))

    return statements


def _analyze_move(stmt: str, line_number: int) -> list[StatementRecord]:
    """MOVE文を解析する。文中の全MOVE ... TO ... を抽出。"""
    records: list[StatementRecord] = []
    for m in RE_MOVE_ITER.finditer(stmt):
        src_text = m.group(1)
        dst_text = m.group(2)
        src_vars = _extract_var_names(src_text)
        dst_vars = _extract_var_names(dst_text)
        records.append(StatementRecord(
            line_number=line_number,
            statement_type="MOVE",
            assigned_vars=dst_vars,
            referenced_vars=src_vars,
        ))
    return records


def _analyze_compute(stmt: str, line_number: int) -> StatementRecord:
    """COMPUTE文を解析する。左辺=代入、右辺=参照。"""
    # COMPUTE var = expr の形式
    m = re.match(
        r"\bCOMPUTE\s+(.*?)\s*=\s*(.*?)(?:\.\s*$|$)",
        stmt, re.IGNORECASE,
    )
    assigned: list[str] = []
    referenced: list[str] = []
    if m:
        assigned = _extract_var_names(m.group(1))
        referenced = _extract_var_names(m.group(2))
    return StatementRecord(
        line_number=line_number,
        statement_type="COMPUTE",
        assigned_vars=assigned,
        referenced_vars=referenced,
    )


def _analyze_arithmetic(
    stmt: str, line_number: int, stmt_type: str,
) -> StatementRecord:
    """算術文（ADD, SUBTRACT, MULTIPLY, DIVIDE）を解析する。

    GIVING句またはTO句の変数を代入対象として記録する。
    """
    assigned: list[str] = []
    referenced: list[str] = []

    # GIVING句がある場合
    m_giving = RE_ARITH_GIVING.search(stmt)
    if m_giving:
        assigned = _extract_var_names(m_giving.group(1))
        # GIVING前の全変数を参照として抽出
        before_giving = stmt[:m_giving.start()]
        referenced = _extract_var_names(before_giving)
        # キーワード自体を除去（ADD, SUBTRACT等）
        kw_upper = stmt_type.upper()
        referenced = [v for v in referenced if v != kw_upper]
    elif stmt_type.upper() in ("ADD", "SUBTRACT"):
        # TO句がある場合（ADD ... TO var / SUBTRACT ... FROM var）
        m_to = RE_ARITH_TO.search(stmt)
        if m_to:
            to_vars = _extract_var_names(m_to.group(1))
            assigned = to_vars
            # TO/FROM前の変数を参照として抽出
            before_to = stmt[:m_to.start()]
            referenced = _extract_var_names(before_to)
            kw_upper = stmt_type.upper()
            referenced = [v for v in referenced if v != kw_upper]
            # TO先の変数も参照（累積加算のため）
            referenced.extend(to_vars)
    else:
        # MULTIPLY ... BY var / DIVIDE ... INTO var
        # BY/INTO句の変数を代入対象として扱う
        m_by = re.search(
            r"\b(?:BY|INTO)\s+(.*?)(?:\s+GIVING\b|\s+REMAINDER\b|\.\s*$|$)",
            stmt, re.IGNORECASE,
        )
        if m_by:
            by_vars = _extract_var_names(m_by.group(1))
            assigned = by_vars
            before_by = stmt[:m_by.start()]
            referenced = _extract_var_names(before_by)
            kw_upper = stmt_type.upper()
            referenced = [v for v in referenced if v != kw_upper]
            referenced.extend(by_vars)

    return StatementRecord(
        line_number=line_number,
        statement_type=stmt_type.upper(),
        assigned_vars=assigned,
        referenced_vars=referenced,
    )


def _analyze_condition_refs(stmt: str) -> list[str]:
    """条件式内の参照変数を抽出する。

    IF, WHEN, UNTIL, 比較演算子を含む文から変数を抽出。
    """
    refs: list[str] = []

    # IF文
    for m in RE_IF.finditer(stmt):
        refs.extend(_extract_var_names(m.group(1)))

    # WHEN句
    for m in RE_WHEN.finditer(stmt):
        refs.extend(_extract_var_names(m.group(1)))

    # UNTIL句
    for m in RE_UNTIL.finditer(stmt):
        refs.extend(_extract_var_names(m.group(1)))

    return refs


def _analyze_single_statement(
    line_number: int, stmt: str,
) -> list[StatementRecord]:
    """単一の文を解析してStatementRecordのリストを返す。

    Args:
        line_number: 文の開始行番号
        stmt: 文テキスト（ピリオド付き）

    Returns:
        StatementRecordのリスト
    """
    upper_stmt = stmt.upper()
    records: list[StatementRecord] = []

    # --- MOVE文 ---
    if "MOVE" in upper_stmt and "TO" in upper_stmt:
        move_records = _analyze_move(stmt, line_number)
        if move_records:
            records.extend(move_records)

    # --- COMPUTE文 ---
    if RE_COMPUTE_KW.search(stmt):
        records.append(_analyze_compute(stmt, line_number))

    # --- 算術文（ADD, SUBTRACT, MULTIPLY, DIVIDE） ---
    for kw in ("ADD", "SUBTRACT", "MULTIPLY", "DIVIDE"):
        pat = re.compile(rf"\b{kw}\b", re.IGNORECASE)
        if pat.search(stmt) and not RE_COMPUTE_KW.search(stmt):
            records.append(
                _analyze_arithmetic(stmt, line_number, kw)
            )
            break  # 1文に1つの算術文のみ

    # --- INITIALIZE文 ---
    m_init = RE_INITIALIZE.search(stmt)
    if m_init:
        init_vars = _extract_var_names(m_init.group(1))
        records.append(StatementRecord(
            line_number=line_number,
            statement_type="INITIALIZE",
            assigned_vars=init_vars,
            referenced_vars=[],
        ))

    # --- ACCEPT文 ---
    m_accept = RE_ACCEPT.search(stmt)
    if m_accept:
        accept_vars = _extract_var_names(m_accept.group(1))
        records.append(StatementRecord(
            line_number=line_number,
            statement_type="ACCEPT",
            assigned_vars=accept_vars,
            referenced_vars=[],
        ))

    # --- READ INTO文 ---
    m_read = RE_READ_INTO.search(stmt)
    if m_read:
        read_vars = _extract_var_names(m_read.group(1))
        records.append(StatementRecord(
            line_number=line_number,
            statement_type="READ",
            assigned_vars=read_vars,
            referenced_vars=[],
        ))

    # --- STRING INTO文 ---
    m_string = RE_STRING_INTO.search(stmt)
    if m_string:
        string_vars = _extract_var_names(m_string.group(1))
        records.append(StatementRecord(
            line_number=line_number,
            statement_type="STRING",
            assigned_vars=string_vars,
            referenced_vars=[],
        ))

    # --- UNSTRING INTO文 ---
    m_unstring = RE_UNSTRING_INTO.search(stmt)
    if m_unstring:
        unstring_vars = _extract_var_names(m_unstring.group(1))
        records.append(StatementRecord(
            line_number=line_number,
            statement_type="UNSTRING",
            assigned_vars=unstring_vars,
            referenced_vars=[],
        ))

    # --- DISPLAY文 ---
    m_display = RE_DISPLAY.search(stmt)
    if m_display:
        display_vars = _extract_var_names(m_display.group(1))
        records.append(StatementRecord(
            line_number=line_number,
            statement_type="DISPLAY",
            assigned_vars=[],
            referenced_vars=display_vars,
        ))

    # --- CALL USING文 ---
    m_call = RE_CALL_USING.search(stmt)
    if m_call:
        call_vars = _extract_var_names(m_call.group(1))
        records.append(StatementRecord(
            line_number=line_number,
            statement_type="CALL",
            assigned_vars=[],
            referenced_vars=call_vars,
        ))

    # --- PERFORM VARYING文 ---
    m_varying = RE_VARYING_VAR.search(stmt)
    if m_varying:
        vary_name = m_varying.group(1).upper()
        if vary_name not in COBOL_KEYWORDS:
            records.append(StatementRecord(
                line_number=line_number,
                statement_type="PERFORM",
                assigned_vars=[vary_name],
                referenced_vars=[],
            ))

    # --- 条件参照変数（IF, WHEN, UNTIL, 比較演算子） ---
    cond_refs = _analyze_condition_refs(stmt)
    if cond_refs:
        records.append(StatementRecord(
            line_number=line_number,
            statement_type="CONDITION",
            assigned_vars=[],
            referenced_vars=cond_refs,
        ))

    return records


def analyze_statements(lines: list[NormalizedLine]) -> list[StatementRecord]:
    """正規化済み論理行からPROCEDURE DIVISIONの文を解析する。

    処理:
    1. PROCEDURE DIVISIONの開始を検出
    2. ピリオド区切りで文を収集
    3. 各文を解析して代入・参照変数を記録

    Args:
        lines: 正規化済みのNormalizedLineリスト

    Returns:
        解析済みのStatementRecordリスト
    """
    # 1. PROCEDURE DIVISION内の文を収集
    statements = _collect_procedure_statements(lines)

    # 2. 各文を解析
    results: list[StatementRecord] = []
    for line_number, stmt in statements:
        records = _analyze_single_statement(line_number, stmt)
        results.extend(records)

    return results
