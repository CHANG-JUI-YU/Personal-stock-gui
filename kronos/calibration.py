import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from data.database import Database


class CalibrationAnalyzer:
    """
    模型校準分析器。
    評估模型預測機率與實際結果之間的一致性，
    支援 Kronos 與 TimesFM 兩種模型的校準比較。
    """

    def __init__(self, db_path='data/stock_advisor.db'):
        self.db = Database(db_path)

    def collect_prediction_outcomes(self, ticker: str, interval: str = '1d') -> pd.DataFrame:
        """
        收集歷史預測並與實際價格結果配對。

        查詢指定標的的所有預測紀錄，並對照實際價格變動方向。
        同時收集 Kronos (interval) 與 TimesFM (interval + '_tfm') 的預測。

        Args:
            ticker: 股票代碼
            interval: 時間間隔 (如 '1d', '1h')

        Returns:
            DataFrame 欄位: date, predicted_prob, actual_direction, model_type
        """
        conn = self.db._get_connection()
        try:
            # 取得 Kronos 預測 (使用原始 interval)
            kronos_df = pd.read_sql_query(
                "SELECT date, up_prob, pred_len FROM predictions "
                "WHERE ticker = ? AND interval = ? ORDER BY date ASC",
                conn, params=[ticker, interval]
            )

            # 取得 TimesFM 預測 (interval 加 '_tfm' 後綴)
            tfm_interval = interval + '_tfm'
            tfm_df = pd.read_sql_query(
                "SELECT date, up_prob, pred_len FROM predictions "
                "WHERE ticker = ? AND interval = ? ORDER BY date ASC",
                conn, params=[ticker, tfm_interval]
            )

            # 取得所有價格資料
            price_df = pd.read_sql_query(
                "SELECT date, close FROM prices "
                "WHERE ticker = ? AND interval = ? ORDER BY date ASC",
                conn, params=[ticker, interval]
            )
        finally:
            conn.close()

        if price_df.empty:
            return pd.DataFrame(columns=['date', 'predicted_prob', 'actual_direction', 'model_type'])

        # 將日期轉為 datetime 以便比對並正規化 (去除時分秒)
        price_df['date'] = pd.to_datetime(price_df['date'], format='mixed').dt.normalize()
        price_df = price_df.sort_values('date').reset_index(drop=True)

        results = []

        # 處理 Kronos 預測
        if not kronos_df.empty:
            kronos_df['date'] = pd.to_datetime(kronos_df['date'], format='mixed').dt.normalize()
            results.extend(
                self._match_predictions_with_prices(kronos_df, price_df, 'kronos')
            )

        # 處理 TimesFM 預測
        if not tfm_df.empty:
            tfm_df['date'] = pd.to_datetime(tfm_df['date'], format='mixed').dt.normalize()
            results.extend(
                self._match_predictions_with_prices(tfm_df, price_df, 'timesfm')
            )

        if not results:
            return pd.DataFrame(columns=['date', 'predicted_prob', 'actual_direction', 'model_type'])

        return pd.DataFrame(results)

    def _match_predictions_with_prices(self, pred_df: pd.DataFrame,
                                       price_df: pd.DataFrame,
                                       model_type: str) -> List[dict]:
        """
        將預測紀錄與實際價格配對，計算實際方向。

        Args:
            pred_df: 預測 DataFrame (date, up_prob, pred_len)
            price_df: 價格 DataFrame (date, close)
            model_type: 模型類型標記

        Returns:
            配對結果的 dict 清單
        """
        results = []
        for _, row in pred_df.iterrows():
            pred_date = row['date']
            pred_prob = row['up_prob']
            pred_len = int(row['pred_len']) if pd.notna(row['pred_len']) else 20

            # 找到預測日期在價格序列中的位置
            mask = price_df['date'] >= pred_date
            if not mask.any():
                continue

            start_idx = price_df[mask].index[0]
            end_idx = start_idx + pred_len

            # 確保有足夠的未來資料
            if end_idx >= len(price_df):
                continue

            start_price = price_df.loc[start_idx, 'close']
            end_price = price_df.loc[end_idx, 'close']

            # 判斷實際方向：漲 = 1, 跌 = 0
            actual_direction = 1 if end_price > start_price else 0

            results.append({
                'date': pred_date,
                'predicted_prob': pred_prob,
                'actual_direction': actual_direction,
                'model_type': model_type
            })

        return results

    def compute_calibration(self, predictions_df: pd.DataFrame, n_bins: int = 10) -> Dict:
        """
        計算校準指標。

        將預測機率分成等寬的 bins，計算每個 bin 中預測機率的平均值
        與實際準確率之間的差異。

        Args:
            predictions_df: 包含 predicted_prob 與 actual_direction 的 DataFrame
            n_bins: 分組數量

        Returns:
            dict 包含 bin_edges, bin_centers, bin_accuracies, bin_counts,
                  brier_score, ece, total_predictions
        """
        if predictions_df.empty:
            return {
                'bin_edges': [],
                'bin_centers': [],
                'bin_accuracies': [],
                'bin_counts': [],
                'brier_score': None,
                'ece': None,
                'total_predictions': 0
            }

        predicted = predictions_df['predicted_prob'].values
        actual = predictions_df['actual_direction'].values

        # 計算 Brier Score 與 ECE
        brier = self.compute_brier_score(predicted, actual)
        ece = self.compute_ece(predicted, actual, n_bins)

        # 建立等寬 bins
        bin_edges = np.linspace(0, 1, n_bins + 1)
        bin_centers = []
        bin_accuracies = []
        bin_counts = []

        for i in range(n_bins):
            lower = bin_edges[i]
            upper = bin_edges[i + 1]

            # 最後一個 bin 包含上界
            if i == n_bins - 1:
                mask = (predicted >= lower) & (predicted <= upper)
            else:
                mask = (predicted >= lower) & (predicted < upper)

            bin_count = mask.sum()
            bin_counts.append(int(bin_count))
            bin_centers.append(float((lower + upper) / 2))

            if bin_count > 0:
                bin_acc = float(actual[mask].mean())
                bin_accuracies.append(bin_acc)
            else:
                bin_accuracies.append(None)

        return {
            'bin_edges': bin_edges.tolist(),
            'bin_centers': bin_centers,
            'bin_accuracies': bin_accuracies,
            'bin_counts': bin_counts,
            'brier_score': float(brier),
            'ece': float(ece),
            'total_predictions': len(predicted)
        }

    @staticmethod
    def compute_brier_score(predicted_probs, actual_outcomes) -> float:
        """
        Brier Score = mean((predicted - actual)^2)

        完美校準的模型 Brier Score 為 0，最差為 1。

        Args:
            predicted_probs: 預測機率陣列
            actual_outcomes: 實際結果陣列 (0 或 1)

        Returns:
            Brier Score 浮點數
        """
        predicted = np.array(predicted_probs, dtype=float)
        actual = np.array(actual_outcomes, dtype=float)

        if len(predicted) == 0:
            return 0.0

        return float(np.mean((predicted - actual) ** 2))

    @staticmethod
    def compute_ece(predicted_probs, actual_outcomes, n_bins: int = 10) -> float:
        """
        Expected Calibration Error (ECE)
        ECE = sum(|acc_b - conf_b| * n_b / N)

        衡量各 bin 的預測信心度與實際準確率之間的加權絕對誤差。

        Args:
            predicted_probs: 預測機率陣列
            actual_outcomes: 實際結果陣列 (0 或 1)
            n_bins: 分組數量

        Returns:
            ECE 浮點數
        """
        predicted = np.array(predicted_probs, dtype=float)
        actual = np.array(actual_outcomes, dtype=float)
        n_total = len(predicted)

        if n_total == 0:
            return 0.0

        bin_edges = np.linspace(0, 1, n_bins + 1)
        ece = 0.0

        for i in range(n_bins):
            lower = bin_edges[i]
            upper = bin_edges[i + 1]

            if i == n_bins - 1:
                mask = (predicted >= lower) & (predicted <= upper)
            else:
                mask = (predicted >= lower) & (predicted < upper)

            bin_count = mask.sum()
            if bin_count == 0:
                continue

            # conf_b: 此 bin 的平均預測機率
            bin_pred_mean = predicted[mask].mean()
            # acc_b: 此 bin 的實際準確率
            bin_actual_mean = actual[mask].mean()

            ece += (bin_count / n_total) * abs(bin_pred_mean - bin_actual_mean)

        return float(ece)
