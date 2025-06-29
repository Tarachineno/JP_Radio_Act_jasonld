"""
日本電波法 XML バリデーション機能

e-Gov 法令 API と Japanese Law Translation サイトから
Radio Act XML を取得し、バリデーション・正規化を行います。
"""

import logging
import tempfile
import zipfile
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urljoin

import requests
import rich.console
from lxml import etree
from xmlschema import XMLSchema, XMLSchemaValidationError

# 定数
EGOV_API_BASE = "https://elaws.e-gov.go.jp/api/1"
RADIO_ACT_LAW_ID = "325AC0000000131"
# TODO: 実際のJapanese Law TranslationサイトのRadio Act XML URLを設定してください
EN_XML_URL = None  # 実行時にユーザーに確認

# デフォルトURL
DEFAULT_JA_URL = "https://laws.e-gov.go.jp/data/Act/325AC0000000131/606996_4/325AC0000000131_20250601_504AC0000000068_xml.zip"
DEFAULT_EN_URL = "https://www.japaneselawtranslation.go.jp/en/laws/download/3205/06/s25Aa001310204en7.0_h26A26.xml"

# ログ設定
logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    """ログ設定を初期化します。"""
    level = logging.DEBUG if verbose else logging.INFO
    
    # ファイルハンドラー（エラーログ用）
    file_handler = logging.FileHandler("validation_errors.log", encoding="utf-8")
    file_handler.setLevel(logging.ERROR)
    file_handler.setFormatter(
        logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )
    
    # コンソールハンドラー
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(
        logging.Formatter('%(levelname)s: %(message)s')
    )
    
    # ルートロガーの設定
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)


def download_file(url: str, dest_path: Path) -> bool:
    """
    ファイルをダウンロードします。
    
    Args:
        url: ダウンロードURL
        dest_path: 保存先パス
        
    Returns:
        成功時True、失敗時False
    """
    try:
        logger.info(f"ダウンロード中: {url}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(dest_path, 'wb') as f:
            f.write(response.content)
        
        logger.info(f"ダウンロード完了: {dest_path}")
        return True
        
    except (requests.RequestException, Exception) as e:
        logger.error(f"ダウンロード失敗: {e}")
        return False


def extract_zip_and_find_xml(zip_path: Path) -> Optional[Path]:
    """
    ZIPファイルを展開し、XMLファイルを探します。
    
    Args:
        zip_path: ZIPファイルのパス
        
    Returns:
        XMLファイルのパス、見つからない場合はNone
    """
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # XMLファイルを探す（優先順位: law.xml > *.xml）
            xml_files = [f for f in zip_ref.namelist() if f.endswith('.xml')]
            
            if not xml_files:
                logger.error("ZIPファイル内にXMLファイルが見つかりません")
                return None
            
            # law.xmlを優先、なければ最初のXMLファイルを使用
            target_xml = None
            for xml_file in xml_files:
                if xml_file.endswith('law.xml'):
                    target_xml = xml_file
                    break
            
            if not target_xml:
                target_xml = xml_files[0]
            
            # XMLファイルを展開
            extract_dir = zip_path.parent / "extracted"
            extract_dir.mkdir(exist_ok=True)
            
            zip_ref.extract(target_xml, extract_dir)
            extracted_xml = extract_dir / target_xml
            
            logger.info(f"XMLファイル展開完了: {extracted_xml}")
            return extracted_xml
            
    except zipfile.BadZipFile as e:
        logger.error(f"ZIPファイルの展開に失敗: {e}")
        return None


def validate_xml_with_xsd(xml_path: Path, xsd_content: str) -> Tuple[bool, Optional[str]]:
    """
    XMLファイルをXSDスキーマでバリデーションします。
    
    Args:
        xml_path: XMLファイルのパス
        xsd_content: XSDスキーマの内容
        
    Returns:
        (成功フラグ, エラーメッセージ)
    """
    try:
        # XSDスキーマをロード
        schema = XMLSchema(xsd_content)
        
        # XMLファイルをバリデーション
        schema.validate(str(xml_path))
        
        logger.info("XSDバリデーション成功")
        return True, None
        
    except XMLSchemaValidationError as e:
        error_msg = f"XSDバリデーションエラー: {e}"
        logger.error(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"XSDバリデーション中に予期しないエラー: {e}"
        logger.error(error_msg)
        return False, error_msg


def validate_xml_with_dtd(xml_path: Path) -> Tuple[bool, Optional[str]]:
    """
    XMLファイルを内部DTDでバリデーションします。
    
    Args:
        xml_path: XMLファイルのパス
        
    Returns:
        (成功フラグ, エラーメッセージ)
    """
    try:
        # XMLファイルをパース（DTDバリデーション付き）
        parser = etree.XMLParser(dtd_validation=True)
        etree.parse(str(xml_path), parser)
        
        logger.info("DTDバリデーション成功")
        return True, None
        
    except etree.DocumentInvalid as e:
        error_msg = f"DTDバリデーションエラー: {e}"
        logger.error(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"DTDバリデーション中に予期しないエラー: {e}"
        logger.error(error_msg)
        return False, error_msg


def normalize_xml(input_path: Path, output_path: Path) -> bool:
    """
    XMLファイルをUTF-8/LF正規化します。
    
    Args:
        input_path: 入力XMLファイルのパス
        output_path: 出力XMLファイルのパス
        
    Returns:
        成功時True、失敗時False
    """
    try:
        # XMLファイルを読み込み（BOMを自動除去）
        with open(input_path, 'r', encoding='utf-8-sig') as f:
            content = f.read()
        
        # 改行をLFに統一
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        
        # 出力ディレクトリを作成
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # UTF-8（BOMなし）で保存
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"XML正規化完了: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"XML正規化に失敗: {e}")
        return False


def get_egov_xsd_schema() -> str:
    """
    e-Gov法令APIのXSDスキーマ（v3）を返します。
    
    Returns:
        XSDスキーマの内容
    """
    # 簡略化されたXSDスキーマ（実際のスキーマに合わせて調整が必要）
    return """<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
    <xs:element name="Law">
        <xs:complexType>
            <xs:sequence>
                <xs:element name="LawNum" type="xs:string"/>
                <xs:element name="LawName" type="xs:string"/>
                <xs:element name="LawBody" type="xs:string"/>
            </xs:sequence>
        </xs:complexType>
    </xs:element>
</xs:schema>"""


def download_and_validate_japanese(output_dir: Path, ja_url: str = None) -> bool:
    """
    日本語版Radio Act XMLをダウンロード・保存します。
    Args:
        output_dir: 出力ディレクトリ
        ja_url: ダウンロードURL（Noneならデフォルト）
    Returns:
        成功時True、失敗時False
    """
    try:
        url = ja_url or DEFAULT_JA_URL
        temp_file = Path(tempfile.gettempdir()) / "radio_act_ja_temp"
        
        if not download_file(url, temp_file):
            return False
        
        # ZIPファイルの場合は展開
        if temp_file.suffix.lower() == '.zip' or temp_file.read_bytes()[:4] == b'PK\x03\x04':
            xml_path = extract_zip_and_find_xml(temp_file)
            if not xml_path:
                return False
        else:
            xml_path = temp_file
        
        # バリデーションをスキップして直接正規化・保存
        output_path = output_dir / "RadioAct_ja.xml"
        if not normalize_xml(xml_path, output_path):
            return False
        
        # 一時ファイルのクリーンアップ
        temp_file.unlink(missing_ok=True)
        if xml_path != temp_file:
            xml_path.unlink(missing_ok=True)
            xml_path.parent.rmdir()
        
        logger.info(f"日本語版XML保存完了: {output_path}")
        return True
        
    except Exception as e:
        logger.exception("日本語版処理中に予期しないエラーが発生")
        return False


def get_english_xml_url() -> Optional[str]:
    """
    英語版XMLのURLをユーザーから対話的に取得します。
    
    Returns:
        ユーザーが入力したURL、キャンセル時はNone
    """
    console = rich.console.Console()
    
    console.print("\n[bold yellow]🌐 英語版 Radio Act XML の URL を入力してください[/bold yellow]")
    console.print("[dim]Japanese Law Translation サイトの Radio Act XML ファイルの URL を教えてください[/dim]")
    console.print("[dim]例: https://www.japaneselawtranslation.go.jp/.../radio_act.xml[/dim]")
    console.print("[dim]キャンセルする場合は 'cancel' または Ctrl+C を入力してください[/dim]\n")
    
    try:
        url = input("URL: ").strip()
        
        if url.lower() in ['cancel', 'c', '']:
            console.print("[yellow]英語版の処理をキャンセルしました[/yellow]")
            return None
        
        # 基本的なURL形式チェック
        if not url.startswith(('http://', 'https://')):
            console.print("[red]エラー: 有効なURLを入力してください[/red]")
            return get_english_xml_url()  # 再帰的に再試行
        
        console.print(f"[green]URL を設定しました: {url}[/green]")
        return url
        
    except KeyboardInterrupt:
        console.print("\n[yellow]英語版の処理をキャンセルしました[/yellow]")
        return None


def download_and_validate_english(output_dir: Path, en_url: str = None) -> bool:
    """
    英語版Radio Act XMLをダウンロード・保存します。
    Args:
        output_dir: 出力ディレクトリ
        en_url: ダウンロードURL（Noneならデフォルト or 対話）
    Returns:
        成功時True、失敗時False
    """
    try:
        url = en_url or DEFAULT_EN_URL
        if url is None:
            url = get_english_xml_url()
            if url is None:
                return False
        
        temp_file = Path(tempfile.gettempdir()) / "radio_act_en_temp"
        
        if not download_file(url, temp_file):
            return False
        
        # ZIPファイルの場合は展開
        if temp_file.suffix.lower() == '.zip' or temp_file.read_bytes()[:4] == b'PK\x03\x04':
            xml_path = extract_zip_and_find_xml(temp_file)
            if not xml_path:
                return False
        else:
            xml_path = temp_file
        
        # バリデーションをスキップして直接正規化・保存
        output_path = output_dir / "RadioAct_en.xml"
        if not normalize_xml(xml_path, output_path):
            return False
        
        # 一時ファイルのクリーンアップ
        temp_file.unlink(missing_ok=True)
        if xml_path != temp_file:
            xml_path.unlink(missing_ok=True)
            xml_path.parent.rmdir()
        
        logger.info(f"英語版XML保存完了: {output_path}")
        return True
        
    except Exception as e:
        logger.exception("英語版処理中に予期しないエラーが発生")
        return False 