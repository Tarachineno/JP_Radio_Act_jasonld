"""
ELI (European Legislation Identifier) 変換機能

電波法XMLをELIフォーマットに変換し、対訳リンクを付与してJSON-LD形式で出力します。
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin

from lxml import etree
from pyld import jsonld
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, XSD

# 定数
ELI_NS = "http://data.europa.eu/eli/ontology#"
JAPAN_LAW_NS = "http://data.japan.go.jp/law/ontology#"
RADIO_ACT_URI = "http://data.japan.go.jp/law/radio-act/1950/131"

# 名前空間
ELI = Namespace(ELI_NS)
JAPAN_LAW = Namespace(JAPAN_LAW_NS)

logger = logging.getLogger(__name__)


class ELIConverter:
    """ELI変換クラス"""
    
    def __init__(self):
        self.japanese_xml: Optional[etree._Element] = None
        self.english_xml: Optional[etree._Element] = None
        self.structured_xml: Optional[etree._Element] = None
        
    def load_xml_files(self, ja_path: Path, en_path: Path) -> bool:
        """
        XMLファイルを読み込みます。
        
        Args:
            ja_path: 日本語版XMLファイルのパス
            en_path: 英語版XMLファイルのパス
            
        Returns:
            成功時True、失敗時False
        """
        try:
            # 日本語版XML読み込み
            self.japanese_xml = etree.parse(str(ja_path)).getroot()
            logger.info(f"日本語版XML読み込み完了: {ja_path}")
            
            # 英語版XML読み込み
            self.english_xml = etree.parse(str(en_path)).getroot()
            logger.info(f"英語版XML読み込み完了: {en_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"XMLファイル読み込みに失敗: {e}")
            return False
    
    def create_structured_xml(self) -> bool:
        """
        XSLT ①: e-Gov法令XMLを構造保持XMLに変換します。
        
        Returns:
            成功時True、失敗時False
        """
        try:
            # 簡易的な構造保持XMLを作成
            # 実際の実装では、より詳細なXSLT変換が必要
            
            root = etree.Element("RadioAct", {
                "xmlns": "http://data.japan.go.jp/law/radio-act",
                "version": "1.0",
                "lang": "ja"
            })
            
            # メタデータ
            metadata = etree.SubElement(root, "Metadata")
            etree.SubElement(metadata, "LawID").text = "325AC0000000131"
            etree.SubElement(metadata, "LawName").text = "電波法"
            etree.SubElement(metadata, "EnactmentDate").text = "1950-05-02"
            etree.SubElement(metadata, "LawNumber").text = "昭和25年法律第131号"
            
            # 条文構造
            articles = etree.SubElement(root, "Articles")
            
            # 日本語版XMLから条文を抽出
            if self.japanese_xml is not None:
                self._extract_articles_from_japanese(articles)
            
            self.structured_xml = root
            logger.info("構造保持XML作成完了")
            return True
            
        except Exception as e:
            logger.error(f"構造保持XML作成に失敗: {e}")
            return False
    
    def _extract_articles_from_japanese(self, articles_elem: etree._Element) -> None:
        """日本語版XMLから条文を抽出します。"""
        try:
            # 実際のXML構造に合わせて調整
            # Article要素を探す
            article_elements = self.japanese_xml.xpath("//Article[@Num]")
            
            if not article_elements:
                logger.warning("Article要素が見つかりません")
                return
            
            logger.info(f"条文数: {len(article_elements)}")
            
            for article in article_elements:
                article_num = article.get("Num")
                if not article_num:
                    continue
                
                article_elem = etree.SubElement(articles_elem, "Article", {
                    "id": f"art_{article_num}",
                    "number": article_num
                })
                
                # 条文番号
                number_elem = etree.SubElement(article_elem, "Number")
                number_elem.text = article_num
                
                # 条文タイトル（ArticleTitle要素から取得）
                title_elem = article.find(".//ArticleTitle")
                if title_elem is not None and title_elem.text:
                    title_elem_xml = etree.SubElement(article_elem, "Title")
                    title_elem_xml.text = title_elem.text.strip()
                else:
                    # デフォルトタイトル
                    title_elem_xml = etree.SubElement(article_elem, "Title")
                    title_elem_xml.text = f"第{article_num}条"
                
                # 条文内容（Sentence要素から取得）
                sentences = article.xpath(".//Sentence")
                if sentences:
                    content_elem = etree.SubElement(article_elem, "Content")
                    # 改行を保持して結合
                    content_parts = []
                    for sentence in sentences:
                        if sentence.text:
                            content_parts.append(sentence.text.strip())
                    content_elem.text = "\n".join(content_parts)
                else:
                    # フォールバック: 条文全体のテキスト
                    content_elem = etree.SubElement(article_elem, "Content")
                    content_text = " ".join([t.strip() for t in article.xpath(".//text()") if t.strip()])
                    content_elem.text = content_text
                
                # 英語対訳のプレースホルダー
                translation_elem = etree.SubElement(article_elem, "Translation", {
                    "lang": "en",
                    "status": "pending"
                })
                translation_elem.text = f"Article {article_num} - English translation"
                
        except Exception as e:
            logger.error(f"条文抽出に失敗: {e}")
    
    def add_translation_links(self) -> bool:
        """
        対訳リンク付与: 英訳XMLと対訳リンクを付与します。
        
        Returns:
            成功時True、失敗時False
        """
        try:
            if self.structured_xml is None:
                logger.error("構造保持XMLが作成されていません")
                return False
            
            # 英語版XMLから対訳を抽出してリンクを付与
            if self.english_xml is not None:
                self._link_english_translations()
            
            logger.info("対訳リンク付与完了")
            return True
            
        except Exception as e:
            logger.error(f"対訳リンク付与に失敗: {e}")
            return False
    
    def _link_english_translations(self) -> None:
        """英語対訳をリンクします。"""
        try:
            if self.english_xml is None:
                logger.warning("英語版XMLが読み込まれていません")
                return
            
            # 英語版から条文を抽出
            english_articles = {}
            article_elements = self.english_xml.xpath("//Article[@Num]")
            
            for article in article_elements:
                article_num = article.get("Num")
                if not article_num:
                    continue
                
                # 条文タイトル
                title_elem = article.find(".//ArticleTitle")
                title = title_elem.text if title_elem is not None else f"Article {article_num}"
                
                # 条文内容
                sentences = article.xpath(".//ParagraphSentence//Sentence")
                content_parts = []
                for sentence in sentences:
                    if sentence.text:
                        content_parts.append(sentence.text.strip())
                
                english_articles[article_num] = {
                    "title": title,
                    "content": "\n".join(content_parts)
                }
            
            # 構造保持XMLの条文に対訳を追加
            for article_elem in self.structured_xml.xpath("//Article"):
                article_number = article_elem.get("number")
                translation_elem = article_elem.find("Translation[@lang='en']")
                
                if article_number in english_articles and translation_elem is not None:
                    english_data = english_articles[article_number]
                    translation_elem.set("status", "completed")
                    translation_elem.text = english_data["content"]
                    
                    # タイトルも更新
                    title_elem = article_elem.find("Title")
                    if title_elem is not None:
                        title_elem.set("en", english_data["title"])
            
            logger.info(f"英語対訳リンク完了: {len(english_articles)}条文")
            
        except Exception as e:
            logger.error(f"英語対訳リンクに失敗: {e}")
    
    def convert_to_json_ld(self) -> Optional[Dict]:
        """
        XSLT ②: 構造保持XMLをJSON-LD (ELI+schema) に変換します。
        
        Returns:
            JSON-LD形式の辞書、失敗時None
        """
        try:
            if self.structured_xml is None:
                logger.error("構造保持XMLが作成されていません")
                return None
            
            # XMLからメタデータを抽出
            metadata = self._extract_metadata_from_xml()
            
            # サンプルに合わせた詳細ELIメタデータ
            json_ld = {
                "@context": {
                    "@vocab": ELI_NS,
                    "eli": ELI_NS,
                    "japan_law": JAPAN_LAW_NS,
                    "rdfs": str(RDFS),
                    "xsd": str(XSD)
                },
                "@id": RADIO_ACT_URI,
                "@type": "eli:LegalResource",
                "eli:title": {
                    "@language": "ja",
                    "@value": metadata["law_name"]
                },
                "eli:title_alternative": {
                    "@language": "en",
                    "@value": metadata["law_name_en"]
                },
                "eli:date_document": {"@value": metadata["enactment_date"], "@type": "xsd:date"},
                "eli:date_version": {"@value": metadata["date_version"], "@type": "xsd:date"},
                "eli:version": metadata["version"],
                "eli:valid": metadata["valid"],
                "eli:passed_by": metadata["passed_by"],
                "eli:publisher": metadata["publisher"],
                "eli:type_document": metadata["document_type"],
                "eli:number": "131",  # 法令番号のみ
                "eli:language": ["ja", "en"],
                "eli:is_about": "radio spectrum management",
                "eli:has_part": self._extract_articles_json_ld()
            }
            
            logger.info("JSON-LD変換完了")
            return json_ld
            
        except Exception as e:
            logger.error(f"JSON-LD変換に失敗: {e}")
            return None
    
    def _extract_articles_json_ld(self) -> List[Dict]:
        """条文をJSON-LD形式で抽出します。"""
        articles = []
        
        try:
            article_elements = self.structured_xml.xpath("//Article")
            
            for article_elem in article_elements:
                article_id = article_elem.get("id")
                article_number = article_elem.get("number")
                
                # 条文タイトルを取得
                title_elem = article_elem.find("Title")
                title = title_elem.text if title_elem is not None else f"第{article_number}条"
                
                # 条文内容を取得
                content_elem = article_elem.find("Content")
                content = content_elem.text if content_elem is not None else ""
                
                # 英語対訳を取得
                translation_elem = article_elem.find("Translation[@lang='en']")
                translation = translation_elem.text if translation_elem is not None else ""
                
                article_json = {
                    "@id": f"{RADIO_ACT_URI}#{article_id}",
                    "@type": "eli:LegalResourceSubdivision",
                    "eli:division_type": "article",
                    "eli:number": article_number,
                    "eli:title": {
                        "@language": "ja",
                        "@value": title
                    },
                    "eli:content": {
                        "@language": "ja",
                        "@value": content
                    },
                    "eli:has_language_version": [
                        {
                            "@type": "eli:LanguageVersion",
                            "eli:language": "ja",
                            "eli:content": content
                        },
                        {
                            "@type": "eli:LanguageVersion",
                            "eli:language": "en",
                            "eli:content": translation
                        }
                    ]
                }
                
                articles.append(article_json)
                
        except Exception as e:
            logger.error(f"条文JSON-LD抽出に失敗: {e}")
        
        return articles
    
    def save_json_ld(self, json_ld: Dict, output_path: Path) -> bool:
        """
        JSON-LDをファイルに保存します。
        
        Args:
            json_ld: JSON-LD形式の辞書
            output_path: 出力ファイルパス
            
        Returns:
            成功時True、失敗時False
        """
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(json_ld, f, ensure_ascii=False, indent=2)
            
            logger.info(f"JSON-LD保存完了: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"JSON-LD保存に失敗: {e}")
            return False
    
    def save_structured_xml(self, output_path: Path) -> bool:
        """
        構造保持XMLをファイルに保存します。
        
        Args:
            output_path: 出力ファイルパス
            
        Returns:
            成功時True、失敗時False
        """
        try:
            if self.structured_xml is None:
                logger.error("構造保持XMLが作成されていません")
                return False
            
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 整形して保存
            tree = etree.ElementTree(self.structured_xml)
            tree.write(str(output_path), encoding='utf-8', pretty_print=True, xml_declaration=True)
            
            logger.info(f"構造保持XML保存完了: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"構造保持XML保存に失敗: {e}")
            return False

    def _extract_metadata_from_xml(self) -> Dict[str, str]:
        """XMLからメタデータを抽出します。"""
        metadata = {
            "law_id": "325AC0000000131",
            "law_name": "電波法",
            "law_name_en": "Radio Act",
            "enactment_date": "1950-05-02",
            "law_number": "昭和25年法律第131号",
            "version": "20240801",
            "date_version": "2024-08-01",
            "valid": "1950-05-02/9999-12-31",
            "passed_by": "National Diet of Japan",
            "publisher": "Ministry of Internal Affairs and Communications",
            "document_type": "Act"
        }
        
        try:
            # 日本語版XMLからメタデータを抽出
            if self.japanese_xml is not None:
                # Law要素の属性から抽出
                law_elem = self.japanese_xml.find(".//Law")
                if law_elem is not None:
                    # 制定日
                    year = law_elem.get("Year", "25")
                    month = law_elem.get("PromulgateMonth", "05")
                    day = law_elem.get("PromulgateDay", "02")
                    era = law_elem.get("Era", "Showa")
                    
                    # 昭和25年を西暦1950年に変換
                    if era == "Showa":
                        western_year = 1925 + int(year)
                    else:
                        western_year = int(year)
                    
                    metadata["enactment_date"] = f"{western_year}-{month.zfill(2)}-{day.zfill(2)}"
                    metadata["valid"] = f"{western_year}-{month.zfill(2)}-{day.zfill(2)}/9999-12-31"
                
                # 法令番号
                law_num_elem = self.japanese_xml.find(".//LawNum")
                if law_num_elem is not None and law_num_elem.text:
                    metadata["law_number"] = law_num_elem.text.strip()
                
                # 法令名
                law_title_elem = self.japanese_xml.find(".//LawTitle")
                if law_title_elem is not None and law_title_elem.text:
                    metadata["law_name"] = law_title_elem.text.strip()
            
            # 英語版XMLからメタデータを抽出
            if self.english_xml is not None:
                # 英語法令名
                law_title_en_elem = self.english_xml.find(".//LawTitle")
                if law_title_en_elem is not None and law_title_en_elem.text:
                    metadata["law_name_en"] = law_title_en_elem.text.strip()
                
                # 英語版の制定日
                original_date = self.english_xml.get("OriginalPromulgateDate")
                if original_date:
                    # "May 2, 1950" 形式を "1950-05-02" に変換
                    try:
                        from datetime import datetime
                        date_obj = datetime.strptime(original_date, "%B %d, %Y")
                        metadata["enactment_date"] = date_obj.strftime("%Y-%m-%d")
                        metadata["valid"] = f"{date_obj.strftime('%Y-%m-%d')}/9999-12-31"
                    except ValueError:
                        pass
            
            logger.info(f"メタデータ抽出完了: {metadata}")
            
        except Exception as e:
            logger.error(f"メタデータ抽出に失敗: {e}")
        
        return metadata


def convert_to_eli(ja_xml_path: Path, en_xml_path: Path, output_dir: Path) -> bool:
    """
    電波法XMLをELI形式に変換します。
    
    Args:
        ja_xml_path: 日本語版XMLファイルのパス
        en_xml_path: 英語版XMLファイルのパス
        output_dir: 出力ディレクトリ
        
    Returns:
        成功時True、失敗時False
    """
    try:
        converter = ELIConverter()
        
        # 1. XMLファイル読み込み
        if not converter.load_xml_files(ja_xml_path, en_xml_path):
            return False
        
        # 2. XSLT ①: 構造保持XML作成
        if not converter.create_structured_xml():
            return False
        
        # 3. 対訳リンク付与
        if not converter.add_translation_links():
            return False
        
        # 4. 構造保持XML保存
        structured_xml_path = output_dir / "RadioAct_structured.xml"
        if not converter.save_structured_xml(structured_xml_path):
            return False
        
        # 5. XSLT ②: JSON-LD変換
        json_ld = converter.convert_to_json_ld()
        if json_ld is None:
            return False
        
        # 6. JSON-LD保存
        json_ld_path = output_dir / "RadioAct_eli.jsonld"
        if not converter.save_json_ld(json_ld, json_ld_path):
            return False
        
        return True
        
    except Exception as e:
        logger.exception("ELI変換中に予期しないエラーが発生")
        return False 