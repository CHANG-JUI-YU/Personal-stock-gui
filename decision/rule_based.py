import numpy as np


class DecisionResult:
    """決策結果資料類別，包含完整的決策資訊"""

    def __init__(self, action: str, final_score: float, confidence: float,
                 risk_level: str, scores: dict, evidence: list,
                 contributions: dict):
        self.action = action
        self.final_score = final_score
        self.confidence = confidence
        self.risk_level = risk_level
        self.scores = scores
        self.evidence = evidence
        self.contributions = contributions

    def to_dict(self):
        return {
            "action": self.action,
            "final_score": self.final_score,
            "confidence": self.confidence,
            "risk_level": self.risk_level,
            "scores": self.scores,
            "evidence": self.evidence,
            "contributions": self.contributions,
        }


class RuleBasedDecision:
    """
    規則式決策引擎
    根據 Kronos、TimesFM、TradingAgents 三方分數加權計算最終決策。
    """

    # 預設權重
    DEFAULT_WEIGHTS = {
        "w_kronos": 0.35,
        "w_timesfm": 0.30,
        "w_ta": 0.35,
    }

    # 決策門檻 (基於 final_score 絕對值)
    HOLD_THRESHOLD = 15.0

    def __init__(self, w_kronos: float = None, w_timesfm: float = None,
                 w_ta: float = None):
        self.w_kronos = w_kronos if w_kronos is not None else self.DEFAULT_WEIGHTS["w_kronos"]
        self.w_timesfm = w_timesfm if w_timesfm is not None else self.DEFAULT_WEIGHTS["w_timesfm"]
        self.w_ta = w_ta if w_ta is not None else self.DEFAULT_WEIGHTS["w_ta"]

    def _determine_action(self, final_score: float) -> str:
        """根據 final_score 決定最終動作"""
        if final_score >= self.HOLD_THRESHOLD:
            return "BUY"
        elif final_score <= -self.HOLD_THRESHOLD:
            return "SELL"
        else:
            return "HOLD"

    def _calculate_confidence(self, final_score: float) -> float:
        """
        計算信心水準 (0.0 ~ 1.0)
        基於 final_score 距離 HOLD 門檻的程度。
        距離門檻越遠，信心越高；最高以 100 分封頂。
        """
        abs_score = abs(final_score)
        if abs_score < self.HOLD_THRESHOLD:
            # 在 HOLD 區間內，信心較低
            return round(abs_score / self.HOLD_THRESHOLD * 0.5, 4)
        else:
            # 超過門檻，從 0.5 線性成長到 1.0 (在 score=100 時達到 1.0)
            beyond = abs_score - self.HOLD_THRESHOLD
            max_beyond = 100.0 - self.HOLD_THRESHOLD
            confidence = 0.5 + (beyond / max_beyond) * 0.5
            return round(min(confidence, 1.0), 4)

    def _determine_risk_level(self, confidence: float, final_score: float) -> str:
        """根據信心水準與分數判斷風險等級"""
        abs_score = abs(final_score)
        if abs_score >= 60 and confidence >= 0.7:
            return "LOW"
        elif abs_score >= 30:
            return "MEDIUM"
        else:
            return "HIGH"

    def evaluate(self, kronos_pred: dict = None, tfm_pred: dict = None,
                 ta_result: dict = None) -> DecisionResult:
        evidence = []

        # ------------------------------------------------------------------
        # 1. Kronos Score (-100 to 100)
        # ------------------------------------------------------------------
        score_k = 0.0
        p_k = 0.5
        if kronos_pred:
            p_k = kronos_pred.get("up_prob", 0.5)
            score_k = (p_k - 0.5) * 200
            evidence.append(
                f"Kronos: 預測上漲機率 {p_k * 100:.1f}% -> 分數 {score_k:+.1f} (計算公式: ({p_k:.3f} - 0.5) * 200)"
            )

        # ------------------------------------------------------------------
        # 2. TimesFM Score (-100 to 100)
        # ------------------------------------------------------------------
        score_tfm = 0.0
        p_tfm = 0.5
        if tfm_pred:
            p_tfm = tfm_pred.get("up_prob", 0.5)
            uncertainty = tfm_pred.get("uncertainty_pct", 0.0)
            score_tfm = (p_tfm - 0.5) * 200
            evidence.append(
                f"TimesFM: 預測上漲機率 {p_tfm * 100:.1f}%, 不確定區間 {uncertainty * 100:.1f}% -> 分數 {score_tfm:+.1f} (計算公式: ({p_tfm:.3f} - 0.5) * 200)"
            )

        # ------------------------------------------------------------------
        # 3. TradingAgents Score (-100 to 100)
        # ------------------------------------------------------------------
        score_ta = 0.0
        pm_reasoning = ""
        if ta_result and "agents" in ta_result:
            pm_data = ta_result["agents"].get("Portfolio Manager")
            if pm_data:
                action = pm_data.get("action", "HOLD")
                confidence = pm_data.get("confidence", 0.0)
                pm_reasoning = pm_data.get("reasoning", "")

                if action == "BUY":
                    score_ta = float(confidence * 100)
                elif action == "SELL":
                    score_ta = float(-confidence * 100)
                else:
                    score_ta = 0.0

                evidence.append(
                    f"TradingAgent: {action} (信心水準 {confidence:.2f} -> 分數 {score_ta:+.1f})"
                )

        # ------------------------------------------------------------------
        # 4. 加權總分計算
        # ------------------------------------------------------------------
        final_score = (
            self.w_kronos * score_k
            + self.w_timesfm * score_tfm
            + self.w_ta * score_ta
        )

        action = self._determine_action(final_score)
        confidence = self._calculate_confidence(final_score)
        risk_level = self._determine_risk_level(confidence, final_score)

        evidence.append(
            f"加權總分: {self.w_kronos:.2f}*{score_k:+.1f} + "
            f"{self.w_timesfm:.2f}*{score_tfm:+.1f} + "
            f"{self.w_ta:.2f}*{score_ta:+.1f} = {final_score:+.2f}"
        )
        evidence.append(
            f"決策: {action} (信心 {confidence:.2%}, 風險 {risk_level})"
        )

        # ------------------------------------------------------------------
        # 4.5 引入 Portfolio Manager 分析報告意見
        # ------------------------------------------------------------------
        if pm_reasoning:
            evidence.append("=== Portfolio Manager 決策報告意見 ===")
            evidence.append(pm_reasoning)

        # ------------------------------------------------------------------
        # 5. 各模型貢獻度
        # ------------------------------------------------------------------
        contributions = {
            "kronos": {
                "weight": self.w_kronos,
                "raw_score": score_k,
                "score_contribution": round(self.w_kronos * score_k, 4),
            },
            "timesfm": {
                "weight": self.w_timesfm,
                "raw_score": score_tfm,
                "score_contribution": round(self.w_timesfm * score_tfm, 4),
            },
            "trading_agents": {
                "weight": self.w_ta,
                "raw_score": score_ta,
                "score_contribution": round(self.w_ta * score_ta, 4),
            },
        }

        # ------------------------------------------------------------------
        # 6. 組裝分數字典
        # ------------------------------------------------------------------
        scores = {
            "kronos": {
                "raw_p": p_k,
                "score": score_k,
            },
            "timesfm": {
                "raw_p": p_tfm,
                "score": score_tfm,
            },
            "trading_agents": {
                "detail": (
                    ta_result["agents"]
                    if ta_result and "agents" in ta_result
                    else {}
                ),
                "score": score_ta,
            },
        }

        return DecisionResult(
            action=action,
            final_score=round(final_score, 4),
            confidence=confidence,
            risk_level=risk_level,
            scores=scores,
            evidence=evidence,
            contributions=contributions,
        )
