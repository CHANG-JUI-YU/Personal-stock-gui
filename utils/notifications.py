"""
Notification System - 通知系統
提供桌面通知與訊號變動追蹤功能。
"""
import os
import platform
from datetime import datetime


def send_desktop_notification(title: str, message: str) -> bool:
    """
    發送桌面通知。
    優先使用 plyer，若不可用則使用 Windows ctypes MessageBox。

    Parameters
    ----------
    title : str
        通知標題
    message : str
        通知內容

    Returns
    -------
    bool : 是否成功發送
    """
    # 嘗試使用 plyer
    try:
        from plyer import notification
        notification.notify(
            title=title,
            message=message,
            app_name="KRONOS_X_AGENT",
            timeout=10,
        )
        return True
    except ImportError:
        pass
    except Exception as e:
        print(f"plyer 通知失敗: {e}")

    # Windows 備援: ctypes MessageBox
    if platform.system() == "Windows":
        try:
            import ctypes
            # MB_OK | MB_ICONINFORMATION | MB_SYSTEMMODAL
            ctypes.windll.user32.MessageBoxW(
                0,
                str(message),
                str(title),
                0x00000040 | 0x00001000
            )
            return True
        except Exception as e:
            print(f"ctypes 通知失敗: {e}")

    print(f"[Notification] {title}: {message}")
    return False


class NotificationManager:
    """
    訊號變動追蹤管理器。
    記錄每檔股票的最新操作建議，當建議改變時發送通知。
    """

    def __init__(self):
        # 儲存每檔股票的上次操作: {ticker: last_action}
        self._state = {}

    def check_and_notify(self, ticker: str, new_action: str, previous_action: str = None) -> bool:
        """
        檢查操作建議是否發生變化，若有變化則發送桌面通知。

        Parameters
        ----------
        ticker : str
            股票代碼
        new_action : str
            新的操作建議 (BUY / SELL / HOLD)
        previous_action : str or None
            前次操作建議。若為 None，則從內部狀態取得。

        Returns
        -------
        bool : 是否有發送通知 (即是否發生變化)
        """
        ticker = ticker.upper()
        new_action = new_action.upper() if new_action else "N/A"

        # 若未提供 previous_action，使用內部追蹤的狀態
        if previous_action is None:
            previous_action = self._state.get(ticker)
        else:
            previous_action = previous_action.upper()

        # 更新內部狀態
        self._state[ticker] = new_action

        # 首次紀錄，不發送通知
        if previous_action is None:
            return False

        # 操作未變更，不發送
        if new_action == previous_action:
            return False

        # 操作發生變化，發送通知
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 建構通知訊息
        action_labels = {
            "BUY": "BUY (買入)",
            "SELL": "SELL (賣出)",
            "HOLD": "HOLD (持有)",
        }
        old_label = action_labels.get(previous_action, previous_action)
        new_label = action_labels.get(new_action, new_action)

        title = f"KRONOS Signal Change: {ticker}"
        message = (
            f"[{timestamp}]\n"
            f"{ticker} 操作建議變更:\n"
            f"{old_label} -> {new_label}"
        )

        send_desktop_notification(title, message)
        return True

    def get_current_action(self, ticker: str) -> str:
        """
        取得某檔股票目前追蹤的操作建議。

        Parameters
        ----------
        ticker : str
            股票代碼

        Returns
        -------
        str or None
        """
        return self._state.get(ticker.upper())

    def reset(self):
        """清除所有追蹤狀態。"""
        self._state.clear()
