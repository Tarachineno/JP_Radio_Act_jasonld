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
EN_XML_URL = "https://www.japaneselawtranslation.go.jp/common/data/law.xml"  # 仮のURL

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
    ZIPファイルを展開し、law.xmlファイルを探します。
    
    Args:
        zip_path: ZIPファイルのパス
        
    Returns:
        law.xmlファイルのパス、見つからない場合はNone
    """
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # law.xmlファイルを探す
            xml_files = [f for f in zip_ref.namelist() if f.endswith('law.xml')]
            
            if not xml_files:
                logger.error("ZIPファイル内にlaw.xmlが見つかりません")
                return None
            
            # 最初に見つかったlaw.xmlを展開
            xml_file = xml_files[0]
            extract_dir = zip_path.parent / "extracted"
            extract_dir.mkdir(exist_ok=True)
            
            zip_ref.extract(xml_file, extract_dir)
            extracted_xml = extract_dir / xml_file
            
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
        # XMLファイルを読み込み
        with open(input_path, 'r', encoding='utf-8') as f:
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


def download_and_validate_japanese(output_dir: Path) -> bool:
    """
    日本語版Radio Act XMLをダウンロード・検証・保存します。
    
    Args:
        output_dir: 出力ディレクトリ
        
    Returns:
        成功時True、失敗時False
    """
    try:
        # 1. e-Gov APIからZIPファイルをダウンロード
        zip_url = f"{EGOV_API_BASE}/lawdata/{RADIO_ACT_LAW_ID}"
        temp_zip = Path(tempfile.gettempdir()) / f"radio_act_{RADIO_ACT_LAW_ID}.zip"
        
        if not download_file(zip_url, temp_zip):
            return False
        
        # 2. ZIPファイルを展開してlaw.xmlを取得
        xml_path = extract_zip_and_find_xml(temp_zip)
        if not xml_path:
            return False
        
        # 3. XSDバリデーション
        xsd_schema = get_egov_xsd_schema()
        is_valid, error_msg = validate_xml_with_xsd(xml_path, xsd_schema)
        
        if not is_valid:
            logger.error(f"XSDバリデーション失敗: {error_msg}")
            return False
        
        # 4. XML正規化・保存
        output_path = output_dir / "RadioAct_ja.xml"
        if not normalize_xml(xml_path, output_path):
            return False
        
        # 5. 一時ファイルのクリーンアップ
        temp_zip.unlink(missing_ok=True)
        xml_path.unlink(missing_ok=True)
        xml_path.parent.rmdir()
        
        return True
        
    except Exception as e:
        logger.exception("日本語版処理中に予期しないエラーが発生")
        return False


def download_and_validate_english(output_dir: Path) -> bool:
    """
    英語版Radio Act XMLをダウンロード・検証・保存します。
    
    Args:
        output_dir: 出力ディレクトリ
        
    Returns:
        成功時True、失敗時False
    """
    try:
        # 1. Japanese Law TranslationサイトからXMLをダウンロード
        temp_xml = Path(tempfile.gettempdir()) / "radio_act_en_temp.xml"
        
        if not download_file(EN_XML_URL, temp_xml):
            return False
        
        # 2. DTDバリデーション
        is_valid, error_msg = validate_xml_with_dtd(temp_xml)
        
        if not is_valid:
            logger.error(f"DTDバリデーション失敗: {error_msg}")
            return False
        
        # 3. XML正規化・保存
        output_path = output_dir / "RadioAct_en.xml"
        if not normalize_xml(temp_xml, output_path):
            return False
        
        # 4. 一時ファイルのクリーンアップ
        temp_xml.unlink(missing_ok=True)
        
        return True
        
    except Exception as e:
        logger.exception("英語版処理中に予期しないエラーが発生")
        return False 