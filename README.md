# Personal-stock-gui

Personal-stock-gui 是一個結合大型語言模型 (LLM) 與先進時間序列預測技術的個人化股票分析圖形介面系統。本專案整合了多智能體 (Multi-Agent) 辯論機制與多種量化預測模型，為使用者提供深度的市場洞察、技術分析以及歷史回測功能。

## 核心功能

1. **雙重時間序列模型預測 (TimesFM 與 KRONOS)**
   - **KRONOS 預測模型**：運用進階的量化預測技術分析市場趨勢，能夠針對特定股票提供精準的漲跌機率 (Up Probability) 與信心分數，為交易決策提供數據支撐。
   - **TimesFM 預測模型**：基於時間序列的基礎模型 (Foundation Model)，從不同維度提供平行的預測數據，並與 KRONOS 模型互相對照驗證，大幅提高市場預測的穩定性與準確度。

2. **多智能體辯論與分析系統 (Multi-Agent System)**
   - 系統內建四種虛擬分析師：市場分析師 (Market Analyst)、情緒分析師 (Sentiment Analyst)、新聞分析師 (News Analyst) 與基本面分析師 (Fundamentals Analyst)。
   - 透過呼叫外部大型語言模型 (如 DeepSeek 等)，讓多位分析師針對同一檔股票進行辯論與綜合評估，最後由投資組合經理 (Portfolio Manager) 做出綜合的買賣建議。

3. **完整的歷史回測引擎 (Backtesting Engine)**
   - 允許使用者針對過去的歷史資料執行交易策略模擬。
   - 透過風險管理 (Risk Management) 模組控制資金回撤，並產生詳細的回測績效報表，協助使用者驗證並優化投資策略。

4. **圖形化操作介面 (GUI Dashboard)**
   - 基於 PyQt6 打造的流暢桌面應用程式。
   - 提供直覺的儀表板、股票分析檢視、預測模型比較以及系統設定等頁面，使用者無須撰寫程式碼即可操作複雜的 AI 分析流程。

5. **自動化技術分析報告 (TA Reports)**
   - 整合即時市場數據與模型預測結果，系統能自動生成並儲存 Markdown 格式的完整技術分析報告。

## 整合的 GitHub 開源專案

本專案高度整合了以下三個強大的核心開源專案，作為系統底層的預測與分析引擎。詳細的專案架構與原始碼說明，請參閱各專案專屬的 README 檔案：

1. **TradingAgents (多智能體交易辯論框架)**
   - 負責處理多個虛擬分析師 (LLM) 之間的辯論流程與最終投資決策。
   - 📖 [請參閱 TradingAgents README](./TradingAgents/README.md)

2. **Kronos (進階時間序列預測模型)**
   - 專門用於量化分析與精準預測股票未來趨勢及信心分數。
   - 📖 [請參閱 Kronos README](./kronos/README.md)

3. **TimesFM (時間序列基礎模型)**
   - 作為另一個平行的預測引擎，提供市場趨勢的基準數據並與 Kronos 進行交叉驗證。
   - 📖 [請參閱 TimesFM 官方 README](https://github.com/google-research/timesfm)

## 系統架構與目錄說明

- `ui/`：圖形化介面的核心程式碼，包含主視窗 (`main_window.py`)、側邊欄 (`sidebar.py`) 以及各個功能頁面 (如 `dashboard.py`、`stock_analysis.py` 等)。
- `data/`：負責資料收集、處理與儲存，內部包含核心資料庫檔案 (`stock_advisor.db`)，用於記錄股票歷史資料、模型預測結果與系統日誌。
- `decision/`：交易決策模組，包含基於規則的交易邏輯 (`rule_based.py`) 與風險管理機制 (`risk_manager.py`)。
- `backtest/`：回測引擎 (`engine.py`)，用於執行與評估歷史交易策略。
- `trading_agents/`：整合多智能體框架的適配器，負責與 LLM 介接並調度分析師之間的辯論流程。
- `reports/`：統一存放由系統自動產生的 Markdown 格式股票技術分析報告，方便團隊成員查閱與簡報使用。
- `utils/`：系統共用工具，如日誌紀錄 (`logger.py`) 與資料匯出 (`export.py`) 功能。
- `third_party/`：包含專案所依賴的第三方原始碼子模組。

## 環境建置與安裝指南

### 1. 取得專案程式碼
請先將本儲存庫複製到你的本地端電腦中：
```bash
git clone <本儲存庫網址>
cd Personal-stock-gui
```

### 2. 建立並啟動虛擬環境 (建議)
為了避免套件衝突，建議建立獨立的 Python 虛擬環境：
```bash
python -m venv .venv
# Windows 系統啟動虛擬環境
.venv\Scripts\activate
# macOS/Linux 系統啟動虛擬環境
source .venv/bin/activate
```

### 3. 安裝依賴套件
系統所需的所有套件與相依性皆已記錄於 `requirements.txt` 中。請執行以下指令進行安裝 (此清單已移除硬體綁定的限制，可通用於各種環境)：
```bash
pip install -r requirements.txt
```

### 4. 設定環境變數與 API 金鑰
本系統在執行多智能體分析時需要呼叫 LLM 服務。請在專案根目錄下建立一個名為 `.env` 的檔案，並填入你所使用的 API 金鑰：
```env
# 範例：使用 DeepSeek 作為模型提供者
DEEPSEEK_API_KEY=your_deepseek_api_key_here
```

## 使用教學

環境建置完成並設定好 API 金鑰後，請在終端機執行以下指令以啟動圖形化介面：

```bash
python main_gui.py
```

啟動後，你可以在左側的設定頁面中確認 API 模型供應商是否選擇正確，隨後即可進入「股票分析」或「模型比較」頁面開始你的量化投資探索。
