import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QLineEdit, QPushButton, QMessageBox, QComboBox)
from PyQt6.QtCore import Qt

class SettingsPage(QWidget):
    def __init__(self, env_path=".env"):
        super().__init__()
        self.env_path = env_path
        self.init_ui()
        self.load_env()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header = QLabel("Settings")
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: #2C3E50;")
        layout.addWidget(header)
        
        # Provider Selection
        provider_label = QLabel("LLM Provider (Important for model compatibility):")
        provider_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-top: 20px;")
        
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["openai", "deepseek", "ollama", "openrouter", "minimax", "qwen", "glm", "anthropic", "google"])
        self.provider_combo.setStyleSheet("padding: 8px; font-size: 14px; border: 1px solid #BDC3C7; border-radius: 4px;")
        
        # API Key Input
        api_layout = QVBoxLayout()
        api_label = QLabel("API Key (Required for Real TradingAgents):")
        api_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-top: 20px;")
        
        self.api_input = QLineEdit()
        self.api_input.setPlaceholderText("Enter your API Key here")
        self.api_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_input.setStyleSheet("padding: 8px; font-size: 14px; border: 1px solid #BDC3C7; border-radius: 4px;")
        
        # Base URL Input
        base_url_label = QLabel("OpenAI Base URL (Optional, for reverse proxy):")
        base_url_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-top: 20px;")
        
        self.base_url_input = QLineEdit()
        self.base_url_input.setPlaceholderText("https://api.openai.com/v1")
        self.base_url_input.setStyleSheet("padding: 8px; font-size: 14px; border: 1px solid #BDC3C7; border-radius: 4px;")
        
        # Model Input
        model_label = QLabel("OpenAI Model Name (Optional, defaults to gpt-4o):")
        model_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-top: 20px;")
        
        self.model_input = QLineEdit()
        self.model_input.setPlaceholderText("gpt-4o")
        self.model_input.setStyleSheet("padding: 8px; font-size: 14px; border: 1px solid #BDC3C7; border-radius: 4px;")
        
        # Save Button
        self.save_btn = QPushButton("Save Settings")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #27AE60; color: white; padding: 10px 20px; 
                font-weight: bold; border-radius: 4px; border: none; margin-top: 20px;
            }
            QPushButton:hover { background-color: #2ECC71; }
        """)
        self.save_btn.clicked.connect(self.save_env)
        
        api_layout.addWidget(provider_label)
        api_layout.addWidget(self.provider_combo)
        api_layout.addWidget(api_label)
        api_layout.addWidget(self.api_input)
        api_layout.addWidget(base_url_label)
        api_layout.addWidget(self.base_url_input)
        api_layout.addWidget(model_label)
        api_layout.addWidget(self.model_input)
        api_layout.addWidget(self.save_btn)
        api_layout.addStretch()
        
        layout.addLayout(api_layout)
        
    def load_env(self):
        if not os.path.exists(self.env_path):
            return
            
        with open(self.env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith("OPENAI_API_KEY="):
                    val = line.split("=", 1)[1].strip()
                    if val:
                        self.api_input.setText(val)
                elif line.startswith("OPENAI_BASE_URL="):
                    val = line.split("=", 1)[1].strip()
                    if val:
                        self.base_url_input.setText(val)
                elif line.startswith("TRADINGAGENTS_LLM_PROVIDER="):
                    val = line.split("=", 1)[1].strip()
                    if val:
                        index = self.provider_combo.findText(val)
                        if index >= 0:
                            self.provider_combo.setCurrentIndex(index)
                        else:
                            self.provider_combo.setCurrentText(val)
                elif line.startswith("OPENAI_MODEL_NAME="):
                    val = line.split("=", 1)[1].strip()
                    if val:
                        self.model_input.setText(val)
                        
    def save_env(self):
        provider = self.provider_combo.currentText().strip()
        api_key = self.api_input.text().strip()
        base_url = self.base_url_input.text().strip()
        model_name = self.model_input.text().strip()
        
        env_dict = {}
        
        if os.path.exists(self.env_path):
            with open(self.env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if "=" in line:
                        k, v = line.split("=", 1)
                        env_dict[k.strip()] = v.strip()
                        
        # Update dict
        if provider:
            env_dict["TRADINGAGENTS_LLM_PROVIDER"] = provider
        elif "TRADINGAGENTS_LLM_PROVIDER" in env_dict and not provider:
            del env_dict["TRADINGAGENTS_LLM_PROVIDER"]
            
        if api_key:
            env_dict["OPENAI_API_KEY"] = api_key
        if base_url:
            env_dict["OPENAI_BASE_URL"] = base_url
        elif "OPENAI_BASE_URL" in env_dict and not base_url:
            # allow clearing base url
            del env_dict["OPENAI_BASE_URL"]
            
        if model_name:
            env_dict["OPENAI_MODEL_NAME"] = model_name
        elif "OPENAI_MODEL_NAME" in env_dict and not model_name:
            del env_dict["OPENAI_MODEL_NAME"]
            
        # Write back
        env_dir = os.path.dirname(self.env_path)
        if env_dir:
            os.makedirs(env_dir, exist_ok=True)
            
        with open(self.env_path, 'w', encoding='utf-8') as f:
            for k, v in env_dict.items():
                f.write(f"{k}={v}\n")
            
        # Set to current environment so that it takes effect immediately without restart
        if provider:
            os.environ["TRADINGAGENTS_LLM_PROVIDER"] = provider
        elif "TRADINGAGENTS_LLM_PROVIDER" in os.environ:
            del os.environ["TRADINGAGENTS_LLM_PROVIDER"]
            
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key
        if base_url:
            os.environ["OPENAI_BASE_URL"] = base_url
        elif "OPENAI_BASE_URL" in os.environ:
            del os.environ["OPENAI_BASE_URL"]
            
        if model_name:
            os.environ["OPENAI_MODEL_NAME"] = model_name
        elif "OPENAI_MODEL_NAME" in os.environ:
            del os.environ["OPENAI_MODEL_NAME"]
            
        QMessageBox.information(self, "Success", "Settings saved successfully!\nReal TradingAgents can now use the specified API key, Base URL, and Model.")
