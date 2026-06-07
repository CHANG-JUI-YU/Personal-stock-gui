import os
import subprocess
from PyQt6.QtCore import QThread, pyqtSignal

class MiroFishServerThread(QThread):
    server_ready = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.process = None

    def run(self):
        # 啟動 MiroFish 前端伺服器 (使用 Vite 的預設 5173 port)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        frontend_dir = os.path.join(project_root, "third_party", "MiroFish", "frontend")
        
        try:
            # 由於我們沒有完整的後端相依環境，我們在此僅啟動前端 dev server 作為展示
            self.process = subprocess.Popen(
                ["npm", "run", "dev", "--", "--port", "8050", "--strictPort"],
                cwd=frontend_dir,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            # 延長等待時間至 6 秒，確保 Vite 有充足時間啟動完成
            self.msleep(6000)
            self.server_ready.emit()
            
            # 保持執行緒存活
            self.process.wait()
        except Exception as e:
            print(f"啟動 MiroFish 伺服器失敗: {e}")

    def stop(self):
        if self.process:
            self.process.terminate()
            self.process.kill()
