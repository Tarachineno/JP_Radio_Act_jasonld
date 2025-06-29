"""
日本電波法 XML バリデーションスクリプトのテスト

pytest で実行するためのユニットテスト
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

from radio_act_validator import (
    download_file,
    extract_zip_and_find_xml,
    validate_xml_with_xsd,
    validate_xml_with_dtd,
    normalize_xml,
    get_egov_xsd_schema,
    get_english_xml_url
)


class TestDownloadFile:
    """download_file関数のテスト"""
    
    @patch('radio_act_validator.requests.get')
    def test_download_file_success(self, mock_get):
        """正常なダウンロードのテスト"""
        # モックの設定
        mock_response = Mock()
        mock_response.content = b"test content"
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        with tempfile.TemporaryDirectory() as temp_dir:
            dest_path = Path(temp_dir) / "test.txt"
            result = download_file("https://example.com/test.txt", dest_path)
            
            assert result is True
            assert dest_path.exists()
            assert dest_path.read_bytes() == b"test content"
    
    @patch('radio_act_validator.requests.get')
    def test_download_file_failure(self, mock_get):
        """ダウンロード失敗のテスト"""
        # モックの設定
        mock_get.side_effect = Exception("Network error")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            dest_path = Path(temp_dir) / "test.txt"
            result = download_file("https://example.com/test.txt", dest_path)
            
            assert result is False
            assert not dest_path.exists()


class TestExtractZipAndFindXml:
    """extract_zip_and_find_xml関数のテスト"""
    
    def test_extract_zip_with_law_xml(self):
        """law.xmlを含むZIPファイルの展開テスト"""
        # テスト用のZIPファイルを作成
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = Path(temp_dir) / "test.zip"
            
            # 簡易的なZIPファイルを作成
            import zipfile
            with zipfile.ZipFile(zip_path, 'w') as zip_ref:
                zip_ref.writestr("law.xml", "<?xml version='1.0'?><root>test</root>")
            
            result = extract_zip_and_find_xml(zip_path)
            
            assert result is not None
            assert result.name == "law.xml"
            assert result.exists()
    
    def test_extract_zip_with_other_xml(self):
        """law.xml以外のXMLファイルを含むZIPファイルの展開テスト"""
        # テスト用のZIPファイルを作成
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = Path(temp_dir) / "test.zip"
            
            # 簡易的なZIPファイルを作成
            import zipfile
            with zipfile.ZipFile(zip_path, 'w') as zip_ref:
                zip_ref.writestr("other.xml", "<?xml version='1.0'?><root>test</root>")
            
            result = extract_zip_and_find_xml(zip_path)
            
            assert result is not None
            assert result.name == "other.xml"
            assert result.exists()
    
    def test_extract_zip_without_law_xml(self):
        """XMLファイルを含まないZIPファイルのテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = Path(temp_dir) / "test.zip"
            
            # XMLファイルを含まないZIPファイルを作成
            import zipfile
            with zipfile.ZipFile(zip_path, 'w') as zip_ref:
                zip_ref.writestr("other.txt", "test content")
            
            result = extract_zip_and_find_xml(zip_path)
            
            assert result is None


class TestValidateXmlWithXsd:
    """validate_xml_with_xsd関数のテスト"""
    
    def test_validate_xml_with_valid_schema(self):
        """有効なXSDスキーマでのバリデーションテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            xml_path = Path(temp_dir) / "test.xml"
            xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<Law>
    <LawNum>325AC0000000131</LawNum>
    <LawName>電波法</LawName>
    <LawBody>法律本文</LawBody>
</Law>"""
            xml_path.write_text(xml_content, encoding='utf-8')
            
            xsd_schema = get_egov_xsd_schema()
            is_valid, error_msg = validate_xml_with_xsd(xml_path, xsd_schema)
            
            assert is_valid is True
            assert error_msg is None
    
    def test_validate_xml_with_invalid_schema(self):
        """無効なXMLでのバリデーションテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            xml_path = Path(temp_dir) / "test.xml"
            xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<InvalidRoot>
    <InvalidElement>test</InvalidElement>
</InvalidRoot>"""
            xml_path.write_text(xml_content, encoding='utf-8')
            
            xsd_schema = get_egov_xsd_schema()
            is_valid, error_msg = validate_xml_with_xsd(xml_path, xsd_schema)
            
            assert is_valid is False
            assert error_msg is not None


class TestValidateXmlWithDtd:
    """validate_xml_with_dtd関数のテスト"""
    
    def test_validate_xml_with_valid_dtd(self):
        """有効なDTDでのバリデーションテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            xml_path = Path(temp_dir) / "test.xml"
            xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE root [
<!ELEMENT root (item*)>
<!ELEMENT item (#PCDATA)>
]>
<root>
    <item>test</item>
</root>"""
            xml_path.write_text(xml_content, encoding='utf-8')
            
            is_valid, error_msg = validate_xml_with_dtd(xml_path)
            
            assert is_valid is True
            assert error_msg is None


class TestNormalizeXml:
    """normalize_xml関数のテスト"""
    
    def test_normalize_xml_success(self):
        """XML正規化の成功テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "input.xml"
            output_path = Path(temp_dir) / "output.xml"
            
            # テスト用XML（CRLF改行を含む）
            xml_content = "<?xml version='1.0'?>\r\n<root>\r\n<item>test</item>\r\n</root>"
            input_path.write_text(xml_content, encoding='utf-8')
            
            result = normalize_xml(input_path, output_path)
            
            assert result is True
            assert output_path.exists()
            
            # 改行がLFに統一されていることを確認
            normalized_content = output_path.read_text(encoding='utf-8')
            assert '\r\n' not in normalized_content
            assert '\r' not in normalized_content
            assert '\n' in normalized_content


class TestGetEgovXsdSchema:
    """get_egov_xsd_schema関数のテスト"""
    
    def test_get_egov_xsd_schema_returns_string(self):
        """XSDスキーマが文字列として返されることをテスト"""
        schema = get_egov_xsd_schema()
        
        assert isinstance(schema, str)
        assert "<?xml version=" in schema
        assert "<xs:schema" in schema
        assert "Law" in schema


class TestGetEnglishXmlUrl:
    """get_english_xml_url関数のテスト"""
    
    @patch('builtins.input')
    def test_get_english_xml_url_valid_input(self, mock_input):
        """有効なURL入力のテスト"""
        mock_input.return_value = "https://example.com/radio_act.xml"
        
        result = get_english_xml_url()
        
        assert result == "https://example.com/radio_act.xml"
    
    @patch('builtins.input')
    def test_get_english_xml_url_cancel(self, mock_input):
        """キャンセル入力のテスト"""
        mock_input.return_value = "cancel"
        
        result = get_english_xml_url()
        
        assert result is None
    
    @patch('builtins.input')
    def test_get_english_xml_url_invalid_url(self, mock_input):
        """無効なURL入力のテスト"""
        # 最初に無効なURL、次に有効なURL
        mock_input.side_effect = ["invalid-url", "https://example.com/radio_act.xml"]
        
        result = get_english_xml_url()
        
        assert result == "https://example.com/radio_act.xml"
        assert mock_input.call_count == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 