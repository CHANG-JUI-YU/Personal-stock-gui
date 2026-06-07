import numpy as np
import pandas as pd
from typing import Dict, List


class SensitivityAnalyzer:
    """
    基於擾動的時間序列模型敏感度分析。
    透過對不同時間窗口及特徵加入隨機噪音，
    衡量各因素對預測結果的影響程度。
    """

    def __init__(self, predict_fn):
        """
        Args:
            predict_fn: 接受 DataFrame 並回傳含 'up_prob' 鍵的 dict 的可呼叫物件。
        """
        self.predict_fn = predict_fn

    def analyze_window_sensitivity(self, df: pd.DataFrame,
                                   window_sizes: List[int] = [5, 10, 20],
                                   n_perturbations: int = 10,
                                   noise_scale: float = 0.02) -> Dict:
        """
        針對每個時間窗口（最近 N 天），加入隨機噪音並衡量對預測的影響。

        Args:
            df: OHLCV 價格 DataFrame
            window_sizes: 要測試的窗口大小清單
            n_perturbations: 每個窗口的擾動次數
            noise_scale: 噪音比例（相對於標準差）

        Returns:
            dict 包含基準機率、各窗口敏感度、最敏感窗口及排名
        """
        baseline = self.predict_fn(df)
        baseline_prob = baseline.get('up_prob', 0.5)

        results = {}
        for ws in window_sizes:
            if ws > len(df):
                continue
            deltas = []
            for _ in range(n_perturbations):
                perturbed = df.copy()
                # 自動偵測收盤價欄位名稱
                col = 'Close' if 'Close' in perturbed.columns else 'close'
                noise = np.random.normal(
                    0,
                    noise_scale * perturbed[col].iloc[-ws:].std(),
                    ws
                )
                perturbed.iloc[-ws:, perturbed.columns.get_loc(col)] += noise
                prob = self.predict_fn(perturbed).get('up_prob', 0.5)
                deltas.append(abs(prob - baseline_prob))

            results[f'last_{ws}_days'] = {
                'mean_impact': float(np.mean(deltas)),
                'max_impact': float(np.max(deltas)),
                'sensitivity_score': float(np.mean(deltas) / (baseline_prob + 1e-8))
            }

        # 依影響程度排序
        ranked = sorted(results.items(), key=lambda x: x[1]['mean_impact'], reverse=True)

        return {
            'baseline_prob': baseline_prob,
            'window_sensitivities': results,
            'most_sensitive_window': ranked[0][0] if ranked else None,
            'ranking': [r[0] for r in ranked]
        }

    def analyze_feature_sensitivity(self, df: pd.DataFrame,
                                    features: List[str] = ['Open', 'High', 'Low', 'Close', 'Volume'],
                                    n_perturbations: int = 10,
                                    noise_scale: float = 0.02) -> Dict:
        """
        分析哪個 OHLCV 特徵對預測影響最大。

        Args:
            df: OHLCV 價格 DataFrame
            features: 要分析的特徵清單
            n_perturbations: 每個特徵的擾動次數
            noise_scale: 噪音比例

        Returns:
            dict 包含基準機率、各特徵影響程度及排名
        """
        baseline = self.predict_fn(df)
        baseline_prob = baseline.get('up_prob', 0.5)

        impacts = {}
        for feat in features:
            # 處理大小寫不一致的欄位名稱
            col = feat if feat in df.columns else feat.lower()
            if col not in df.columns:
                continue

            deltas = []
            for _ in range(n_perturbations):
                p = df.copy()
                noise = np.random.normal(0, noise_scale * p[col].std(), len(p))
                p[col] = p[col] + noise
                prob = self.predict_fn(p).get('up_prob', 0.5)
                deltas.append(abs(prob - baseline_prob))

            impacts[feat] = {
                'mean_impact': float(np.mean(deltas)),
                'max_impact': float(np.max(deltas)),
                'importance_score': float(np.mean(deltas))
            }

        # 正規化重要性分數
        total = sum(v['importance_score'] for v in impacts.values()) + 1e-8
        for f in impacts:
            impacts[f]['normalized_importance'] = impacts[f]['importance_score'] / total

        ranked = sorted(impacts.items(), key=lambda x: x[1]['importance_score'], reverse=True)

        return {
            'baseline_prob': baseline_prob,
            'feature_impacts': impacts,
            'ranking': [r[0] for r in ranked]
        }
