import sqlite3
import pandas as pd
import json
from datetime import datetime
import os

class Database:
    def __init__(self, db_path="data/stock_advisor.db"):
        self.db_path = db_path
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Create generic prices table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS prices (
                    ticker TEXT,
                    interval TEXT,
                    date TEXT,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume INTEGER,
                    PRIMARY KEY (ticker, interval, date)
                )
            ''')
            
            # We can optionally drop daily_prices to save space, but we'll leave it or ignore it.
            cursor.execute('DROP TABLE IF EXISTS daily_prices')
            
            # Create predictions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS predictions (
                    ticker TEXT,
                    date TEXT,
                    interval TEXT,
                    pred_len INTEGER,
                    up_prob REAL,
                    score_k REAL,
                    raw_output TEXT,
                    PRIMARY KEY (ticker, date, interval)
                )
            ''')
            
            # Create decisions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS decisions (
                    ticker TEXT,
                    date TEXT,
                    interval TEXT,
                    action TEXT,
                    final_score REAL,
                    kronos_contrib REAL,
                    ta_contrib REAL,
                    json_data TEXT,
                    PRIMARY KEY (ticker, date, interval)
                )
            ''')
            
            # Create ta_reports table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ta_reports (
                    ticker TEXT,
                    date TEXT,
                    interval TEXT,
                    json_data TEXT,
                    PRIMARY KEY (ticker, date, interval)
                )
            ''')

            # Watchlist - 觀察清單
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS watchlist (
                    ticker TEXT PRIMARY KEY,
                    added_date TEXT,
                    notes TEXT
                )
            ''')

            # Scheduler Logs - 排程執行紀錄
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS scheduler_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT,
                    run_time TEXT,
                    status TEXT,
                    error_msg TEXT,
                    duration_sec REAL
                )
            ''')

            conn.commit()

    # ------------------------------------------------------------------
    # Prices 相關方法
    # ------------------------------------------------------------------

    def insert_prices(self, ticker: str, interval: str, df: pd.DataFrame):
        """
        Insert prices from a pandas DataFrame.
        Expects index to be Date/Datetime, columns: Open, High, Low, Close, Volume.
        """
        if df.empty:
            return

        with self._get_connection() as conn:
            cursor = conn.cursor()
            for index, row in df.iterrows():
                # Store datetime as string
                date_str = str(index)
                cursor.execute('''
                    INSERT OR REPLACE INTO prices (ticker, interval, date, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (ticker, interval, date_str, row['Open'], row['High'], row['Low'], row['Close'], int(row['Volume'])))
            conn.commit()

    def get_all_tickers(self) -> list:
        """
        Get a list of all unique tickers in the database.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT ticker FROM prices ORDER BY ticker ASC")
                return [row[0] for row in cursor.fetchall()]
        except Exception:
            return []

    def delete_prices(self, ticker: str, interval: str) -> bool:
        """
        Delete all price records for a specific ticker and interval.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM prices WHERE ticker = ? AND interval = ?", (ticker, interval))
                conn.commit()
            return True
        except Exception as e:
            print(f"Error deleting prices: {e}")
            return False

    def get_prices(self, ticker: str, interval: str = '1d', start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        Retrieve prices for a ticker and interval as a pandas DataFrame.
        """
        query = "SELECT date, open, high, low, close, volume FROM prices WHERE ticker = ? AND interval = ?"
        params = [ticker, interval]
        
        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)
            
        query += " ORDER BY date ASC"
        
        with self._get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=params, parse_dates=['date'])
            if not df.empty:
                df.set_index('date', inplace=True)
                df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            return df

    # ------------------------------------------------------------------
    # Predictions 相關方法
    # ------------------------------------------------------------------

    def insert_prediction(self, ticker: str, interval: str, date: str, pred_len: int, up_prob: float, score_k: float, raw_output: dict):
        """
        Save a Kronos prediction.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO predictions (ticker, date, interval, pred_len, up_prob, score_k, raw_output)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (ticker, date, interval, pred_len, up_prob, score_k, json.dumps(raw_output)))
            conn.commit()

    def get_prediction(self, ticker: str, interval: str, date: str) -> dict:
        """
        Retrieve a prediction for a specific ticker, interval, and date.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM predictions WHERE ticker = ? AND interval = ? AND date = ?", (ticker, interval, date))
            row = cursor.fetchone()
            if row:
                return {
                    "ticker": row[0],
                    "date": row[1],
                    "interval": row[2],
                    "pred_len": row[3],
                    "up_prob": row[4],
                    "score_k": row[5],
                    "raw_output": json.loads(row[6]) if row[6] else None
                }
            return None

    def get_latest_prediction(self, ticker: str, interval: str) -> dict:
        """
        Retrieve the most recent prediction for a given ticker and interval.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM predictions WHERE ticker = ? AND interval = ? "
                "ORDER BY date DESC LIMIT 1",
                (ticker, interval)
            )
            row = cursor.fetchone()
            if row:
                return {
                    "ticker": row[0],
                    "date": row[1],
                    "interval": row[2],
                    "pred_len": row[3],
                    "up_prob": row[4],
                    "score_k": row[5],
                    "raw_output": row[6]
                }
            return None

    # ------------------------------------------------------------------
    # Decisions 相關方法
    # ------------------------------------------------------------------

    def insert_decision(self, ticker: str, interval: str, date: str, decision_dict: dict):
        """
        Save a final Decision Agent result.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO decisions (ticker, date, interval, action, final_score, kronos_contrib, ta_contrib, json_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                ticker, 
                date, 
                interval,
                decision_dict.get('action'), 
                decision_dict.get('final_score'),
                decision_dict.get('contributions', {}).get('kronos', {}).get('score_contribution'),
                decision_dict.get('contributions', {}).get('trading_agents', {}).get('score_contribution'),
                json.dumps(decision_dict, ensure_ascii=False)
            ))
            conn.commit()

    def get_decisions(self, ticker: str, interval: str, limit: int = 1) -> pd.DataFrame:
        """
        Retrieve the latest decision results.
        Returns a DataFrame with columns matching the decisions table schema.
        'json_data' is selected as 'data' to match what ta_report.py expects.
        """
        query = "SELECT date, interval, action, final_score, kronos_contrib, ta_contrib, json_data as data FROM decisions WHERE ticker = ? AND interval = ? ORDER BY date DESC LIMIT ?"
        with self._get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=[ticker, interval, limit])
            return df

    # ------------------------------------------------------------------
    # TA Reports 相關方法
    # ------------------------------------------------------------------

    def insert_ta_report(self, ticker: str, interval: str, date: str, json_data: dict):
        """
        Save a standalone TA Report.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO ta_reports (ticker, date, interval, json_data)
                VALUES (?, ?, ?, ?)
            ''', (ticker, date, interval, json.dumps(json_data, ensure_ascii=False)))
            conn.commit()
            
    def get_ta_report(self, ticker: str, interval: str, date: str = None) -> dict:
        """
        Retrieve a TA Report. If date is None, gets the latest one.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if date:
                cursor.execute(
                    "SELECT json_data FROM ta_reports WHERE ticker = ? AND interval = ? AND date <= ? ORDER BY date DESC LIMIT 1",
                    (ticker, interval, date)
                )
            else:
                cursor.execute("SELECT json_data FROM ta_reports WHERE ticker = ? AND interval = ? ORDER BY date DESC LIMIT 1", (ticker, interval))
            row = cursor.fetchone()
            if row and row[0]:
                return json.loads(row[0])
            return None

    def get_all_ta_reports(self) -> list:
        """
        Retrieve all TA Reports from the database, ordered by date descending.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT ticker, interval, date, json_data FROM ta_reports ORDER BY date DESC, ticker ASC")
            rows = cursor.fetchall()
            reports = []
            for row in rows:
                try:
                    data = json.loads(row[3])
                except Exception:
                    data = {}
                reports.append({
                    "ticker": row[0],
                    "interval": row[1],
                    "date": row[2],
                    "data": data
                })
            return reports

    # ------------------------------------------------------------------
    # Watchlist 觀察清單方法
    # ------------------------------------------------------------------

    def add_to_watchlist(self, ticker: str, notes: str = '') -> bool:
        """
        將股票加入觀察清單。若已存在則更新備註。
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO watchlist (ticker, added_date, notes)
                    VALUES (?, ?, ?)
                ''', (ticker.upper(), datetime.now().strftime('%Y-%m-%d %H:%M:%S'), notes))
                conn.commit()
            return True
        except Exception as e:
            print(f"Error adding to watchlist: {e}")
            return False

    def remove_from_watchlist(self, ticker: str) -> bool:
        """
        從觀察清單移除股票。
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM watchlist WHERE ticker = ?", (ticker.upper(),))
                conn.commit()
            return True
        except Exception as e:
            print(f"Error removing from watchlist: {e}")
            return False

    def get_watchlist(self) -> list:
        """
        取得觀察清單中所有股票，回傳 list of dict。
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT ticker, added_date, notes FROM watchlist ORDER BY added_date DESC")
                rows = cursor.fetchall()
                return [
                    {"ticker": row[0], "added_date": row[1], "notes": row[2]}
                    for row in rows
                ]
        except Exception:
            return []

    def is_in_watchlist(self, ticker: str) -> bool:
        """
        檢查股票是否在觀察清單中。
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM watchlist WHERE ticker = ?", (ticker.upper(),))
                return cursor.fetchone() is not None
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Scheduler Logs 排程紀錄方法
    # ------------------------------------------------------------------

    def insert_scheduler_log(self, ticker: str, run_time: str, status: str,
                             error_msg: str = '', duration_sec: float = 0.0) -> bool:
        """
        插入一筆排程執行紀錄。
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO scheduler_logs (ticker, run_time, status, error_msg, duration_sec)
                    VALUES (?, ?, ?, ?, ?)
                ''', (ticker, run_time, status, error_msg, duration_sec))
                conn.commit()
            return True
        except Exception as e:
            print(f"Error inserting scheduler log: {e}")
            return False

    def get_scheduler_logs(self, limit: int = 50) -> list:
        """
        取得最近的排程執行紀錄，回傳 list of dict。
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, ticker, run_time, status, error_msg, duration_sec "
                    "FROM scheduler_logs ORDER BY id DESC LIMIT ?", (limit,)
                )
                rows = cursor.fetchall()
                return [
                    {
                        "id": row[0],
                        "ticker": row[1],
                        "run_time": row[2],
                        "status": row[3],
                        "error_msg": row[4],
                        "duration_sec": row[5]
                    }
                    for row in rows
                ]
        except Exception:
            return []
