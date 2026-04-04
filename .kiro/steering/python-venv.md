---
inclusion: auto
---

# Steering: Python仮想環境の管理

## 目的
Pythonプロジェクトの構築時に、仮想環境（venv）を必ず使用し、プロジェクト固有の依存関係を隔離する。

## ルール

### 1. 仮想環境の確認と作成
- Pythonプロジェクトのセットアップやライブラリインストールを行う前に、ワークスペースルートに `.venv` ディレクトリが存在するか確認する
- `.venv` が存在しない場合は、`python -m venv .venv` で仮想環境を作成する
- 仮想環境の作成後、必ずアクティベートしてからライブラリをインストールする

### 2. ライブラリのインストール
- `pip install` は必ず仮想環境内で実行する
- Windows環境では `.venv/Scripts/pip` を使用する
- Linux/Mac環境では `.venv/bin/pip` を使用する
- `requirements.txt` がある場合は `.venv/Scripts/pip install -r requirements.txt`（Windows）で一括インストールする

### 3. コマンド実行時の注意
- Pythonスクリプトの実行やテストの実行も仮想環境内で行う
- Windows: `.venv/Scripts/python`、`.venv/Scripts/pytest` 等を使用する
- Linux/Mac: `.venv/bin/python`、`.venv/bin/pytest` 等を使用する
