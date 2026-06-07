"""
KRONOS_X_AGENT 共識分析模組
分析 Kronos、TimesFM、TradingAgents 三個模型之間的一致性程度。
"""

from utils.logger import get_logger

logger = get_logger("kronos.consensus")


def _score_to_action(score: float, threshold: float = 15.0) -> str:
    """將分數轉換為動作方向"""
    if score >= threshold:
        return "BUY"
    elif score <= -threshold:
        return "SELL"
    return "HOLD"


def calculate_agreement(kronos_action: str, timesfm_action: str,
                        ta_action: str) -> float:
    """
    計算三個模型的一致性分數。

    Args:
        kronos_action: Kronos 模型動作 (BUY/HOLD/SELL)
        timesfm_action: TimesFM 模型動作 (BUY/HOLD/SELL)
        ta_action: TradingAgents 動作 (BUY/HOLD/SELL)

    Returns:
        一致性分數 0.0 ~ 1.0
        - 1.0: 三者完全一致
        - 0.67: 兩者一致
        - 0.33: 僅一者持有不同意見但無衝突 (如 BUY + HOLD)
        - 0.0: 三者完全分歧 (同時出現 BUY 與 SELL)
    """
    actions = [kronos_action, timesfm_action, ta_action]
    unique = set(actions)

    if len(unique) == 1:
        # 三者完全一致
        return 1.0

    if len(unique) == 2:
        # 檢查是否存在對立 (BUY vs SELL)
        if "BUY" in unique and "SELL" in unique:
            return 0.33
        # 兩者一致，一者為 HOLD (不衝突)
        return 0.67

    # 三者皆不同 (BUY + HOLD + SELL)
    return 0.0


def calculate_direction_consensus(scores_dict: dict) -> dict:
    """
    檢查所有模型是否同意方向 (正/負/中性)。

    Args:
        scores_dict: 分數字典，格式為::

            {
                "kronos": {"score": float},
                "timesfm": {"score": float},
                "trading_agents": {"score": float}
            }

    Returns:
        包含方向共識資訊的字典::

            {
                "all_agree": bool,
                "majority_direction": str,
                "directions": dict,
                "conflict": bool
            }
    """
    def _direction(score: float) -> str:
        if score > 5.0:
            return "BULLISH"
        elif score < -5.0:
            return "BEARISH"
        return "NEUTRAL"

    kronos_score = scores_dict.get("kronos", {}).get("score", 0.0)
    timesfm_score = scores_dict.get("timesfm", {}).get("score", 0.0)
    ta_score = scores_dict.get("trading_agents", {}).get("score", 0.0)

    directions = {
        "kronos": _direction(kronos_score),
        "timesfm": _direction(timesfm_score),
        "trading_agents": _direction(ta_score),
    }

    direction_values = list(directions.values())
    unique_dirs = set(direction_values)

    # 判斷多數方向
    from collections import Counter
    counts = Counter(direction_values)
    majority_direction = counts.most_common(1)[0][0]

    # 是否存在對立衝突 (BULLISH vs BEARISH)
    has_conflict = "BULLISH" in unique_dirs and "BEARISH" in unique_dirs

    return {
        "all_agree": len(unique_dirs) == 1,
        "majority_direction": majority_direction,
        "directions": directions,
        "conflict": has_conflict,
    }


def get_consensus_report(scores_dict: dict) -> dict:
    """
    產生完整的共識分析報告。

    Args:
        scores_dict: 分數字典，格式同 calculate_direction_consensus

    Returns:
        完整共識分析字典::

            {
                "agreement_score": float,
                "direction_consensus": dict,
                "model_actions": dict,
                "summary": str,
                "recommendation_strength": str
            }
    """
    # 從分數推導各模型的動作
    kronos_score = scores_dict.get("kronos", {}).get("score", 0.0)
    timesfm_score = scores_dict.get("timesfm", {}).get("score", 0.0)
    ta_score = scores_dict.get("trading_agents", {}).get("score", 0.0)

    kronos_action = _score_to_action(kronos_score)
    timesfm_action = _score_to_action(timesfm_score)
    ta_action = _score_to_action(ta_score)

    # 計算一致性
    agreement = calculate_agreement(kronos_action, timesfm_action, ta_action)
    direction_info = calculate_direction_consensus(scores_dict)

    model_actions = {
        "kronos": {"score": kronos_score, "action": kronos_action},
        "timesfm": {"score": timesfm_score, "action": timesfm_action},
        "trading_agents": {"score": ta_score, "action": ta_action},
    }

    # 建議強度
    if agreement >= 0.9:
        strength = "STRONG"
    elif agreement >= 0.6:
        strength = "MODERATE"
    elif agreement >= 0.3:
        strength = "WEAK"
    else:
        strength = "CONFLICTING"

    # 摘要文字
    if agreement == 1.0:
        summary = f"三個模型完全一致，皆建議 {kronos_action}，信號強度高。"
    elif agreement >= 0.67:
        majority = direction_info["majority_direction"]
        summary = f"多數模型方向一致 ({majority})，信號具有參考價值。"
    elif direction_info["conflict"]:
        summary = "模型之間存在方向衝突 (多空分歧)，建議觀望。"
    else:
        summary = "模型意見分歧，信號強度低，建議謹慎操作。"

    report = {
        "agreement_score": agreement,
        "direction_consensus": direction_info,
        "model_actions": model_actions,
        "summary": summary,
        "recommendation_strength": strength,
    }

    logger.info(
        "共識分析: 一致性=%.2f, 方向=%s, 強度=%s",
        agreement,
        direction_info["majority_direction"],
        strength,
    )

    return report
