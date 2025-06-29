#!/usr/bin/env python3
"""
日本電波法 XML 取得・正規化スクリプト

e-Gov 法令 API から Radio Act (LawID: 325AC0000000131) の XML を取得し、
UTF-8/LF 正規化を行います。
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional, Tuple

import rich.console
import rich.panel
from rich import print as rprint

from radio_act_validator import (
    download_and_validate_japanese,
    download_and_validate_english,
    setup_logging
)


def parse_arguments() -> argparse.Namespace:
    """コマンドライン引数を解析します。"""
    parser = argparse.ArgumentParser(
        description="日本電波法 XML 取得・正規化スクリプト",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python validate_radio_act_xml.py --ja --en    # 両方のファイルを処理
  python validate_radio_act_xml.py --ja         # 日本語版のみ
  python validate_radio_act_xml.py --en         # 英語版のみ
        """
    )
    
    parser.add_argument(
        "--ja", "--japanese",
        action="store_true",
        help="日本語版 Radio Act XML を取得・保存"
    )
    
    parser.add_argument(
        "--en", "--english", 
        action="store_true",
        help="英語版 Radio Act XML を取得・保存"
    )
    
    parser.add_argument(
        "--ja-url",
        type=str,
        default=None,
        help="日本語版 Radio Act XML のダウンロードURL (省略時はデフォルト)"
    )
    parser.add_argument(
        "--en-url",
        type=str,
        default=None,
        help="英語版 Radio Act XML のダウンロードURL (省略時はデフォルト)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="詳細なログ出力"
    )
    
    parser.add_argument(
        "--output-dir", "-o",
        type=str,
        default="data",
        help="出力ディレクトリ (デフォルト: data)"
    )
    
    return parser.parse_args()


def main() -> int:
    """メイン関数"""
    args = parse_arguments()
    
    # 出力ディレクトリの作成
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    # ログ設定
    setup_logging(verbose=args.verbose)
    logger = logging.getLogger(__name__)
    
    console = rich.console.Console()
    
    # 引数チェック
    if not args.ja and not args.en:
        console.print(
            "[red]エラー: --ja または --en のいずれかを指定してください[/red]"
        )
        return 1
    
    console.print(
        rich.panel.Panel(
            "[bold blue]日本電波法 XML 取得・正規化スクリプト[/bold blue]",
            border_style="blue"
        )
    )
    
    success_count = 0
    total_count = 0
    
    try:
        # 日本語版の処理
        if args.ja:
            total_count += 1
            console.print("\n[bold yellow]📥 日本語版 Radio Act XML を取得中...[/bold yellow]")
            
            if download_and_validate_japanese(output_dir, ja_url=args.ja_url):
                console.print("[green]✅ 日本語版の取得が完了しました[/green]")
                success_count += 1
            else:
                console.print("[red]❌ 日本語版の取得に失敗しました[/red]")
        
        # 英語版の処理
        if args.en:
            total_count += 1
            console.print("\n[bold yellow]📥 英語版 Radio Act XML を取得中...[/bold yellow]")
            
            if download_and_validate_english(output_dir, en_url=args.en_url):
                console.print("[green]✅ 英語版の取得が完了しました[/green]")
                success_count += 1
            else:
                console.print("[red]❌ 英語版の取得に失敗しました[/red]")
        
        # 結果サマリー
        console.print(f"\n[bold]📊 処理結果: {success_count}/{total_count} 成功[/bold]")
        
        if success_count == total_count:
            console.print("[green]🎉 すべての処理が正常に完了しました！[/green]")
            return 0
        else:
            console.print("[red]⚠️  一部の処理に失敗しました[/red]")
            return 1
            
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  処理が中断されました[/yellow]")
        return 1
    except Exception as e:
        logger.exception("予期しないエラーが発生しました")
        console.print(f"[red]❌ 予期しないエラー: {e}[/red]")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 