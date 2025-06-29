# 日本電波法 XML 取得・正規化スクリプト

e-Gov 法令 API と Japanese Law Translation サイトから Radio Act XML を取得し、UTF-8/LF 正規化を行う Python スクリプトです。

## 🎯 機能

1. **e-Gov 法令 API** から Radio Act (LawID: 325AC0000000131) の ZIP を取得し展開
2. **Japanese Law Translation** サイトの Radio Act 英訳 XML (JLT-XML) を取得
3. 両 XML の文字コードを UTF-8、改行 LF に統一
4. 検証結果を CLI でカラー出力（成功 ✔ / 失敗 ✖ + エラー要約）

## 🔧 技術スタック

- **Python** ≥ 3.11
- **外部ライブラリ**:
  - `xmlschema` - XSD 検証
  - `lxml` - XML 処理
  - `requests` - HTTP リクエスト
  - `rich` - カラー出力
  - `pytest` - テスト実行

## 📦 インストール

```bash
# 仮想環境の作成とアクティベート
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 依存関係のインストール
pip install --upgrade pip
pip install -r requirements.txt
```

## 🚀 使用方法

### 基本的な使用方法

```bash
# 両方のファイルを処理
python validate_radio_act_xml.py --ja --en

# 日本語版のみ
python validate_radio_act_xml.py --ja

# 英語版のみ
python validate_radio_act_xml.py --en

# 詳細ログ出力
python validate_radio_act_xml.py --ja --en --verbose

# カスタム出力ディレクトリ
python validate_radio_act_xml.py --ja --en --output-dir ./custom_data
```

### ヘルプ表示

```bash
python validate_radio_act_xml.py --help
```

## 📁 出力ファイル

処理が成功すると、以下のファイルが生成されます：

- `data/RadioAct_ja.xml` - 日本語版 Radio Act XML（UTF-8/LF 正規化済み）
- `data/RadioAct_en.xml` - 英語版 Radio Act XML（UTF-8/LF 正規化済み）
- `validation_errors.log` - バリデーションエラーの詳細ログ

## 🧪 テスト実行

```bash
# 全テスト実行
pytest

# 詳細出力でテスト実行
pytest -v

# 特定のテストファイル実行
pytest tests/test_validate_radio_act_xml.py

# カバレッジ付きテスト実行
pytest --cov=radio_act_validator
```

## 📋 受け入れ基準

- ✅ `python validate_radio_act_xml.py --ja --en` で両ファイルをダウンロード・保存
- ✅ スクリプト実行後、`data/` ディレクトリに UTF-8/LF 正規化済ファイルが存在
- ✅ `file` コマンドで確認しても BOM なし
- ✅ `pytest -q` がグリーン

## 🔍 ファイル構造

```
JP_Radio_Act_jasonld/
├── validate_radio_act_xml.py      # メインスクリプト
├── radio_act_validator.py         # バリデーション機能モジュール
├── requirements.txt               # 依存関係
├── README.md                      # このファイル
├── data/                          # 出力ディレクトリ
│   ├── RadioAct_ja.xml           # 日本語版（生成される）
│   └── RadioAct_en.xml           # 英語版（生成される）
├── tests/                         # テストディレクトリ
│   └── test_validate_radio_act_xml.py
└── validation_errors.log         # エラーログ（生成される）
```

## ⚠️ 注意事項

- **英語版 XML URL**: 現在は仮のURLを使用しています。実際の Japanese Law Translation サイトの正確なURLに更新が必要です。
- **XSD スキーマ**: e-Gov 法令 API の実際のスキーマに合わせて調整が必要な場合があります。
- **ネットワーク接続**: インターネット接続が必要です。

## 🤝 貢献

1. このリポジトリをフォーク
2. 機能ブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

## 📄 ライセンス

このプロジェクトは MIT ライセンスの下で公開されています。

## 🐛 問題報告

バグや機能要求がある場合は、GitHub の Issues で報告してください。 