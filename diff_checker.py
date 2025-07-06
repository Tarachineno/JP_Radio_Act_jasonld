#!/usr/bin/env python3
"""
法規データソース差分確認モジュール

e-GovとJapanese Law Translationから最新のデータをダウンロードし、
既存のデータと比較して差分を検出する機能を提供します。
"""

import os
import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
import requests
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
import xml.etree.ElementTree as ET
from xml.dom import minidom

console = Console()


@dataclass
class DiffResult:
    """差分検出結果を格納するデータクラス"""
    source: str
    timestamp: str
    has_changes: bool
    old_hash: Optional[str]
    new_hash: Optional[str]
    changes: List[str]
    error: Optional[str] = None


class LawDiffChecker:
    """法規データソースの差分確認クラス"""
    
    def __init__(self, data_dir: str = "data", cache_file: str = "diff_cache.json"):
        self.data_dir = Path(data_dir)
        self.cache_file = self.data_dir / cache_file
        self.data_dir.mkdir(exist_ok=True)
        
        # ログ設定
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('diff_checker.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # キャッシュ読み込み
        self.cache = self._load_cache()
    
    def _load_cache(self) -> Dict[str, Any]:
        """キャッシュファイルを読み込む"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"キャッシュファイルの読み込みに失敗: {e}")
        return {}
    
    def _save_cache(self):
        """キャッシュファイルに保存"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"キャッシュファイルの保存に失敗: {e}")
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """ファイルのハッシュ値を計算"""
        if not file_path.exists():
            return ""
        
        hash_md5 = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def _download_file(self, url: str, filename: str) -> Optional[Path]:
        """ファイルをダウンロード"""
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            file_path = self.data_dir / filename
            
            # ZIPファイルの場合
            if url.endswith('.zip'):
                import zipfile
                import io
                
                with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
                    # law.xmlを探す
                    xml_files = [f for f in zip_file.namelist() if f.endswith('.xml')]
                    if xml_files:
                        with zip_file.open(xml_files[0]) as xml_file:
                            with open(file_path, 'wb') as f:
                                f.write(xml_file.read())
                    else:
                        self.logger.error(f"ZIPファイル内にXMLファイルが見つかりません: {url}")
                        return None
            else:
                with open(file_path, 'wb') as f:
                    f.write(response.content)
            
            self.logger.info(f"ダウンロード完了: {filename}")
            return file_path
            
        except Exception as e:
            self.logger.error(f"ダウンロード失敗 {url}: {e}")
            return None
    
    def _normalize_xml(self, file_path: Path) -> Path:
        """XMLファイルを正規化"""
        try:
            # XMLをパースして再構築
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # 美しい形式で出力
            xml_str = minidom.parseString(ET.tostring(root, encoding='unicode')).toprettyxml(
                indent="  ", encoding='utf-8'
            )
            
            # BOMを除去してLFに統一
            xml_str = xml_str.replace(b'\xef\xbb\xbf', b'')  # BOM除去
            xml_str = xml_str.replace(b'\r\n', b'\n')  # CRLF → LF
            
            # test.xml → test.normalized.xml
            normalized_path = file_path.with_name(file_path.stem + '.normalized' + file_path.suffix)
            with open(normalized_path, 'wb') as f:
                f.write(xml_str)
            
            return normalized_path
            
        except Exception as e:
            self.logger.error(f"XML正規化失敗 {file_path}: {e}")
            return file_path
    
    def _extract_metadata(self, file_path: Path) -> Dict[str, Any]:
        """XMLファイルからメタデータを抽出"""
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            metadata = {}
            
            # 基本的なメタデータを抽出
            for elem in root.iter():
                if elem.tag.endswith('LawNum'):
                    metadata['law_number'] = elem.text
                elif elem.tag.endswith('LawName'):
                    metadata['law_name'] = elem.text
                elif elem.tag.endswith('EnactDate'):
                    metadata['enact_date'] = elem.text
                elif elem.tag.endswith('EnforcementDate'):
                    metadata['enforcement_date'] = elem.text
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"メタデータ抽出失敗 {file_path}: {e}")
            return {}
    
    def check_japanese_law_diff(self, url: str) -> DiffResult:
        """日本語法規の差分を確認"""
        self.logger.info("日本語法規の差分確認を開始")
        
        result = DiffResult(
            source="Japanese Law",
            timestamp=datetime.now().isoformat(),
            has_changes=False,
            old_hash=None,
            new_hash=None,
            changes=[],
            error=None
        )
        
        try:
            # 既存ファイルのハッシュを取得
            existing_file = self.data_dir / "RadioAct_ja.xml"
            if existing_file.exists():
                result.old_hash = self._calculate_file_hash(existing_file)
            
            # 最新ファイルをダウンロード
            temp_file = self._download_file(url, "RadioAct_ja_temp.xml")
            if not temp_file:
                result.error = "ダウンロードに失敗"
                return result
            
            # 正規化
            normalized_temp = self._normalize_xml(temp_file)
            result.new_hash = self._calculate_file_hash(normalized_temp)
            
            # 差分確認
            if result.old_hash and result.new_hash:
                if result.old_hash != result.new_hash:
                    result.has_changes = True
                    result.changes.append("ハッシュ値が変更されました")
                    
                    # メタデータの差分も確認
                    old_metadata = {}
                    if existing_file.exists():
                        old_metadata = self._extract_metadata(existing_file)
                    
                    new_metadata = self._extract_metadata(normalized_temp)
                    
                    # メタデータの差分を検出
                    for key in set(old_metadata.keys()) | set(new_metadata.keys()):
                        if old_metadata.get(key) != new_metadata.get(key):
                            result.changes.append(f"メタデータ '{key}' が変更: {old_metadata.get(key)} → {new_metadata.get(key)}")
                else:
                    result.changes.append("変更なし")
            else:
                result.changes.append("初回ダウンロード")
            
            # 成功した場合はファイルを置き換え
            if not result.error:
                if existing_file.exists():
                    existing_file.unlink()
                normalized_temp.rename(existing_file)
                temp_file.unlink(missing_ok=True)
            
        except Exception as e:
            result.error = str(e)
            self.logger.error(f"日本語法規差分確認エラー: {e}")
        
        return result
    
    def check_english_law_diff(self, url: str) -> DiffResult:
        """英語法規の差分を確認"""
        self.logger.info("英語法規の差分確認を開始")
        
        result = DiffResult(
            source="English Law",
            timestamp=datetime.now().isoformat(),
            has_changes=False,
            old_hash=None,
            new_hash=None,
            changes=[],
            error=None
        )
        
        try:
            # 既存ファイルのハッシュを取得
            existing_file = self.data_dir / "RadioAct_en.xml"
            if existing_file.exists():
                result.old_hash = self._calculate_file_hash(existing_file)
            
            # 最新ファイルをダウンロード
            temp_file = self._download_file(url, "RadioAct_en_temp.xml")
            if not temp_file:
                result.error = "ダウンロードに失敗"
                return result
            
            # 正規化
            normalized_temp = self._normalize_xml(temp_file)
            result.new_hash = self._calculate_file_hash(normalized_temp)
            
            # 差分確認
            if result.old_hash and result.new_hash:
                if result.old_hash != result.new_hash:
                    result.has_changes = True
                    result.changes.append("ハッシュ値が変更されました")
                    
                    # メタデータの差分も確認
                    old_metadata = {}
                    if existing_file.exists():
                        old_metadata = self._extract_metadata(existing_file)
                    
                    new_metadata = self._extract_metadata(normalized_temp)
                    
                    # メタデータの差分を検出
                    for key in set(old_metadata.keys()) | set(new_metadata.keys()):
                        if old_metadata.get(key) != new_metadata.get(key):
                            result.changes.append(f"メタデータ '{key}' が変更: {old_metadata.get(key)} → {new_metadata.get(key)}")
                else:
                    result.changes.append("変更なし")
            else:
                result.changes.append("初回ダウンロード")
            
            # 成功した場合はファイルを置き換え
            if not result.error:
                if existing_file.exists():
                    existing_file.unlink()
                normalized_temp.rename(existing_file)
                temp_file.unlink(missing_ok=True)
            
        except Exception as e:
            result.error = str(e)
            self.logger.error(f"英語法規差分確認エラー: {e}")
        
        return result
    
    def check_all_diffs(self, ja_url: str, en_url: str) -> List[DiffResult]:
        """全ての差分を確認"""
        results = []
        
        # 日本語法規の差分確認
        ja_result = self.check_japanese_law_diff(ja_url)
        results.append(ja_result)
        
        # 英語法規の差分確認
        en_result = self.check_english_law_diff(en_url)
        results.append(en_result)
        
        # 結果をキャッシュに保存
        self.cache['last_check'] = {
            'timestamp': datetime.now().isoformat(),
            'results': [asdict(result) for result in results]
        }
        self._save_cache()
        
        return results
    
    def display_results(self, results: List[DiffResult]):
        """結果を表示"""
        console.print("\n[bold blue]法規データソース差分確認結果[/bold blue]\n")
        
        for result in results:
            # 結果パネルを作成
            if result.error:
                status = Text("❌ エラー", style="red")
                content = f"エラー: {result.error}"
            elif result.has_changes:
                status = Text("🔄 変更あり", style="yellow")
                content = "\n".join(result.changes)
            else:
                status = Text("✅ 変更なし", style="green")
                content = "\n".join(result.changes)
            
            panel = Panel(
                f"[bold]{result.source}[/bold]\n"
                f"時刻: {result.timestamp}\n"
                f"状態: {status}\n"
                f"変更内容:\n{content}",
                title=f"差分確認結果 - {result.source}",
                border_style="blue"
            )
            console.print(panel)
        
        # サマリーテーブル
        table = Table(title="差分確認サマリー")
        table.add_column("ソース", style="cyan")
        table.add_column("状態", style="magenta")
        table.add_column("変更数", style="green")
        
        for result in results:
            status = "エラー" if result.error else ("変更あり" if result.has_changes else "変更なし")
            change_count = len(result.changes)
            table.add_row(result.source, status, str(change_count))
        
        console.print(table)


def main():
    """メイン関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="法規データソース差分確認ツール")
    parser.add_argument("--ja-url", default="https://elaws.e-gov.go.jp/api/1/lawdata/325AC0000000131", 
                       help="日本語法規XMLのURL")
    parser.add_argument("--en-url", default="https://www.japaneselawtranslation.go.jp/common/data/law/325AC0000000131.zip",
                       help="英語法規XMLのURL")
    parser.add_argument("--data-dir", default="data", help="データディレクトリ")
    parser.add_argument("--cache-file", default="diff_cache.json", help="キャッシュファイル")
    
    args = parser.parse_args()
    
    # 差分確認実行
    checker = LawDiffChecker(args.data_dir, args.cache_file)
    results = checker.check_all_diffs(args.ja_url, args.en_url)
    
    # 結果表示
    checker.display_results(results)
    
    # 変更があった場合は終了コード1を返す
    if any(result.has_changes for result in results):
        return 1
    return 0


if __name__ == "__main__":
    exit(main()) 