"""
Backtest Engine - 回測引擎
提供基於資料庫決策分數的訊號回測，以及 SMA 交叉基準策略。
"""
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from data.database import Database


@dataclass
class BacktestResult:
    """回測結果資料結構。"""
    ticker: str
    strategy_name: str
    total_return: float       # 百分比
    market_return: float      # 百分比 (買入持有)
    max_drawdown: float       # 百分比
    sharpe_ratio: float
    win_rate: float
    total_trades: int
    profit_factor: float
    prices_df: pd.DataFrame = field(repr=False)
    # prices_df 包含欄位: Cum_Market, Cum_Strategy, Position, Drawdown


class BacktestEngine:
    """
    回測引擎，支援:
    1. run_signal_backtest - 使用資料庫中的 Kronos / TimesFM / Fusion 分數進行交易
    2. run_sma_backtest    - SMA 交叉策略作為基準比較
    """

    def __init__(self, db_path: str = "data/stock_advisor.db"):
        self.db = Database(db_path)

    # ------------------------------------------------------------------
    # 公開方法
    # ------------------------------------------------------------------

    def run_signal_backtest(
        self,
        ticker: str,
        interval: str = "1d",
        signal_source: str = "fusion",
        threshold: float = 15.0,
        transaction_cost: float = 0.001,
    ) -> BacktestResult:
        """
        基於資料庫中的預測/決策分數執行回測。

        Parameters
        ----------
        ticker : str
            股票代碼
        interval : str
            時間週期 (e.g. '1d', '1h')
        signal_source : str
            分數來源 - 'kronos', 'timesfm', 'fusion'
        threshold : float
            進場門檻分數，score > threshold 做多, score < -threshold 平倉
        transaction_cost : float
            每筆交易成本比率 (預設 0.1%)

        Returns
        -------
        BacktestResult or None
        """
        # 取得價格資料
        prices = self.db.get_prices(ticker, interval)
        if prices is None or prices.empty or len(prices) < 10:
            return None
        prices.index = prices.index.normalize()
        prices = prices[~prices.index.duplicated(keep='last')]

        # 取得分數序列
        scores = self._get_signal_scores(ticker, interval, signal_source)
        if scores is None or scores.empty:
            return None
        scores.index = scores.index.normalize()
        scores = scores[~scores.index.duplicated(keep='last')]

        # 合併價格與分數 (使用外連接保留週末預測)
        scores.name = 'score'
        df = pd.concat([prices[['Close']], scores], axis=1)
        df['Close'] = df['Close'].ffill()
        df['score'] = df['score'].ffill().fillna(0.0)

        # 產生部位訊號
        df['Position'] = 0
        position = 0
        for i in range(len(df)):
            score_val = df['score'].iloc[i]
            if score_val > threshold and position == 0:
                position = 1
            elif score_val < -threshold and position == 1:
                position = 0
            df.iloc[i, df.columns.get_loc('Position')] = position

        # 避免前視偏差: 部位延遲一期
        df['Position'] = df['Position'].shift(1).fillna(0).astype(int)

        # 計算績效
        return self._calculate_performance(
            df, ticker, f"Signal({signal_source})", transaction_cost
        )

    def run_sma_backtest(
        self,
        ticker: str,
        interval: str = "1d",
        short: int = 10,
        long: int = 50,
        transaction_cost: float = 0.001,
    ) -> BacktestResult:
        """
        SMA 交叉策略回測 (基準策略)。

        Parameters
        ----------
        ticker : str
            股票代碼
        interval : str
            時間週期
        short : int
            短期均線天數
        long : int
            長期均線天數
        transaction_cost : float
            每筆交易成本比率

        Returns
        -------
        BacktestResult or None
        """
        prices = self.db.get_prices(ticker, interval)
        if prices is None or prices.empty or len(prices) < long + 5:
            return None
        prices.index = prices.index.normalize()
        prices = prices[~prices.index.duplicated(keep='last')]

        df = prices[['Close']].copy()
        df['SMA_short'] = df['Close'].rolling(window=short).mean()
        df['SMA_long'] = df['Close'].rolling(window=long).mean()

        # 交叉訊號: 短均線 > 長均線 = 做多
        df['Position'] = 0
        df.loc[df['SMA_short'] > df['SMA_long'], 'Position'] = 1

        # 避免前視偏差
        df['Position'] = df['Position'].shift(1).fillna(0).astype(int)

        # 清除輔助欄位
        df.drop(columns=['SMA_short', 'SMA_long'], inplace=True)

        return self._calculate_performance(
            df, ticker, f"SMA({short}/{long})", transaction_cost
        )

    # ==================================================================
    # 向後相容: 舊版 run_kronos_backtest 方法
    # ==================================================================

    def run_kronos_backtest(self, ticker: str) -> pd.DataFrame:
        """
        保留舊版介面，內部呼叫 run_sma_backtest。
        回傳含 Cum_Market / Cum_Strategy 的 DataFrame，供舊版 BacktestPage 使用。
        """
        result = self.run_sma_backtest(ticker)
        if result is None:
            return None
        return result.prices_df

    # ------------------------------------------------------------------
    # 內部方法
    # ------------------------------------------------------------------

    def _get_signal_scores(
        self, ticker: str, interval: str, source: str
    ) -> pd.Series:
        """
        從資料庫取得分數序列，回傳以日期為索引的 Series。
        """
        try:
            with self.db._get_connection() as conn:
                if source == "fusion":
                    # 從 decisions 表取 final_score
                    query = (
                        "SELECT date, final_score FROM decisions "
                        "WHERE ticker = ? AND interval = ? ORDER BY date ASC"
                    )
                    df = pd.read_sql_query(
                        query, conn, params=[ticker, interval]
                    )
                    if df.empty:
                        return None
                    df['date'] = pd.to_datetime(df['date'], format='mixed')
                    df.set_index('date', inplace=True)
                    return df['final_score']

                elif source == "kronos":
                    # 從 predictions 表取 score_k (interval 不含 _tfm)
                    query = (
                        "SELECT date, score_k FROM predictions "
                        "WHERE ticker = ? AND interval = ? ORDER BY date ASC"
                    )
                    df = pd.read_sql_query(
                        query, conn, params=[ticker, interval]
                    )
                    if df.empty:
                        return None
                    df['date'] = pd.to_datetime(df['date'], format='mixed')
                    df.set_index('date', inplace=True)
                    return df['score_k']

                elif source == "timesfm":
                    # 從 predictions 表取 score_k (interval 帶 _tfm 後綴)
                    tfm_interval = interval + "_tfm"
                    query = (
                        "SELECT date, score_k FROM predictions "
                        "WHERE ticker = ? AND interval = ? ORDER BY date ASC"
                    )
                    df = pd.read_sql_query(
                        query, conn, params=[ticker, tfm_interval]
                    )
                    if df.empty:
                        return None
                    df['date'] = pd.to_datetime(df['date'], format='mixed')
                    df.set_index('date', inplace=True)
                    return df['score_k']

        except Exception as e:
            print(f"BacktestEngine: 取得分數失敗 ({source}): {e}")
        return None

    def _calculate_performance(
        self,
        df: pd.DataFrame,
        ticker: str,
        strategy_name: str,
        transaction_cost: float,
    ) -> BacktestResult:
        """
        給定帶有 Close 與 Position 欄位的 DataFrame，計算完整回測績效指標。
        """
        df = df.dropna(subset=['Close']).copy()
        if len(df) < 2:
            return None

        # 日報酬
        df['Daily_Return'] = df['Close'].pct_change().fillna(0.0)

        # 交易成本: 當部位變動時扣除成本
        df['Position_Change'] = df['Position'].diff().abs().fillna(0)
        df['Cost'] = df['Position_Change'] * transaction_cost

        # 策略報酬 = 部位 * 日報酬 - 成本
        df['Strategy_Return'] = df['Position'] * df['Daily_Return'] - df['Cost']

        # 累積報酬
        df['Cum_Market'] = (1 + df['Daily_Return']).cumprod()
        df['Cum_Strategy'] = (1 + df['Strategy_Return']).cumprod()

        # 最大回撤
        cum_max = df['Cum_Strategy'].cummax()
        df['Drawdown'] = (df['Cum_Strategy'] - cum_max) / cum_max
        max_drawdown = float(df['Drawdown'].min()) * 100  # 百分比 (負值)

        # 總報酬
        total_return = (df['Cum_Strategy'].iloc[-1] - 1) * 100
        market_return = (df['Cum_Market'].iloc[-1] - 1) * 100

        # Sharpe Ratio (假設無風險利率 = 0，年化以 252 交易日計)
        strategy_returns = df['Strategy_Return']
        mean_ret = strategy_returns.mean()
        std_ret = strategy_returns.std()
        sharpe_ratio = 0.0
        if std_ret > 0:
            sharpe_ratio = (mean_ret / std_ret) * np.sqrt(252)

        # 交易次數與勝率
        trades = self._extract_trades(df)
        total_trades = len(trades)
        winning_trades = [t for t in trades if t > 0]
        losing_trades = [t for t in trades if t <= 0]
        win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0.0

        # 獲利因子
        gross_profit = sum(winning_trades) if winning_trades else 0.0
        gross_loss = abs(sum(losing_trades)) if losing_trades else 0.0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf') if gross_profit > 0 else 0.0

        return BacktestResult(
            ticker=ticker,
            strategy_name=strategy_name,
            total_return=round(total_return, 4),
            market_return=round(market_return, 4),
            max_drawdown=round(max_drawdown, 4),
            sharpe_ratio=round(sharpe_ratio, 4),
            win_rate=round(win_rate, 2),
            total_trades=total_trades,
            profit_factor=round(profit_factor, 4),
            prices_df=df,
        )

    @staticmethod
    def _extract_trades(df: pd.DataFrame) -> list:
        """
        從部位序列中拆解出每筆交易的報酬率。
        每次從 0 -> 1 為進場，從 1 -> 0 為出場。
        """
        trades = []
        in_trade = False
        entry_price = 0.0

        for i in range(len(df)):
            pos = df['Position'].iloc[i]
            close = df['Close'].iloc[i]

            if pos == 1 and not in_trade:
                # 進場
                in_trade = True
                entry_price = close
            elif pos == 0 and in_trade:
                # 出場
                in_trade = False
                if entry_price > 0:
                    pnl = (close - entry_price) / entry_price
                    trades.append(pnl)

        return trades
