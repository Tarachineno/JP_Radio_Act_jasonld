#!/usr/bin/env python3
"""
法規データソース差分確認モジュールのテスト
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
import json
import hashlib

from diff_checker import LawDiffChecker, DiffResult


class TestLawDiffChecker:
    """LawDiffCheckerクラスのテスト"""
    
    @pytest.fixture
    def temp_dir(self):
        """一時ディレクトリを作成"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def checker(self, temp_dir):
        """LawDiffCheckerインスタンスを作成"""
        return LawDiffChecker(str(temp_dir), "test_cache.json")
    
    def test_init(self, temp_dir):
        """初期化テスト"""
        checker = LawDiffChecker(str(temp_dir), "test_cache.json")
        assert checker.data_dir == temp_dir
        assert checker.cache_file == temp_dir / "test_cache.json"
        assert temp_dir.exists()
    
    def test_load_cache_existing(self, temp_dir):
        """既存キャッシュファイルの読み込みテスト"""
        cache_data = {"test": "data"}
        cache_file = temp_dir / "test_cache.json"
        
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f)
        
        checker = LawDiffChecker(str(temp_dir), "test_cache.json")
        assert checker.cache == cache_data
    
    def test_load_cache_not_existing(self, temp_dir):
        """存在しないキャッシュファイルの読み込みテスト"""
        checker = LawDiffChecker(str(temp_dir), "nonexistent.json")
        assert checker.cache == {}
    
    def test_save_cache(self, temp_dir):
        """キャッシュ保存テスト"""
        checker = LawDiffChecker(str(temp_dir), "test_cache.json")
        checker.cache = {"test": "data"}
        checker._save_cache()
        
        cache_file = temp_dir / "test_cache.json"
        assert cache_file.exists()
        
        with open(cache_file, 'r') as f:
            saved_data = json.load(f)
        assert saved_data == {"test": "data"}
    
    def test_calculate_file_hash(self, temp_dir):
        """ファイルハッシュ計算テスト"""
        checker = LawDiffChecker(str(temp_dir), "test_cache.json")
        
        # テストファイルを作成
        test_file = temp_dir / "test.txt"
        test_content = "Hello, World!"
        with open(test_file, 'w') as f:
            f.write(test_content)
        
        # ハッシュを計算
        hash_value = checker._calculate_file_hash(test_file)
        
        # 期待されるハッシュ値を計算
        expected_hash = hashlib.md5(test_content.encode()).hexdigest()
        assert hash_value == expected_hash
    
    def test_calculate_file_hash_not_existing(self, temp_dir):
        """存在しないファイルのハッシュ計算テスト"""
        checker = LawDiffChecker(str(temp_dir), "test_cache.json")
        non_existing_file = temp_dir / "nonexistent.txt"
        
        hash_value = checker._calculate_file_hash(non_existing_file)
        assert hash_value == ""
    
    @patch('diff_checker.requests.get')
    def test_download_file_success(self, mock_get, temp_dir):
        """ファイルダウンロード成功テスト"""
        checker = LawDiffChecker(str(temp_dir), "test_cache.json")
        
        # モックレスポンスを設定
        mock_response = Mock()
        mock_response.content = b"test content"
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # ダウンロード実行
        result = checker._download_file("http://example.com/test.xml", "test.xml")
        
        assert result is not None
        assert result == temp_dir / "test.xml"
        assert result.exists()
        
        # ファイル内容を確認
        with open(result, 'rb') as f:
            content = f.read()
        assert content == b"test content"
    
    @patch('diff_checker.requests.get')
    def test_download_file_failure(self, mock_get, temp_dir):
        """ファイルダウンロード失敗テスト"""
        checker = LawDiffChecker(str(temp_dir), "test_cache.json")
        
        # モックで例外を発生
        mock_get.side_effect = Exception("Download failed")
        
        # ダウンロード実行
        result = checker._download_file("http://example.com/test.xml", "test.xml")
        
        assert result is None
    
    def test_normalize_xml(self, temp_dir):
        """XML正規化テスト"""
        checker = LawDiffChecker(str(temp_dir), "test_cache.json")
        
        # テストXMLファイルを作成
        test_xml = """<?xml version="1.0" encoding="UTF-8"?>
<root>
    <item>test</item>
</root>"""
        
        test_file = temp_dir / "test.xml"
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(test_xml)
        
        # 正規化実行
        result = checker._normalize_xml(test_file)
        
        assert result.exists()
        assert result.name.endswith('.normalized.xml')
        
        # 正規化されたファイルの内容を確認
        with open(result, 'rb') as f:
            content = f.read()
        
        # BOMが除去されていることを確認
        assert not content.startswith(b'\xef\xbb\xbf')
        # LF改行になっていることを確認
        assert b'\r\n' not in content
    
    def test_extract_metadata(self, temp_dir):
        """メタデータ抽出テスト"""
        checker = LawDiffChecker(str(temp_dir), "test_cache.json")
        
        # テストXMLファイルを作成
        test_xml = """<?xml version="1.0" encoding="UTF-8"?>
<root>
    <LawNum>325AC0000000131</LawNum>
    <LawName>電波法</LawName>
    <EnactDate>1950-05-02</EnactDate>
    <EnforcementDate>1950-06-01</EnforcementDate>
</root>"""
        
        test_file = temp_dir / "test.xml"
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(test_xml)
        
        # メタデータ抽出実行
        metadata = checker._extract_metadata(test_file)
        
        expected_metadata = {
            'law_number': '325AC0000000131',
            'law_name': '電波法',
            'enact_date': '1950-05-02',
            'enforcement_date': '1950-06-01'
        }
        
        assert metadata == expected_metadata
    
    @patch('diff_checker.LawDiffChecker._download_file')
    @patch('diff_checker.LawDiffChecker._normalize_xml')
    def test_check_japanese_law_diff_no_changes(self, mock_normalize, mock_download, temp_dir):
        """日本語法規差分確認 - 変更なしテスト"""
        checker = LawDiffChecker(str(temp_dir), "test_cache.json")
        
        # 既存ファイルを作成
        existing_file = temp_dir / "RadioAct_ja.xml"
        existing_content = "existing content"
        with open(existing_file, 'w') as f:
            f.write(existing_content)
        
        # モック設定
        temp_file = temp_dir / "RadioAct_ja_temp.xml"
        with open(temp_file, 'w') as f:
            f.write(existing_content)  # 同じ内容
        
        mock_download.return_value = temp_file
        mock_normalize.return_value = temp_file
        
        # 差分確認実行
        result = checker.check_japanese_law_diff("http://example.com/test.xml")
        
        assert result.source == "Japanese Law"
        assert not result.has_changes
        assert "変更なし" in result.changes
        assert result.error is None
    
    @patch('diff_checker.LawDiffChecker._download_file')
    @patch('diff_checker.LawDiffChecker._normalize_xml')
    def test_check_japanese_law_diff_with_changes(self, mock_normalize, mock_download, temp_dir):
        """日本語法規差分確認 - 変更ありテスト"""
        checker = LawDiffChecker(str(temp_dir), "test_cache.json")
        
        # 既存ファイルを作成
        existing_file = temp_dir / "RadioAct_ja.xml"
        existing_content = "existing content"
        with open(existing_file, 'w') as f:
            f.write(existing_content)
        
        # モック設定
        temp_file = temp_dir / "RadioAct_ja_temp.xml"
        new_content = "new content"
        with open(temp_file, 'w') as f:
            f.write(new_content)  # 異なる内容
        
        mock_download.return_value = temp_file
        mock_normalize.return_value = temp_file
        
        # 差分確認実行
        result = checker.check_japanese_law_diff("http://example.com/test.xml")
        
        assert result.source == "Japanese Law"
        assert result.has_changes
        assert "ハッシュ値が変更されました" in result.changes
        assert result.error is None
    
    @patch('diff_checker.LawDiffChecker._download_file')
    def test_check_japanese_law_diff_download_failure(self, mock_download, temp_dir):
        """日本語法規差分確認 - ダウンロード失敗テスト"""
        checker = LawDiffChecker(str(temp_dir), "test_cache.json")
        
        # モックでダウンロード失敗を設定
        mock_download.return_value = None
        
        # 差分確認実行
        result = checker.check_japanese_law_diff("http://example.com/test.xml")
        
        assert result.source == "Japanese Law"
        assert result.error == "ダウンロードに失敗"
        assert not result.has_changes
    
    def test_check_all_diffs(self, temp_dir):
        """全差分確認テスト"""
        checker = LawDiffChecker(str(temp_dir), "test_cache.json")
        
        with patch.object(checker, 'check_japanese_law_diff') as mock_ja:
            with patch.object(checker, 'check_english_law_diff') as mock_en:
                # モック結果を設定
                ja_result = DiffResult(
                    source="Japanese Law",
                    timestamp="2024-01-01T00:00:00",
                    has_changes=False,
                    old_hash="old_hash",
                    new_hash="old_hash",
                    changes=["変更なし"]
                )
                en_result = DiffResult(
                    source="English Law",
                    timestamp="2024-01-01T00:00:00",
                    has_changes=True,
                    old_hash="old_hash",
                    new_hash="new_hash",
                    changes=["ハッシュ値が変更されました"]
                )
                
                mock_ja.return_value = ja_result
                mock_en.return_value = en_result
                
                # 全差分確認実行
                results = checker.check_all_diffs("ja_url", "en_url")
                
                assert len(results) == 2
                assert results[0] == ja_result
                assert results[1] == en_result
                
                # キャッシュが保存されていることを確認
                assert 'last_check' in checker.cache
                assert 'results' in checker.cache['last_check']


class TestDiffResult:
    """DiffResultクラスのテスト"""
    
    def test_diff_result_creation(self):
        """DiffResult作成テスト"""
        result = DiffResult(
            source="Test Source",
            timestamp="2024-01-01T00:00:00",
            has_changes=True,
            old_hash="old_hash",
            new_hash="new_hash",
            changes=["change1", "change2"],
            error=None
        )
        
        assert result.source == "Test Source"
        assert result.timestamp == "2024-01-01T00:00:00"
        assert result.has_changes is True
        assert result.old_hash == "old_hash"
        assert result.new_hash == "new_hash"
        assert result.changes == ["change1", "change2"]
        assert result.error is None
    
    def test_diff_result_with_error(self):
        """エラー付きDiffResult作成テスト"""
        result = DiffResult(
            source="Test Source",
            timestamp="2024-01-01T00:00:00",
            has_changes=False,
            old_hash=None,
            new_hash=None,
            changes=[],
            error="Test error"
        )
        
        assert result.error == "Test error"
        assert not result.has_changes


if __name__ == "__main__":
    pytest.main([__file__]) 