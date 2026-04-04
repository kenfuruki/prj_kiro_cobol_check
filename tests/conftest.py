"""共通フィクスチャとジェネレータ

テスト全体で使用する共通のpytestフィクスチャを定義する。
Hypothesisカスタムジェネレータは各タスクで段階的に追加する。
"""

import pytest

from cobol_static_checker import (
    NormalizedLine,
    StatementRecord,
    VariableDefinition,
    Warning,
)
