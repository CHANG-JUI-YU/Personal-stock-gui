"""
KRONOS_X_AGENT 風險管理模組
在決策引擎輸出之後進行額外的風險檢查，
若觸發任何風險旗標，將降級動作為 HOLD 並降低信心水準。
"""

import pandas as pd
from utils.logger import get_logger

logger = get_logger("decision.risk_manager")


class RiskFlag:
    """單一風險旗標"""

    def __init__(self, name: str, description: str, severity: str = "WARNING"):
        self.name = name
        self.description = description
        self.severity = severity  # WARNING / CRITICAL

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "severity": self.severity,
        }


class RiskManager:
    """
    風險管理器
    提供波動度、連續信號、市場環境等檢查。
    """

    def check_volatility(self, prices_df: pd.DataFrame,
                         threshold: float = 0.05) -> list:
        """
        檢查 ATR (Average True Range) 是否異常偏高。

        Args:
            prices_df: 價格 DataFrame，需包含 High, Low, Close 欄位
            threshold: ATR 佔收盤價比例的警戒門檻 (預設 5%)

        Returns:
            觸發的 RiskFlag 列表
        """
        flags = []

        if prices_df is None or prices_df.empty or len(prices_df) < 15:
            return flags

        try:
            df = prices_df.copy()
            high = df["High"]
            low = df["Low"]
            close = df["Close"]
            prev_close = close.shift(1)

            # True Range 三元素取最大值
            tr1 = high - low
            tr2 = (high - prev_close).abs()
            tr3 = (low - prev_close).abs()
            true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

            # 14 日 ATR
            atr_14 = true_range.rolling(window=14).mean().iloc[-1]
            last_close = close.iloc[-1]

            if last_close > 0:
                atr_ratio = atr_14 / last_close
                if atr_ratio > threshold:
                    flags.append(RiskFlag(
                        name="HIGH_VOLATILITY",
                        description=(
                            f"ATR/Close 比率 {atr_ratio:.4f} 超過門檻 {threshold:.4f}，"
                            f"市場波動度異常偏高"
                        ),
                        severity="WARNING",
                    ))
                    logger.warning(
                        "波動度警告: ATR 比率 %.4f > 門檻 %.4f",
                        atr_ratio, threshold,
                    )
        except Exception as e:
            logger.error("波動度檢查失敗: %s", e)

        return flags

    def check_consecutive_signals(self, db, ticker: str, interval: str,
                                  max_consecutive: int = 3) -> list:
        """
        檢查最近是否有過多同方向的連續信號。
        避免在趨勢末端持續發出相同方向的決策。

        Args:
            db: Database 實例
            ticker: 股票代碼
            interval: 時間間隔
            max_consecutive: 允許的最大連續同向信號數量

        Returns:
            觸發的 RiskFlag 列表
        """
        flags = []

        try:
            decisions_df = db.get_decisions(ticker, interval, limit=max_consecutive + 1)
            if decisions_df is None or decisions_df.empty:
                return flags

            actions = decisions_df["action"].tolist()
            if len(actions) < max_consecutive:
                return flags

            # 檢查最近 N 筆是否全為相同的非 HOLD 動作
            recent = actions[:max_consecutive]
            if len(set(recent)) == 1 and recent[0] in ("BUY", "SELL"):
                flags.append(RiskFlag(
                    name="CONSECUTIVE_SIGNALS",
                    description=(
                        f"最近 {max_consecutive} 次決策皆為 {recent[0]}，"
                        f"可能處於趨勢末端，建議謹慎操作"
                    ),
                    severity="WARNING",
                ))
                logger.warning(
                    "連續信號警告: 最近 %d 次皆為 %s",
                    max_consecutive, recent[0],
                )
        except Exception as e:
            logger.error("連續信號檢查失敗: %s", e)

        return flags

    def check_market_environment(self, db, vix_threshold: float = 30.0) -> list:
        """
        檢查 VIX 恐慌指數是否過高。
        若資料庫中有 VIX 相關價格資料，則進行檢查。

        Args:
            db: Database 實例
            vix_threshold: VIX 警戒門檻 (預設 30)

        Returns:
            觸發的 RiskFlag 列表
        """
        flags = []

        try:
            # 嘗試從資料庫取得 VIX 資料 (使用 ^VIX 代碼)
            vix_df = db.get_prices("^VIX", interval="1d")
            if vix_df is None or vix_df.empty:
                # 沒有 VIX 資料，跳過檢查
                return flags

            latest_vix = vix_df["Close"].iloc[-1]
            if latest_vix >= vix_threshold:
                flags.append(RiskFlag(
                    name="HIGH_VIX",
                    description=(
                        f"VIX 指數 {latest_vix:.2f} 超過恐慌門檻 {vix_threshold:.1f}，"
                        f"市場處於恐慌狀態"
                    ),
                    severity="CRITICAL",
                ))
                logger.warning(
                    "市場恐慌警告: VIX %.2f >= 門檻 %.1f",
                    latest_vix, vix_threshold,
                )
        except Exception as e:
            logger.error("市場環境檢查失敗: %s", e)

        return flags

    def evaluate(self, decision_result: dict, prices_df: pd.DataFrame,
                 db, ticker: str, interval: str) -> dict:
        """
        執行所有風險檢查，並視需要降級決策。

        Args:
            decision_result: 來自 RuleBasedDecision 的決策結果字典
                             (需包含 action, confidence, risk_level 等欄位)
            prices_df: 價格 DataFrame
            db: Database 實例
            ticker: 股票代碼
            interval: 時間間隔

        Returns:
            更新後的 decision_result 字典，新增 risk_flags 欄位
        """
        all_flags = []

        # 執行各項檢查
        all_flags.extend(self.check_volatility(prices_df))
        all_flags.extend(self.check_consecutive_signals(db, ticker, interval))
        all_flags.extend(self.check_market_environment(db))

        # 將風險旗標寫入結果
        decision_result["risk_flags"] = [f.to_dict() for f in all_flags]

        if all_flags:
            original_action = decision_result.get("action", "HOLD")
            original_confidence = decision_result.get("confidence", 0.0)

            # 有 CRITICAL 旗標則直接降級
            has_critical = any(f.severity == "CRITICAL" for f in all_flags)
            warning_count = sum(1 for f in all_flags if f.severity == "WARNING")

            if has_critical or warning_count >= 2:
                # 強制降級為 HOLD
                decision_result["action"] = "HOLD"
                decision_result["confidence"] = round(
                    original_confidence * 0.3, 4
                )
                decision_result["risk_level"] = "HIGH"
                logger.info(
                    "風險降級: %s -> HOLD (原始信心 %.2f -> %.2f)",
                    original_action, original_confidence,
                    decision_result["confidence"],
                )
            elif warning_count == 1:
                # 單一警告: 降低信心但保留動作
                decision_result["confidence"] = round(
                    original_confidence * 0.6, 4
                )
                if decision_result.get("risk_level") == "LOW":
                    decision_result["risk_level"] = "MEDIUM"
                logger.info(
                    "風險警告: 信心降低 %.2f -> %.2f",
                    original_confidence, decision_result["confidence"],
                )

        return decision_result
