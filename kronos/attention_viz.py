import numpy as np
from typing import Dict, List


class TemporalAttentionAnalyzer:
    """
    時序注意力代理分析器。
    由於無法直接取得 Transformer 的 attention weights，
    此模組使用基於相關性的時序重要性分析作為替代方案，
    透過歷史價格模式與預測分布之間的關聯來推斷注意力分配。
    """

    def __init__(self):
        pass

    def compute_temporal_importance(self, all_samples: list, mean_pred: list,
                                   historical_close: list) -> Dict:
        """
        分析哪些歷史時間步驟與預測變異最相關。

        方法概述:
        1. 計算每個歷史步驟的局部價格梯度
        2. 計算價格動量與預測標準差的滑動窗口相關性
        3. 建立 heatmap: 使用餘弦相似度衡量 (hist_i, pred_j) 配對關係
        4. 找出前 5 個關鍵驅動步驟

        Args:
            all_samples: 多次採樣預測結果清單，每個元素為 (pred_len,) 陣列
            mean_pred: 平均預測值陣列 (pred_len,)
            historical_close: 歷史收盤價陣列 (hist_len,)

        Returns:
            dict 包含:
                - temporal_importance: 每個歷史步驟的重要性分數 (1D)
                - heatmap_data: 2D 陣列 (hist_len x pred_len) 供熱力圖使用
                - key_driver_indices: 前 5 個最重要歷史步驟的索引
                - pred_variance: 每個預測步驟的變異數
        """
        samples = np.array(all_samples, dtype=float)   # (n_samples, pred_len)
        hist = np.array(historical_close, dtype=float)  # (hist_len,)
        mean_p = np.array(mean_pred, dtype=float)        # (pred_len,)

        pred_len = samples.shape[1]
        hist_len = len(hist)

        # 計算每個預測步驟的標準差
        pred_std = np.std(samples, axis=0)   # (pred_len,)
        pred_variance = np.var(samples, axis=0)

        # 計算歷史價格的局部梯度（每個點的近似微分）
        hist_gradient = np.zeros(hist_len)
        for i in range(hist_len):
            # 中心差分法計算局部梯度
            if i == 0:
                hist_gradient[i] = hist[1] - hist[0] if hist_len > 1 else 0.0
            elif i == hist_len - 1:
                hist_gradient[i] = hist[-1] - hist[-2]
            else:
                hist_gradient[i] = (hist[i + 1] - hist[i - 1]) / 2.0

        # 正規化梯度
        grad_norm = np.linalg.norm(hist_gradient)
        if grad_norm > 0:
            hist_gradient_normalized = hist_gradient / grad_norm
        else:
            hist_gradient_normalized = hist_gradient

        # 計算預測方向的梯度
        pred_gradient = np.zeros(pred_len)
        for j in range(pred_len):
            if j == 0:
                pred_gradient[j] = mean_p[1] - mean_p[0] if pred_len > 1 else 0.0
            elif j == pred_len - 1:
                pred_gradient[j] = mean_p[-1] - mean_p[-2]
            else:
                pred_gradient[j] = (mean_p[j + 1] - mean_p[j - 1]) / 2.0

        # 建立 heatmap: (hist_len x pred_len)
        # 使用局部價格梯度與預測梯度的餘弦相似度
        heatmap = np.zeros((hist_len, pred_len))

        for h in range(hist_len):
            # 取局部窗口特徵向量 (以此步驟為中心)
            window_radius = 2
            w_start = max(0, h - window_radius)
            w_end = min(hist_len, h + window_radius + 1)
            local_window = hist[w_start:w_end]

            # 局部梯度向量
            if len(local_window) > 1:
                local_grad = np.diff(local_window)
            else:
                local_grad = np.array([0.0])

            local_grad_norm = np.linalg.norm(local_grad) + 1e-8

            for p in range(pred_len):
                # 預測局部梯度向量
                p_start = max(0, p - 1)
                p_end = min(pred_len, p + 2)
                pred_local = mean_p[p_start:p_end]

                if len(pred_local) > 1:
                    pred_local_grad = np.diff(pred_local)
                else:
                    pred_local_grad = np.array([0.0])

                pred_local_norm = np.linalg.norm(pred_local_grad) + 1e-8

                # 餘弦相似度：取兩向量中較短的長度進行計算
                min_len = min(len(local_grad), len(pred_local_grad))
                if min_len > 0:
                    a = local_grad[:min_len]
                    b = pred_local_grad[:min_len]
                    cos_sim = np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8)
                else:
                    cos_sim = 0.0

                # 加入時間衰減：越近期的歷史步驟越重要
                time_decay = np.exp(-0.03 * (hist_len - 1 - h))

                # 加入預測不確定性加權
                uncertainty_weight = pred_std[p] / (np.mean(pred_std) + 1e-8)

                heatmap[h, p] = cos_sim * time_decay * uncertainty_weight

        # 正規化 heatmap 至 [-1, 1]
        heatmap_abs_max = np.max(np.abs(heatmap))
        if heatmap_abs_max > 0:
            heatmap = heatmap / heatmap_abs_max

        # 計算滑動窗口相關性：歷史局部動量 vs 預測分散程度
        # 用於產生 1D 的 temporal_importance
        temporal_importance = np.zeros(hist_len)

        # 計算每個歷史步驟的局部價格動量特徵
        for i in range(hist_len):
            w_start = max(0, i - 3)
            w_end = min(hist_len, i + 4)
            local_prices = hist[w_start:w_end]

            # 特徵 1: 局部波動性
            local_volatility = np.std(local_prices) / (np.mean(np.abs(local_prices)) + 1e-8)

            # 特徵 2: 局部趨勢方向性
            if len(local_prices) > 1:
                x = np.arange(len(local_prices))
                slope = np.polyfit(x, local_prices, 1)[0]
                trend_strength = abs(slope) / (np.std(local_prices) + 1e-8)
            else:
                trend_strength = 0.0

            # 特徵 3: 時間衰減
            time_weight = np.exp(-0.05 * (hist_len - 1 - i))

            # 綜合重要性 = 波動性 * 趨勢強度 * 時間權重
            temporal_importance[i] = (local_volatility + trend_strength) * time_weight

        # 加入 heatmap 跨預測步驟的平均影響
        heatmap_importance = np.mean(np.abs(heatmap), axis=1)
        temporal_importance = 0.5 * temporal_importance + 0.5 * heatmap_importance

        # 正規化至 [0, 1]
        imp_max = np.max(temporal_importance)
        if imp_max > 0:
            temporal_importance = temporal_importance / imp_max

        # 找出前 5 個最重要的歷史步驟
        n_top = min(5, hist_len)
        key_indices = np.argsort(temporal_importance)[-n_top:][::-1]

        return {
            'temporal_importance': temporal_importance.tolist(),
            'heatmap_data': heatmap.tolist(),
            'key_driver_indices': key_indices.tolist(),
            'pred_variance': pred_variance.tolist()
        }

    def compute_price_pattern_influence(self, historical_close: list,
                                        pred_close: list) -> Dict:
        """
        分析哪些近期價格模式對預測方向影響最大。

        偵測模式:
        - 動量: 5 日、10 日、20 日報酬率
        - 波動性體制: 近期 vs 歷史波動性比較
        - 支撐/壓力位接近度: 價格在近期範圍中的位置

        Args:
            historical_close: 歷史收盤價清單
            pred_close: 預測收盤價清單

        Returns:
            dict 包含各模式的影響分析、分數及描述
        """
        hist = np.array(historical_close, dtype=float)
        pred = np.array(pred_close, dtype=float)

        if len(hist) < 5 or len(pred) < 2:
            return {
                'patterns': {},
                'dominant_pattern': 'insufficient_data',
                'pattern_scores': {}
            }

        # 預測方向與報酬率
        pred_direction = pred[-1] - pred[0]
        pred_return = pred_direction / (abs(pred[0]) + 1e-8)

        patterns = {}
        pattern_scores = {}

        # --- 1. 短期動量 (5 日) ---
        momentum_5d = (hist[-1] - hist[-5]) / (abs(hist[-5]) + 1e-8)
        alignment_5d = float(np.sign(momentum_5d) * np.sign(pred_return))
        patterns['momentum_5d'] = {
            'value': float(momentum_5d),
            'description': f"5-day return: {momentum_5d * 100:.2f}%, "
                           f"{'consistent' if alignment_5d > 0 else 'divergent'} with prediction",
            'alignment_with_prediction': alignment_5d
        }
        pattern_scores['momentum_5d'] = abs(float(momentum_5d))

        # --- 2. 中期動量 (10 日) ---
        if len(hist) >= 10:
            momentum_10d = (hist[-1] - hist[-10]) / (abs(hist[-10]) + 1e-8)
            alignment_10d = float(np.sign(momentum_10d) * np.sign(pred_return))
            patterns['momentum_10d'] = {
                'value': float(momentum_10d),
                'description': f"10-day return: {momentum_10d * 100:.2f}%, "
                               f"{'consistent' if alignment_10d > 0 else 'divergent'} with prediction",
                'alignment_with_prediction': alignment_10d
            }
            pattern_scores['momentum_10d'] = abs(float(momentum_10d))

        # --- 3. 長期動量 (20 日) ---
        if len(hist) >= 20:
            momentum_20d = (hist[-1] - hist[-20]) / (abs(hist[-20]) + 1e-8)
            alignment_20d = float(np.sign(momentum_20d) * np.sign(pred_return))
            patterns['momentum_20d'] = {
                'value': float(momentum_20d),
                'description': f"20-day return: {momentum_20d * 100:.2f}%, "
                               f"{'consistent' if alignment_20d > 0 else 'divergent'} with prediction",
                'alignment_with_prediction': alignment_20d
            }
            pattern_scores['momentum_20d'] = abs(float(momentum_20d))

        # --- 4. 波動性體制 ---
        if len(hist) >= 20:
            # 近期波動性 (最近 20 天的日報酬標準差)
            recent_returns = np.diff(hist[-20:]) / (np.abs(hist[-21:-1]) + 1e-8)
            recent_vol = float(np.std(recent_returns))

            # 歷史波動性 (若有足夠資料)
            if len(hist) >= 40:
                older_returns = np.diff(hist[-40:-20]) / (np.abs(hist[-41:-21]) + 1e-8)
                older_vol = float(np.std(older_returns))
            else:
                older_vol = recent_vol

            vol_change = (recent_vol - older_vol) / (older_vol + 1e-8)

            if vol_change > 0.1:
                vol_desc = "Volatility expanding - higher uncertainty expected"
            elif vol_change < -0.1:
                vol_desc = "Volatility contracting - lower uncertainty expected"
            else:
                vol_desc = "Volatility stable"

            patterns['volatility_regime'] = {
                'recent_volatility': recent_vol,
                'vol_change': float(vol_change),
                'description': vol_desc
            }
            pattern_scores['volatility_regime'] = abs(float(vol_change))

        # --- 5. 支撐/壓力位接近度 ---
        if len(hist) >= 20:
            recent_high = float(np.max(hist[-20:]))
            recent_low = float(np.min(hist[-20:]))
            price_range = recent_high - recent_low

            if price_range > 0:
                position_in_range = (hist[-1] - recent_low) / price_range
            else:
                position_in_range = 0.5

            near_resistance = bool(position_in_range > 0.8)
            near_support = bool(position_in_range < 0.2)

            if near_resistance:
                sr_desc = "Near resistance level - potential reversal or breakout"
            elif near_support:
                sr_desc = "Near support level - potential bounce or breakdown"
            else:
                sr_desc = f"Mid-range (position: {position_in_range:.1%})"

            patterns['support_resistance'] = {
                'position_in_range': float(position_in_range),
                'near_resistance': near_resistance,
                'near_support': near_support,
                'description': sr_desc
            }
            pattern_scores['support_resistance'] = abs(float(position_in_range - 0.5))

        # 判斷主導模式
        if pattern_scores:
            dominant = max(pattern_scores, key=pattern_scores.get)
        else:
            dominant = 'none'

        # 正規化分數
        total = sum(pattern_scores.values()) + 1e-8
        normalized_scores = {k: v / total for k, v in pattern_scores.items()}

        return {
            'patterns': patterns,
            'dominant_pattern': dominant,
            'pattern_scores': normalized_scores,
            'prediction_return': float(pred_return)
        }
