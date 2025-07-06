# 日本電波法 XML 取得・正規化スクリプト

e-Gov 法令 API と Japanese Law Translation サイトから Radio Act XML を取得し、UTF-8/LF 正規化を行う Python スクリプトです。

## 🎯 機能

1. **e-Gov 法令 API** から Radio Act (LawID: 325AC0000000131) の ZIP を取得し展開
2. **Japanese Law Translation** サイトの Radio Act 英訳 XML (JLT-XML) を取得
3. 両 XML の文字コードを UTF-8、改行 LF に統一
4. 検証結果を CLI でカラー出力（成功 ✔ / 失敗 ✖ + エラー要約）
5. **差分チェック機能**: 前回のダウンロードと比較して変更を検出
6. **JSON-LD 変換**: XML を ELI 準拠の JSON-LD 形式に変換
7. **SPARQL 検証**: JSON-LD データに対する SPARQL クエリ実行

## 🔧 技術スタック

- **Python** ≥ 3.11
- **外部ライブラリ**:
  - `xmlschema` - XSD 検証
  - `lxml` - XML 処理
  - `requests` - HTTP リクエスト
  - `rich` - カラー出力
  - `pytest` - テスト実行
  - `rdflib` - RDF/SPARQL 処理
  - `pyld` - JSON-LD 処理

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

# 差分チェック機能
python validate_radio_act_xml.py --ja --en --diff

# JSON-LD 変換
python validate_radio_act_xml.py --ja --en --convert-jsonld

# SPARQL テスト実行
python validate_radio_act_xml.py --ja --en --sparql-test
```

### ヘルプ表示

```bash
python validate_radio_act_xml.py --help
```

## 📁 出力ファイル

処理が成功すると、以下のファイルが生成されます：

- `data/RadioAct_ja.xml` - 日本語版 Radio Act XML（UTF-8/LF 正規化済み）
- `data/RadioAct_en.xml` - 英語版 Radio Act XML（UTF-8/LF 正規化済み）
- `data/RadioAct_ja.jsonld` - 日本語版 JSON-LD（ELI 準拠）
- `data/RadioAct_en.jsonld` - 英語版 JSON-LD（ELI 準拠）
- `data/hash_cache.json` - ファイルハッシュキャッシュ（差分チェック用）
- `validation_errors.log` - バリデーションエラーの詳細ログ

## 🔍 差分チェック機能

`--diff` オプションを使用すると、前回のダウンロードと比較して変更を検出します：

```bash
python validate_radio_act_xml.py --ja --en --diff
```

### 差分チェックの動作

1. **最新ファイルのダウンロード**: 現在のソースから最新のXMLファイルを取得
2. **正規化処理**: 文字コードと改行コードを統一
3. **ハッシュ計算**: ファイル内容のハッシュ値を計算
4. **比較**: 前回保存されたハッシュ値と比較
5. **変更検出**: 変更があった場合、詳細な差分情報を表示

### 差分チェックの出力例

```
📊 差分チェック結果:
├── 日本語版: 変更なし (ハッシュ: a1b2c3...)
├── 英語版: 変更あり (ハッシュ: x9y8z7...)
└── 変更詳細:
    - 英語版: 第3条の条文が更新されました
```

## 🧪 テスト実行

```bash
# 全テスト実行
pytest

# 詳細出力でテスト実行
pytest -v

# 特定のテストファイル実行
pytest tests/test_validate_radio_act_xml.py
pytest tests/test_diff_checker.py

# カバレッジ付きテスト実行
pytest --cov=radio_act_validator --cov=diff_checker
```

## 📋 受け入れ基準

- ✅ `python validate_radio_act_xml.py --ja --en` で両ファイルをダウンロード・保存
- ✅ スクリプト実行後、`data/` ディレクトリに UTF-8/LF 正規化済ファイルが存在
- ✅ `file` コマンドで確認しても BOM なし
- ✅ `pytest -q` がグリーン
- ✅ 差分チェック機能が正常に動作
- ✅ JSON-LD 変換が正常に実行される
- ✅ SPARQL クエリが正常に実行される

## 🔍 ファイル構造

```
JP_Radio_Act_jasonld/
├── validate_radio_act_xml.py      # メインスクリプト
├── radio_act_validator.py         # バリデーション機能モジュール
├── diff_checker.py                # 差分チェック機能モジュール
├── eli_converter.py               # JSON-LD 変換モジュール
├── sparql_test.py                 # SPARQL テストスクリプト
├── requirements.txt               # 依存関係
├── README.md                      # このファイル
├── data/                          # 出力ディレクトリ
│   ├── RadioAct_ja.xml           # 日本語版（生成される）
│   ├── RadioAct_en.xml           # 英語版（生成される）
│   ├── RadioAct_ja.jsonld        # 日本語版 JSON-LD（生成される）
│   ├── RadioAct_en.jsonld        # 英語版 JSON-LD（生成される）
│   └── hash_cache.json           # ハッシュキャッシュ（生成される）
├── tests/                         # テストディレクトリ
│   ├── test_validate_radio_act_xml.py
│   └── test_diff_checker.py
└── validation_errors.log         # エラーログ（生成される）
```

## ⚠️ 注意事項

- **英語版 XML URL**: 現在は仮のURLを使用しています。実際の Japanese Law Translation サイトの正確なURLに更新が必要です。
- **XSD スキーマ**: e-Gov 法令 API の実際のスキーマに合わせて調整が必要な場合があります。
- **ネットワーク接続**: インターネット接続が必要です。
- **差分チェック**: 初回実行時は比較対象がないため、すべてのファイルが「新規」として扱われます。

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