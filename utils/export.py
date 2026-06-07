"""
Export Module - 匯出工具
提供將決策紀錄、回測結果、TA 報告匯出為 CSV / Markdown / HTML 的功能。
"""
import os
import json
import pandas as pd
from datetime import datetime


def export_decisions_csv(db, ticker: str, interval: str, filepath: str) -> bool:
    """
    將指定股票的決策紀錄匯出為 CSV。

    Parameters
    ----------
    db : Database
        資料庫實例
    ticker : str
        股票代碼
    interval : str
        時間週期
    filepath : str
        輸出檔案路徑

    Returns
    -------
    bool : 是否成功
    """
    try:
        df = db.get_decisions(ticker, interval, limit=9999)
        if df is None or df.empty:
            print(f"Export: 查無 {ticker} ({interval}) 的決策紀錄")
            return False

        os.makedirs(os.path.dirname(filepath) or '.', exist_ok=True)
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        return True
    except Exception as e:
        print(f"Export decisions CSV 失敗: {e}")
        return False


def export_backtest_csv(backtest_result, filepath: str) -> bool:
    """
    將回測結果匯出為 CSV (含每日累積報酬與部位)。

    Parameters
    ----------
    backtest_result : BacktestResult
        回測結果物件
    filepath : str
        輸出檔案路徑

    Returns
    -------
    bool : 是否成功
    """
    try:
        if backtest_result is None or backtest_result.prices_df is None:
            print("Export: 無回測結果可匯出")
            return False

        os.makedirs(os.path.dirname(filepath) or '.', exist_ok=True)

        # 寫入摘要行
        summary_lines = [
            f"# Backtest Summary: {backtest_result.ticker} - {backtest_result.strategy_name}",
            f"# Total Return: {backtest_result.total_return:.2f}%",
            f"# Market Return: {backtest_result.market_return:.2f}%",
            f"# Max Drawdown: {backtest_result.max_drawdown:.2f}%",
            f"# Sharpe Ratio: {backtest_result.sharpe_ratio:.4f}",
            f"# Win Rate: {backtest_result.win_rate:.2f}%",
            f"# Total Trades: {backtest_result.total_trades}",
            f"# Profit Factor: {backtest_result.profit_factor:.4f}",
            "",
        ]

        with open(filepath, 'w', encoding='utf-8-sig') as f:
            for line in summary_lines:
                f.write(line + '\n')

        # 追加 DataFrame
        export_cols = ['Close', 'Position', 'Cum_Market', 'Cum_Strategy', 'Drawdown']
        available_cols = [c for c in export_cols if c in backtest_result.prices_df.columns]
        backtest_result.prices_df[available_cols].to_csv(
            filepath, mode='a', encoding='utf-8-sig'
        )
        return True
    except Exception as e:
        print(f"Export backtest CSV 失敗: {e}")
        return False


def export_ta_report_md(db, ticker: str, interval: str, date: str, filepath: str) -> bool:
    """
    將 TA 報告匯出為 Markdown 格式。

    Parameters
    ----------
    db : Database
        資料庫實例
    ticker : str
        股票代碼
    interval : str
        時間週期
    date : str
        報告日期 (None 表示最新)
    filepath : str
        輸出檔案路徑

    Returns
    -------
    bool : 是否成功
    """
    try:
        report = db.get_ta_report(ticker, interval, date)
        if not report:
            print(f"Export: 查無 {ticker} ({interval}) 的 TA 報告")
            return False

        os.makedirs(os.path.dirname(filepath) or '.', exist_ok=True)

        md_lines = []
        md_lines.append(f"# Technical Analysis Report")
        md_lines.append(f"")
        md_lines.append(f"- **Ticker**: {ticker}")
        md_lines.append(f"- **Interval**: {interval}")
        md_lines.append(f"- **Date**: {date or 'Latest'}")
        md_lines.append(f"- **Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        md_lines.append(f"")

        # 基本資訊
        if "summary" in report:
            md_lines.append(f"## Summary")
            md_lines.append(f"")
            md_lines.append(str(report["summary"]))
            md_lines.append(f"")

        # 指標資料
        if "indicators" in report:
            md_lines.append(f"## Technical Indicators")
            md_lines.append(f"")
            md_lines.append(f"| Indicator | Value |")
            md_lines.append(f"|-----------|-------|")
            indicators = report["indicators"]
            if isinstance(indicators, dict):
                for key, val in indicators.items():
                    md_lines.append(f"| {key} | {val} |")
            md_lines.append(f"")

        # 訊號
        if "signals" in report:
            md_lines.append(f"## Signals")
            md_lines.append(f"")
            signals = report["signals"]
            if isinstance(signals, list):
                for sig in signals:
                    md_lines.append(f"- {sig}")
            elif isinstance(signals, dict):
                for key, val in signals.items():
                    md_lines.append(f"- **{key}**: {val}")
            md_lines.append(f"")

        # 其餘所有 key 以 JSON 形式附加
        excluded_keys = {"summary", "indicators", "signals"}
        remaining = {k: v for k, v in report.items() if k not in excluded_keys}
        if remaining:
            md_lines.append(f"## Additional Data")
            md_lines.append(f"")
            md_lines.append(f"```json")
            md_lines.append(json.dumps(remaining, indent=2, ensure_ascii=False))
            md_lines.append(f"```")
            md_lines.append(f"")

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(md_lines))

        return True
    except Exception as e:
        print(f"Export TA report MD 失敗: {e}")
        return False


def export_ta_report_html(db, ticker: str, interval: str, date: str, filepath: str) -> bool:
    """
    將 TA 報告匯出為帶樣式的 HTML。

    Parameters
    ----------
    db : Database
        資料庫實例
    ticker : str
        股票代碼
    interval : str
        時間週期
    date : str
        報告日期 (None 表示最新)
    filepath : str
        輸出檔案路徑

    Returns
    -------
    bool : 是否成功
    """
    try:
        report = db.get_ta_report(ticker, interval, date)
        if not report:
            print(f"Export: 查無 {ticker} ({interval}) 的 TA 報告")
            return False

        os.makedirs(os.path.dirname(filepath) or '.', exist_ok=True)

        # HTML 樣式
        css = """
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f8f9fa;
            color: #2c3e50;
        }
        h1 {
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }
        h2 {
            color: #34495e;
            margin-top: 30px;
        }
        .meta {
            background-color: #ecf0f1;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        .meta span {
            display: inline-block;
            margin-right: 20px;
            font-size: 14px;
        }
        .meta strong { color: #2c3e50; }
        table {
            border-collapse: collapse;
            width: 100%;
            margin: 10px 0;
        }
        th, td {
            border: 1px solid #bdc3c7;
            padding: 10px 14px;
            text-align: left;
        }
        th {
            background-color: #3498db;
            color: white;
        }
        tr:nth-child(even) { background-color: #ecf0f1; }
        ul { padding-left: 20px; }
        li { margin-bottom: 6px; }
        pre {
            background-color: #2c3e50;
            color: #ecf0f1;
            padding: 15px;
            border-radius: 6px;
            overflow-x: auto;
            font-size: 13px;
        }
        """

        html_parts = []
        html_parts.append(f"<!DOCTYPE html>")
        html_parts.append(f"<html lang='zh-TW'>")
        html_parts.append(f"<head><meta charset='utf-8'><title>TA Report - {ticker}</title>")
        html_parts.append(f"<style>{css}</style></head>")
        html_parts.append(f"<body>")
        html_parts.append(f"<h1>Technical Analysis Report</h1>")

        # Meta 資訊
        html_parts.append(f"<div class='meta'>")
        html_parts.append(f"<span><strong>Ticker:</strong> {ticker}</span>")
        html_parts.append(f"<span><strong>Interval:</strong> {interval}</span>")
        html_parts.append(f"<span><strong>Date:</strong> {date or 'Latest'}</span>")
        html_parts.append(f"<span><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span>")
        html_parts.append(f"</div>")

        # Summary
        if "summary" in report:
            html_parts.append(f"<h2>Summary</h2>")
            summary_text = str(report["summary"]).replace('\n', '<br>')
            html_parts.append(f"<p>{summary_text}</p>")

        # Indicators
        if "indicators" in report:
            html_parts.append(f"<h2>Technical Indicators</h2>")
            html_parts.append(f"<table><tr><th>Indicator</th><th>Value</th></tr>")
            indicators = report["indicators"]
            if isinstance(indicators, dict):
                for key, val in indicators.items():
                    html_parts.append(f"<tr><td>{key}</td><td>{val}</td></tr>")
            html_parts.append(f"</table>")

        # Signals
        if "signals" in report:
            html_parts.append(f"<h2>Signals</h2>")
            html_parts.append(f"<ul>")
            signals = report["signals"]
            if isinstance(signals, list):
                for sig in signals:
                    html_parts.append(f"<li>{sig}</li>")
            elif isinstance(signals, dict):
                for key, val in signals.items():
                    html_parts.append(f"<li><strong>{key}</strong>: {val}</li>")
            html_parts.append(f"</ul>")

        # 其餘資料
        excluded_keys = {"summary", "indicators", "signals"}
        remaining = {k: v for k, v in report.items() if k not in excluded_keys}
        if remaining:
            html_parts.append(f"<h2>Additional Data</h2>")
            json_str = json.dumps(remaining, indent=2, ensure_ascii=False)
            html_parts.append(f"<pre>{json_str}</pre>")

        html_parts.append(f"</body></html>")

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(html_parts))

        return True
    except Exception as e:
        print(f"Export TA report HTML 失敗: {e}")
        return False
