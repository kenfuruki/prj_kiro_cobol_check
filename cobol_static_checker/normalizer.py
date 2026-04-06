"""正規化エンジン

COBOLソースファイルを読み込み、固定形式の前処理を行う。
- cp932エンコーディングでのファイル読み込み
- 72カラム切り詰めと7カラム目以降の内容抽出
- コメント行（*, /, D, d）の除外
- 継続行（-）の結合処理
- 行番号の保持（継続行は開始行番号）
"""

from cobol_static_checker import NormalizedLine


def _normalize_raw_lines(raw_lines: list[str]) -> list[NormalizedLine]:
    """生の行リストを正規化し、論理行のリストを返す。

    内部関数として、ファイル読み込み済みの行リストを処理する。
    テストやパイプライン内部での利用を想定。

    Args:
        raw_lines: ファイルから読み込んだ生の行リスト

    Returns:
        正規化済みのNormalizedLineリスト
    """
    normalized: list[NormalizedLine] = []

    for i, raw in enumerate(raw_lines, start=1):
        # 改行を除去し、72カラムで切り詰め
        line = raw.rstrip("\r\n")[:72]

        # 7カラム未満の行はスキップ
        if len(line) < 7:
            continue

        # 7カラム目（インデックス6）のインジケータを取得
        indicator = line[6]

        # コメント行を除外（*, /, D, d）
        if indicator in ("*", "/", "D", "d"):
            continue

        # 7カラム目以降の内容を抽出（8カラム目以降 = インデックス7〜）
        content = line[7:72] if len(line) >= 8 else ""

        # 継続行の処理
        if indicator == "-":
            if normalized:
                # 直前の行と結合（直前の末尾空白を除去し、継続行の先頭空白を除去）
                prev = normalized[-1]
                merged_content = prev.content.rstrip() + " " + content.lstrip()
                normalized[-1] = NormalizedLine(
                    line_number=prev.line_number,
                    content=merged_content,
                    is_continuation=True,
                )
            else:
                # 直前の行がない場合はそのまま追加
                normalized.append(
                    NormalizedLine(
                        line_number=i,
                        content=content,
                        is_continuation=False,
                    )
                )
        else:
            # 通常行
            normalized.append(
                NormalizedLine(
                    line_number=i,
                    content=content,
                    is_continuation=False,
                )
            )

    return normalized


def normalize_lines(file_path: str, encoding: str = "cp932") -> list[NormalizedLine]:
    """COBOLソースファイルを正規化し、論理行のリストを返す。

    処理:
    1. ファイルをcp932で読み込み
    2. 各行を72カラムで切り詰め
    3. 7カラム目のインジケータを判定
    4. コメント行（*, /, D, d）を除外
    5. 継続行（-）を直前の行と結合
    6. 7カラム目以降の内容を抽出

    Args:
        file_path: COBOLソースファイルのパス
        encoding: ファイルのエンコーディング（デフォルト: cp932）

    Returns:
        正規化済みのNormalizedLineリスト
    """
    with open(file_path, encoding=encoding, errors="replace") as f:
        raw_lines = f.readlines()

    return _normalize_raw_lines(raw_lines)
