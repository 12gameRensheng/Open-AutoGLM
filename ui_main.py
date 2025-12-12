#!/usr/bin/env python3
"""
Phone Agent GUI - AI-powered phone automation with graphical interface.

Features:
- Auto-detect ADB installation
- Auto-configure ADB environment variables
- Auto-connect device and install ADBKeyboard
- User-friendly task execution interface
"""

import os
import sys
import io
import shutil
import subprocess
import threading
import zipfile
import json
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

# Windows 下隐藏控制台窗口的标志
CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

# Add parent directory to path for imports
# 判断是否为打包后的 exe
if getattr(sys, 'frozen', False):
    # 打包后的 exe，使用 exe 所在目录
    SCRIPT_DIR = Path(sys.executable).parent.resolve()
else:
    # 开发环境，使用脚本所在目录
    SCRIPT_DIR = Path(__file__).parent.resolve()

PARENT_DIR = SCRIPT_DIR.parent
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

# Config file for saving user preferences
CONFIG_FILE = SCRIPT_DIR / "ui_config.json"


def load_env_file(verbose=False):
    """Load .env file manually without external dependency."""
    env_path = SCRIPT_DIR / ".env"
    if verbose:
        print(f"[DEBUG] 尝试加载 .env 文件: {env_path}")
        print(f"[DEBUG] 文件存在: {env_path.exists()}")

    if env_path.exists():
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        if key and value:
                            os.environ[key] = value  # 强制覆盖
                            if verbose:
                                print(f"[DEBUG] 设置环境变量: {key}={value[:10]}...")
        except Exception as e:
            if verbose:
                print(f"[DEBUG] 加载 .env 文件失败: {e}")


def reload_env_file():
    """Reload .env file to get latest values."""
    load_env_file(verbose=True)


# Load environment variables
load_env_file()


class TextRedirector(io.StringIO):
    """Redirect stdout/stderr to a text widget."""

    def __init__(self, text_widget, tag="stdout"):
        super().__init__()
        self.text_widget = text_widget
        self.tag = tag

    def write(self, string):
        if string.strip():
            self.text_widget.after(0, self._write, string)

    def _write(self, string):
        self.text_widget.config(state=tk.NORMAL)
        self.text_widget.insert(tk.END, string, self.tag)
        if not string.endswith('\n'):
            self.text_widget.insert(tk.END, '\n')
        self.text_widget.see(tk.END)
        self.text_widget.config(state=tk.DISABLED)

    def flush(self):
        pass


class Theme:
    """Simple clean theme."""

    # Colors
    BG_MAIN = "#f5f5f5"
    BG_CARD = "#ffffff"
    BG_INPUT = "#ffffff"
    BG_LOG = "#fafafa"

    BORDER = "#e0e0e0"
    ACCENT = "#1976d2"
    ACCENT_HOVER = "#1565c0"

    SUCCESS = "#2e7d32"
    WARNING = "#f57c00"
    ERROR = "#c62828"
    INFO = "#1976d2"

    TEXT_PRIMARY = "#212121"
    TEXT_SECONDARY = "#757575"
    TEXT_MUTED = "#9e9e9e"

    # Fonts
    FONT_FAMILY = "Microsoft YaHei"
    FONT_FAMILY_MONO = "Consolas"

    @classmethod
    def apply(cls, root):
        """Apply theme styling."""
        style = ttk.Style()
        style.theme_use('clam')

        root.configure(bg=cls.BG_MAIN)

        # Frame
        style.configure("TFrame", background=cls.BG_MAIN)
        style.configure("Card.TFrame", background=cls.BG_CARD)

        # Labels
        style.configure("TLabel", background=cls.BG_MAIN, foreground=cls.TEXT_PRIMARY,
                       font=(cls.FONT_FAMILY, 10))
        style.configure("Title.TLabel", background=cls.BG_MAIN, foreground=cls.TEXT_PRIMARY,
                       font=(cls.FONT_FAMILY, 16, "bold"))
        style.configure("Subtitle.TLabel", background=cls.BG_MAIN, foreground=cls.TEXT_SECONDARY,
                       font=(cls.FONT_FAMILY, 10))
        style.configure("Card.TLabel", background=cls.BG_CARD, foreground=cls.TEXT_PRIMARY,
                       font=(cls.FONT_FAMILY, 10))
        style.configure("Success.TLabel", background=cls.BG_CARD, foreground=cls.SUCCESS,
                       font=(cls.FONT_FAMILY, 10))
        style.configure("Error.TLabel", background=cls.BG_CARD, foreground=cls.ERROR,
                       font=(cls.FONT_FAMILY, 10))
        style.configure("Warning.TLabel", background=cls.BG_CARD, foreground=cls.WARNING,
                       font=(cls.FONT_FAMILY, 10))
        style.configure("BigStatus.TLabel", background=cls.BG_MAIN, foreground=cls.SUCCESS,
                       font=(cls.FONT_FAMILY, 12, "bold"))

        # LabelFrame
        style.configure("Card.TLabelframe", background=cls.BG_CARD)
        style.configure("Card.TLabelframe.Label", background=cls.BG_CARD,
                       foreground=cls.ACCENT, font=(cls.FONT_FAMILY, 10, "bold"))

        # Buttons - 使用 TButton 的默认样式，只修改特定属性
        style.configure("TButton", font=(cls.FONT_FAMILY, 9), padding=(10, 5))

        # Secondary button
        style.configure("Secondary.TButton", font=(cls.FONT_FAMILY, 9), padding=(10, 5))

        return style


class StatusIndicator(ttk.Frame):
    """A status indicator widget with colored circle."""

    def __init__(self, parent, label_text, **kwargs):
        super().__init__(parent, style="Card.TFrame", **kwargs)

        self.label = ttk.Label(self, text=label_text, style="Card.TLabel", width=12, anchor="w")
        self.label.pack(side=tk.LEFT, padx=(10, 5))

        # Status indicator circle
        self.canvas = tk.Canvas(self, width=12, height=12, bg=Theme.BG_CARD, highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, padx=5)
        self.indicator = self.canvas.create_oval(2, 2, 10, 10, fill=Theme.TEXT_MUTED, outline="")

        self.status_label = ttk.Label(self, text="检测中...", style="Card.TLabel", width=22, anchor="w")
        self.status_label.pack(side=tk.LEFT, padx=5)

        # 使用 tk.Button 而不是 ttk.Button，这样文字颜色更可控
        self.button = tk.Button(self, text="操作", font=(Theme.FONT_FAMILY, 9),
                                bg="#e0e0e0", fg=Theme.TEXT_PRIMARY,
                                activebackground="#bdbdbd", activeforeground=Theme.TEXT_PRIMARY,
                                relief="flat", padx=10, pady=3, cursor="hand2")
        self.button.pack(side=tk.RIGHT, padx=10)

    def set_status(self, success, text):
        """Update status indicator."""
        if success is None:
            color = Theme.WARNING
            style = "Warning.TLabel"
        elif success:
            color = Theme.SUCCESS
            style = "Success.TLabel"
        else:
            color = Theme.ERROR
            style = "Error.TLabel"

        self.canvas.itemconfig(self.indicator, fill=color)
        self.status_label.config(text=text, style=style)

    def set_button(self, text, command, enabled=True):
        """Configure action button."""
        self.button.config(text=text, command=command,
                          state=tk.NORMAL if enabled else tk.DISABLED)
        if not enabled:
            self.button.config(bg="#e0e0e0", fg="#9e9e9e")
        else:
            self.button.config(bg="#e0e0e0", fg=Theme.TEXT_PRIMARY)


class PhoneAgentGUI:
    """Main GUI application."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Phone Agent - AI 智能手机自动化")
        self.root.geometry("850x700")
        self.root.minsize(750, 550)

        # Paths
        self.adb_package_path = SCRIPT_DIR / "软件包" / "platform-tools-latest-windows.zip"
        self.adb_keyboard_path = SCRIPT_DIR / "软件包" / "ADBKeyboard.apk"
        self.adb_install_dir = SCRIPT_DIR / "platform-tools"

        # Status flags
        self.adb_installed = False
        self.adb_in_path = False
        self.device_connected = False
        self.adb_keyboard_installed = False
        self.api_configured = False

        # Agent reference
        self.agent = None
        self.running = False

        # Apply theme and create widgets
        Theme.apply(self.root)
        self._create_widgets()
        self._setup_log_redirect()
        self._check_all_status()

        # 程序启动时显示免责声明（延迟100ms确保窗口已完全显示）
        self.root.after(100, lambda: self._show_disclaimer(force_agree=True))

    def _create_widgets(self):
        """Create all widgets."""
        # Main container
        self.main_frame = ttk.Frame(self.root, style="TFrame")
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)

        # ========== Header ==========
        header = ttk.Frame(self.main_frame, style="TFrame")
        header.pack(fill=tk.X, pady=(0, 15))

        title_row = ttk.Frame(header, style="TFrame")
        title_row.pack(fill=tk.X)

        ttk.Label(title_row, text="Phone Agent", style="Title.TLabel").pack(side=tk.LEFT)
        ttk.Label(title_row, text="AI 智能手机自动化控制系统",
                 style="Subtitle.TLabel").pack(side=tk.LEFT, padx=(15, 0), pady=(5, 0))

        # 免责声明按钮
        disclaimer_btn = tk.Button(title_row, text="免责声明", font=(Theme.FONT_FAMILY, 9),
                                   bg="#ff9800", fg="white", relief="flat", padx=10, pady=3,
                                   cursor="hand2", command=lambda: self._show_disclaimer(force_agree=False))
        disclaimer_btn.pack(side=tk.RIGHT, padx=(10, 0))

        # Author info
        ttk.Label(header, text="禁止非法使用 遵守法律法规 |  特点: 无需显卡 · 无需部署 · 傻瓜操作",
                 style="Subtitle.TLabel").pack(anchor="w", pady=(5, 0))

        # ========== Status Section ==========
        status_outer = ttk.Frame(self.main_frame, style="TFrame")
        status_outer.pack(fill=tk.X, pady=(0, 10))

        self.status_frame = ttk.LabelFrame(status_outer, text="环境配置状态",
                                           style="Card.TLabelframe", padding=10)
        self.status_frame.pack(fill=tk.X)

        status_inner = ttk.Frame(self.status_frame, style="Card.TFrame")
        status_inner.pack(fill=tk.X)

        # Status indicators
        self.adb_indicator = StatusIndicator(status_inner, "ADB 工具")
        self.adb_indicator.pack(fill=tk.X, pady=2)
        self.adb_indicator.set_button("自动安装", self._install_adb)

        self.path_indicator = StatusIndicator(status_inner, "环境变量")
        self.path_indicator.pack(fill=tk.X, pady=2)
        self.path_indicator.set_button("配置PATH", self._configure_path)

        self.device_indicator = StatusIndicator(status_inner, "设备连接")
        self.device_indicator.pack(fill=tk.X, pady=2)
        self.device_indicator.set_button("连接设备", self._connect_device)

        self.keyboard_indicator = StatusIndicator(status_inner, "ADB键盘")
        self.keyboard_indicator.pack(fill=tk.X, pady=2)
        self.keyboard_indicator.set_button("安装键盘", self._install_adb_keyboard)

        self.api_indicator = StatusIndicator(status_inner, "API配置")
        self.api_indicator.pack(fill=tk.X, pady=2)
        self.api_indicator.set_button("配置API", self._configure_api)

        # Refresh button
        refresh_frame = ttk.Frame(self.status_frame, style="Card.TFrame")
        refresh_frame.pack(fill=tk.X, pady=(8, 0))

        refresh_btn = tk.Button(refresh_frame, text="刷新状态", font=(Theme.FONT_FAMILY, 9),
                               bg="#e0e0e0", fg=Theme.TEXT_PRIMARY, relief="flat",
                               padx=15, pady=3, cursor="hand2", command=self._check_all_status)
        refresh_btn.pack()

        # ========== Overall Status ==========
        self.overall_status_label = ttk.Label(self.main_frame, text="正在检测环境...",
                                              style="BigStatus.TLabel")
        self.overall_status_label.pack(pady=8)

        # ========== Task Section ==========
        task_outer = ttk.Frame(self.main_frame, style="TFrame")
        task_outer.pack(fill=tk.X, pady=(0, 10))

        task_frame = ttk.LabelFrame(task_outer, text="任务执行",
                                    style="Card.TLabelframe", padding=10)
        task_frame.pack(fill=tk.X)

        task_inner = ttk.Frame(task_frame, style="Card.TFrame")
        task_inner.pack(fill=tk.X)

        # Input row
        input_row = ttk.Frame(task_inner, style="Card.TFrame")
        input_row.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(input_row, text="任务描述:", style="Card.TLabel").pack(side=tk.LEFT, padx=(0, 10))

        self.task_entry = tk.Entry(input_row, font=(Theme.FONT_FAMILY, 11),
                                   bg=Theme.BG_INPUT, fg=Theme.TEXT_PRIMARY,
                                   insertbackground=Theme.TEXT_PRIMARY,
                                   relief="solid", bd=1)
        self.task_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6, padx=(0, 10))
        self.task_entry.insert(0, "打开b站搜索up主时醋坛子的第一条视频点赞")

        # Buttons - 使用 tk.Button 确保文字显示
        btn_row = ttk.Frame(task_inner, style="Card.TFrame")
        btn_row.pack(fill=tk.X)

        self.start_btn = tk.Button(btn_row, text="开始执行", font=(Theme.FONT_FAMILY, 10, "bold"),
                                   bg=Theme.SUCCESS, fg="white",
                                   activebackground="#1b5e20", activeforeground="white",
                                   relief="flat", padx=20, pady=8, cursor="hand2",
                                   command=self._start_task)
        self.start_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.stop_btn = tk.Button(btn_row, text="停止", font=(Theme.FONT_FAMILY, 10, "bold"),
                                  bg=Theme.ERROR, fg="white",
                                  activebackground="#b71c1c", activeforeground="white",
                                  relief="flat", padx=15, pady=8, cursor="hand2",
                                  state=tk.DISABLED, command=self._stop_task)
        self.stop_btn.pack(side=tk.LEFT)

        # ========== Log Section ==========
        log_outer = ttk.Frame(self.main_frame, style="TFrame")
        log_outer.pack(fill=tk.BOTH, expand=True)

        log_frame = ttk.LabelFrame(log_outer, text="运行日志",
                                   style="Card.TLabelframe", padding=8)
        log_frame.pack(fill=tk.BOTH, expand=True)

        log_container = ttk.Frame(log_frame, style="Card.TFrame")
        log_container.pack(fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(log_container)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.log_text = tk.Text(log_container, font=(Theme.FONT_FAMILY_MONO, 9),
                                bg=Theme.BG_LOG, fg=Theme.TEXT_PRIMARY,
                                insertbackground=Theme.TEXT_PRIMARY,
                                relief="solid", bd=1,
                                state=tk.DISABLED, wrap=tk.WORD,
                                yscrollcommand=scrollbar.set, padx=8, pady=8)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.log_text.yview)

        # Log tags
        self.log_text.tag_configure("info", foreground=Theme.INFO)
        self.log_text.tag_configure("success", foreground=Theme.SUCCESS)
        self.log_text.tag_configure("warning", foreground=Theme.WARNING)
        self.log_text.tag_configure("error", foreground=Theme.ERROR)
        self.log_text.tag_configure("stdout", foreground=Theme.TEXT_SECONDARY)
        self.log_text.tag_configure("stderr", foreground=Theme.WARNING)

        # Clear button
        log_ctrl = ttk.Frame(log_frame, style="Card.TFrame")
        log_ctrl.pack(fill=tk.X, pady=(8, 0))

        clear_btn = tk.Button(log_ctrl, text="清空日志", font=(Theme.FONT_FAMILY, 9),
                             bg="#e0e0e0", fg=Theme.TEXT_PRIMARY, relief="flat",
                             padx=10, pady=2, cursor="hand2", command=self._clear_log)
        clear_btn.pack(side=tk.LEFT)

        # ========== Footer ==========
        ttk.Label(self.main_frame, text="如需帮助请联系微信: le6688zmm 或扫描 qrcode.jpg",
                 style="Subtitle.TLabel").pack(pady=(8, 0))

    def _setup_log_redirect(self):
        """Setup stdout/stderr redirect."""
        self.stdout_redirector = TextRedirector(self.log_text, "stdout")
        self.stderr_redirector = TextRedirector(self.log_text, "stderr")

    def _log(self, message, tag="info"):
        """Add log message."""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n", tag)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _clear_log(self):
        """Clear log."""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _check_all_status(self):
        """Check all status in background."""
        # 重新加载环境变量
        reload_env_file()

        def check():
            try:
                self._check_adb_installed()
            except Exception as e:
                self._log(f"检查ADB安装状态失败: {e}", "error")

            try:
                self._check_adb_in_path()
            except Exception as e:
                self._log(f"检查ADB环境变量失败: {e}", "error")

            try:
                self._check_device_connected()
            except Exception as e:
                self._log(f"检查设备连接失败: {e}", "error")

            try:
                self._check_adb_keyboard()
            except Exception as e:
                self._log(f"检查ADB键盘失败: {e}", "error")

            try:
                self._check_api_config()
            except Exception as e:
                self._log(f"检查API配置失败: {e}", "error")

            try:
                self._update_overall_status()
            except Exception as e:
                self._log(f"更新整体状态失败: {e}", "error")

        threading.Thread(target=check, daemon=True).start()

    def _get_adb_path(self):
        """Get ADB path."""
        adb_path = shutil.which("adb")
        if adb_path:
            return adb_path

        local_adb = self.adb_install_dir / "adb.exe"
        if local_adb.exists():
            return str(local_adb)

        return None

    def _check_adb_installed(self):
        """Check ADB installation."""
        adb_path = self._get_adb_path()

        if adb_path:
            try:
                result = subprocess.run([adb_path, "version"], capture_output=True,
                                       text=True, timeout=10, creationflags=CREATE_NO_WINDOW)
                if result.returncode == 0:
                    version = result.stdout.strip().split("\n")[0]
                    self.adb_installed = True
                    self.root.after(0, lambda: self.adb_indicator.set_status(True, version[:28]))
                    self.root.after(0, lambda: self.adb_indicator.set_button("已安装", None, False))
                    return
            except Exception:
                pass

        if self.adb_package_path.exists():
            self.adb_installed = False
            self.root.after(0, lambda: self.adb_indicator.set_status(False, "未安装(可自动安装)"))
            self.root.after(0, lambda: self.adb_indicator.set_button("自动安装", self._install_adb, True))
        else:
            self.adb_installed = False
            self.root.after(0, lambda: self.adb_indicator.set_status(False, "未安装"))
            self.root.after(0, lambda: self.adb_indicator.set_button("无法安装", None, False))

    def _check_adb_in_path(self):
        """Check if ADB in PATH."""
        if shutil.which("adb"):
            self.adb_in_path = True
            self.root.after(0, lambda: self.path_indicator.set_status(True, "已配置"))
            self.root.after(0, lambda: self.path_indicator.set_button("已配置", None, False))
        else:
            local_adb = self.adb_install_dir / "adb.exe"
            if local_adb.exists():
                self.adb_in_path = False
                self.root.after(0, lambda: self.path_indicator.set_status(None, "未配置(可自动)"))
                self.root.after(0, lambda: self.path_indicator.set_button("配置PATH", self._configure_path, True))
            else:
                self.adb_in_path = False
                self.root.after(0, lambda: self.path_indicator.set_status(False, "未配置"))
                self.root.after(0, lambda: self.path_indicator.set_button("需先安装", None, False))

    def _check_device_connected(self):
        """Check device connection."""
        adb_path = self._get_adb_path()
        if not adb_path:
            self.device_connected = False
            self.root.after(0, lambda: self.device_indicator.set_status(False, "需先安装ADB"))
            self.root.after(0, lambda: self.device_indicator.set_button("连接", None, False))
            return

        try:
            result = subprocess.run([adb_path, "devices"], capture_output=True,
                                     text=True, timeout=10, creationflags=CREATE_NO_WINDOW)
            lines = result.stdout.strip().split("\n")
            devices = [l for l in lines[1:] if l.strip() and "\tdevice" in l]

            if devices:
                device_id = devices[0].split("\t")[0]
                self.device_connected = True
                display_id = device_id if len(device_id) <= 16 else device_id[:13] + "..."
                self.root.after(0, lambda: self.device_indicator.set_status(True, f"已连接:{display_id}"))
                self.root.after(0, lambda: self.device_indicator.set_button("已连接", None, False))
            else:
                self.device_connected = False
                self.root.after(0, lambda: self.device_indicator.set_status(False, "未检测到设备"))
                self.root.after(0, lambda: self.device_indicator.set_button("连接设备", self._connect_device, True))
        except Exception:
            self.device_connected = False
            self.root.after(0, lambda: self.device_indicator.set_status(False, "检测失败"))
            self.root.after(0, lambda: self.device_indicator.set_button("重试", self._check_all_status, True))

    def _check_adb_keyboard(self):
        """Check ADB Keyboard."""
        adb_path = self._get_adb_path()
        if not adb_path or not self.device_connected:
            self.adb_keyboard_installed = False
            self.root.after(0, lambda: self.keyboard_indicator.set_status(False, "需先连接设备"))
            self.root.after(0, lambda: self.keyboard_indicator.set_button("安装", None, False))
            return

        try:
            result = subprocess.run([adb_path, "shell", "ime", "list", "-s"],
                                   capture_output=True, text=True, timeout=10,
                                   creationflags=CREATE_NO_WINDOW)

            if "com.android.adbkeyboard/.AdbIME" in result.stdout:
                self.adb_keyboard_installed = True
                self.root.after(0, lambda: self.keyboard_indicator.set_status(True, "已安装"))
                self.root.after(0, lambda: self.keyboard_indicator.set_button("已安装", None, False))
            else:
                self.adb_keyboard_installed = False
                if self.adb_keyboard_path.exists():
                    self.root.after(0, lambda: self.keyboard_indicator.set_status(False, "未安装(可自动)"))
                    self.root.after(0, lambda: self.keyboard_indicator.set_button("安装键盘", self._install_adb_keyboard, True))
                else:
                    self.root.after(0, lambda: self.keyboard_indicator.set_status(False, "未安装"))
                    self.root.after(0, lambda: self.keyboard_indicator.set_button("无法安装", None, False))
        except Exception:
            self.adb_keyboard_installed = False
            self.root.after(0, lambda: self.keyboard_indicator.set_status(False, "检测失败"))

    def _check_api_config(self):
        """Check API config."""
        api_key = os.environ.get("MODELSCOPE_API_KEY", "").strip()

        # 调试日志
        self._log(f"检查API配置: key长度={len(api_key)}, 前6字符={api_key[:6] if len(api_key) >= 6 else api_key}", "info")

        if api_key and api_key != "EMPTY" and api_key != "your_modelscope_api_key_here":
            self.api_configured = True
            masked = api_key[:6] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
            # 使用默认参数捕获变量值，避免闭包问题
            self.root.after(0, lambda m=masked: self.api_indicator.set_status(True, f"已生效:{m}"))
            self.root.after(0, lambda: self.api_indicator.set_button("重新配置", self._configure_api, True))
            self._log(f"API配置有效: {masked}", "success")
        else:
            self.api_configured = False
            self.root.after(0, lambda: self.api_indicator.set_status(False, "未配置"))
            self.root.after(0, lambda: self.api_indicator.set_button("配置API", self._configure_api, True))
            self._log("API未配置或无效", "warning")

    def _update_overall_status(self):
        """Update overall status."""
        def update():
            if self.adb_installed and self.device_connected and self.adb_keyboard_installed and self.api_configured:
                self.overall_status_label.config(
                    text="环境已就绪！手机已连接！请输入任务开始执行", foreground=Theme.SUCCESS)
                self.start_btn.config(state=tk.NORMAL, bg=Theme.SUCCESS)
            else:
                missing = []
                if not self.adb_installed:
                    missing.append("ADB")
                if not self.device_connected:
                    missing.append("设备")
                if not self.adb_keyboard_installed:
                    missing.append("键盘")
                if not self.api_configured:
                    missing.append("API")

                self.overall_status_label.config(
                    text=f"请先完成配置: {' / '.join(missing)}", foreground=Theme.WARNING)
                self.start_btn.config(state=tk.DISABLED, bg="#9e9e9e")

        self.root.after(0, update)

    def _install_adb(self):
        """Install ADB."""
        def install():
            self._log("开始安装 ADB...", "info")

            if not self.adb_package_path.exists():
                self._log(f"错误: 找不到安装包: {self.adb_package_path}", "error")
                return

            try:
                self._log(f"正在解压 {self.adb_package_path.name}...", "info")
                with zipfile.ZipFile(self.adb_package_path, 'r') as zip_ref:
                    zip_ref.extractall(SCRIPT_DIR)

                if (self.adb_install_dir / "adb.exe").exists():
                    self._log("ADB 安装成功!", "success")
                    self._check_all_status()
                else:
                    self._log("安装失败: 未找到 adb.exe", "error")
            except Exception as e:
                self._log(f"安装失败: {e}", "error")

        threading.Thread(target=install, daemon=True).start()

    def _configure_path(self):
        """Configure PATH."""
        def configure():
            self._log("正在配置环境变量...", "info")
            adb_dir = str(self.adb_install_dir)

            if not self.adb_install_dir.exists():
                self._log("错误: ADB 目录不存在", "error")
                return

            try:
                result = subprocess.run(
                    ["powershell", "-Command", "[Environment]::GetEnvironmentVariable('PATH', 'User')"],
                    capture_output=True, text=True, timeout=30, creationflags=CREATE_NO_WINDOW)
                current_path = result.stdout.strip()

                if adb_dir in current_path:
                    self._log("ADB 已在 PATH 中", "success")
                    self._check_all_status()
                    return

                new_path = f"{current_path};{adb_dir}" if current_path else adb_dir

                subprocess.run(
                    ["powershell", "-Command",
                     f"[Environment]::SetEnvironmentVariable('PATH', '{new_path}', 'User')"],
                    capture_output=True, text=True, timeout=30, creationflags=CREATE_NO_WINDOW)

                os.environ["PATH"] = os.environ.get("PATH", "") + ";" + adb_dir
                self._log("环境变量配置成功!", "success")
                self._log("提示: 新终端窗口才会生效", "info")
                self._check_all_status()
            except Exception as e:
                self._log(f"配置失败: {e}", "error")

        threading.Thread(target=configure, daemon=True).start()

    def _connect_device(self):
        """Show connect dialog."""
        dialog = tk.Toplevel(self.root)
        dialog.title("连接设备")
        dialog.geometry("640x460")
        dialog.configure(bg=Theme.BG_MAIN)
        dialog.transient(self.root)
        dialog.grab_set()

        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 380) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 260) // 2
        dialog.geometry(f"+{x}+{y}")

        tk.Label(dialog, text="选择连接方式", font=(Theme.FONT_FAMILY, 12, "bold"),
                bg=Theme.BG_MAIN, fg=Theme.TEXT_PRIMARY).pack(pady=12)

        # USB
        usb_frame = tk.Frame(dialog, bg=Theme.BG_CARD, padx=12, pady=10)
        usb_frame.pack(fill=tk.X, padx=15, pady=5)

        tk.Label(usb_frame, text="USB 连接", font=(Theme.FONT_FAMILY, 10, "bold"),
                bg=Theme.BG_CARD, fg=Theme.ACCENT).pack(anchor="w")
        tk.Label(usb_frame, text="1. 手机开启USB调试  2. 数据线连接  3. 允许调试",
                font=(Theme.FONT_FAMILY, 9), bg=Theme.BG_CARD,
                fg=Theme.TEXT_SECONDARY).pack(anchor="w")

        def refresh_usb():
            dialog.destroy()
            self._log("正在检测 USB 设备...", "info")
            self._check_all_status()

        tk.Button(usb_frame, text="检测USB设备", font=(Theme.FONT_FAMILY, 9),
                 bg=Theme.ACCENT, fg="white", relief="flat", padx=12, pady=4,
                 cursor="hand2", command=refresh_usb).pack(pady=5)

        # WiFi
        wifi_frame = tk.Frame(dialog, bg=Theme.BG_CARD, padx=12, pady=10)
        wifi_frame.pack(fill=tk.X, padx=15, pady=5)

        tk.Label(wifi_frame, text="WiFi 连接", font=(Theme.FONT_FAMILY, 10, "bold"),
                bg=Theme.BG_CARD, fg=Theme.ACCENT).pack(anchor="w")

        ip_frame = tk.Frame(wifi_frame, bg=Theme.BG_CARD)
        ip_frame.pack(fill=tk.X, pady=5)

        tk.Label(ip_frame, text="IP:端口", font=(Theme.FONT_FAMILY, 9),
                bg=Theme.BG_CARD, fg=Theme.TEXT_SECONDARY).pack(side=tk.LEFT)

        ip_entry = tk.Entry(ip_frame, font=(Theme.FONT_FAMILY, 10),
                           bg=Theme.BG_INPUT, fg=Theme.TEXT_PRIMARY, relief="solid", bd=1, width=18)
        ip_entry.pack(side=tk.LEFT, padx=8, ipady=3)
        ip_entry.insert(0, "192.168.1.100:5555")

        def connect_wifi():
            address = ip_entry.get().strip()
            if address:
                dialog.destroy()
                self._connect_wifi_device(address)

        tk.Button(ip_frame, text="连接", font=(Theme.FONT_FAMILY, 9),
                 bg=Theme.ACCENT, fg="white", relief="flat", padx=10, pady=3,
                 cursor="hand2", command=connect_wifi).pack(side=tk.LEFT)

    def _connect_wifi_device(self, address):
        """Connect WiFi device."""
        def connect():
            self._log(f"正在连接 {address}...", "info")
            adb_path = self._get_adb_path()
            if not adb_path:
                self._log("错误: ADB 未安装", "error")
                return

            try:
                result = subprocess.run([adb_path, "connect", address],
                                       capture_output=True, text=True, timeout=30,
                                       creationflags=CREATE_NO_WINDOW)
                output = result.stdout + result.stderr
                if "connected" in output.lower():
                    self._log(f"连接成功: {address}", "success")
                else:
                    self._log(f"连接失败: {output}", "error")
                self._check_all_status()
            except Exception as e:
                self._log(f"连接失败: {e}", "error")

        threading.Thread(target=connect, daemon=True).start()

    def _install_adb_keyboard(self):
        """Install ADB Keyboard."""
        def install():
            self._log("正在安装 ADB Keyboard...", "info")

            if not self.adb_keyboard_path.exists():
                self._log("错误: 找不到 APK", "error")
                return

            adb_path = self._get_adb_path()
            if not adb_path:
                self._log("错误: ADB 未安装", "error")
                return

            try:
                self._log("正在安装 APK (可能需要手机确认)...", "info")
                result = subprocess.run([adb_path, "install", "-r", str(self.adb_keyboard_path)],
                                       capture_output=True, text=True, timeout=120,
                                       creationflags=CREATE_NO_WINDOW)

                if "Success" in result.stdout + result.stderr:
                    self._log("APK 安装成功!", "success")

                    subprocess.run([adb_path, "shell", "ime", "enable", "com.android.adbkeyboard/.AdbIME"],
                                  capture_output=True, text=True, timeout=30,
                                  creationflags=CREATE_NO_WINDOW)
                    subprocess.run([adb_path, "shell", "ime", "set", "com.android.adbkeyboard/.AdbIME"],
                                  capture_output=True, text=True, timeout=30,
                                  creationflags=CREATE_NO_WINDOW)

                    self._log("ADB Keyboard 配置完成!", "success")
                    self._check_all_status()
                else:
                    self._log(f"安装失败: {result.stdout + result.stderr}", "error")
            except Exception as e:
                self._log(f"安装失败: {e}", "error")

        threading.Thread(target=install, daemon=True).start()

    def _configure_api(self):
        """Show API config dialog."""
        dialog = tk.Toplevel(self.root)
        dialog.title("配置 API")
        dialog.geometry("480x450")
        dialog.configure(bg=Theme.BG_MAIN)
        dialog.transient(self.root)
        dialog.grab_set()

        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 480) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 450) // 2
        dialog.geometry(f"+{x}+{y}")

        tk.Label(dialog, text="配置 ModelScope API", font=(Theme.FONT_FAMILY, 12, "bold"),
                bg=Theme.BG_MAIN, fg=Theme.TEXT_PRIMARY).pack(pady=12)

        # Instructions
        info_frame = tk.Frame(dialog, bg=Theme.BG_CARD, padx=12, pady=10)
        info_frame.pack(fill=tk.X, padx=15, pady=5)

        tk.Label(info_frame, text="获取 API Key 步骤", font=(Theme.FONT_FAMILY, 10, "bold"),
                bg=Theme.BG_CARD, fg=Theme.ACCENT).pack(anchor="w")
        tk.Label(info_frame, text="1. 点击按钮打开 ModelScope\n2. 登录/注册账号\n3. 复制访问令牌\n4. 粘贴到下方",
                font=(Theme.FONT_FAMILY, 9), bg=Theme.BG_CARD,
                fg=Theme.TEXT_SECONDARY, justify="left").pack(anchor="w", pady=5)

        def open_web():
            # 使用 os.startfile 避免弹出控制台窗口
            url = "https://modelscope.cn/my/myaccesstoken"
            if sys.platform == "win32":
                os.startfile(url)
            else:
                import webbrowser
                webbrowser.open(url)

        tk.Button(info_frame, text="打开 ModelScope", font=(Theme.FONT_FAMILY, 9),
                 bg=Theme.ACCENT, fg="white", relief="flat", padx=12, pady=4,
                 cursor="hand2", command=open_web).pack(pady=5)

        # API Key
        key_frame = tk.Frame(dialog, bg=Theme.BG_CARD, padx=12, pady=10)
        key_frame.pack(fill=tk.X, padx=15, pady=8)

        tk.Label(key_frame, text="API Key", font=(Theme.FONT_FAMILY, 10, "bold"),
                bg=Theme.BG_CARD, fg=Theme.ACCENT).pack(anchor="w")

        api_var = tk.StringVar(value=os.environ.get("MODELSCOPE_API_KEY", ""))
        api_entry = tk.Entry(key_frame, textvariable=api_var, font=(Theme.FONT_FAMILY_MONO, 10),
                            bg=Theme.BG_INPUT, fg=Theme.TEXT_PRIMARY, relief="solid", bd=1, show="*")
        api_entry.pack(fill=tk.X, ipady=5, pady=5)

        show_var = tk.BooleanVar(value=False)

        def toggle():
            api_entry.config(show="" if show_var.get() else "*")

        tk.Checkbutton(key_frame, text="显示", variable=show_var, command=toggle,
                      bg=Theme.BG_CARD, fg=Theme.TEXT_SECONDARY,
                      activebackground=Theme.BG_CARD).pack(anchor="w")

        def save():
            api_key = api_var.get().strip()
            if not api_key:
                messagebox.showerror("错误", "请输入 API Key")
                return

            env_file = SCRIPT_DIR / ".env"
            self._log(f"保存API配置到: {env_file}", "info")

            try:
                lines = []
                if env_file.exists():
                    with open(env_file, "r", encoding="utf-8") as f:
                        lines = f.read().split("\n")

                # Update API key
                found = False
                for i, line in enumerate(lines):
                    if line.startswith("MODELSCOPE_API_KEY="):
                        lines[i] = f"MODELSCOPE_API_KEY={api_key}"
                        found = True
                        break
                if not found:
                    lines.append(f"MODELSCOPE_API_KEY={api_key}")

                # Add defaults
                if not any(l.startswith("PHONE_AGENT_BASE_URL=") for l in lines):
                    lines.append("PHONE_AGENT_BASE_URL=https://api-inference.modelscope.cn/v1")
                if not any(l.startswith("PHONE_AGENT_MODEL=") for l in lines):
                    lines.append("PHONE_AGENT_MODEL=ZhipuAI/AutoGLM-Phone-9B")

                with open(env_file, "w", encoding="utf-8") as f:
                    f.write("\n".join(lines))

                self._log(f"文件写入成功，内容行数: {len(lines)}", "success")

                # 立即更新环境变量
                os.environ["MODELSCOPE_API_KEY"] = api_key
                self._log(f"环境变量已设置: MODELSCOPE_API_KEY={api_key[:6]}...", "info")

                messagebox.showinfo("成功", f"API 配置已保存到:\n{env_file}\n\n配置将立即生效!")
                dialog.destroy()

                # 刷新状态
                self._log("开始刷新状态...", "info")
                self._check_all_status()

            except Exception as e:
                self._log(f"保存失败: {e}", "error")
                messagebox.showerror("错误", f"保存失败: {e}")

        tk.Button(dialog, text="保存配置", font=(Theme.FONT_FAMILY, 10, "bold"),
                 bg=Theme.SUCCESS, fg="white", relief="flat", padx=20, pady=8,
                 cursor="hand2", command=save).pack(pady=12)

    def _start_task(self):
        """Start task execution."""
        task = self.task_entry.get().strip()
        if not task:
            messagebox.showerror("错误", "请输入任务描述")
            return

        def run():
            self.running = True
            self.root.after(0, lambda: self.start_btn.config(state=tk.DISABLED, bg="#9e9e9e"))
            self.root.after(0, lambda: self.stop_btn.config(state=tk.NORMAL, bg=Theme.ERROR))

            self._log("=" * 50, "info")
            self._log(f"开始执行任务: {task}", "info")
            self._log("=" * 50, "info")

            old_stdout, old_stderr = sys.stdout, sys.stderr
            sys.stdout = self.stdout_redirector
            sys.stderr = self.stderr_redirector

            try:
                from phone_agent import PhoneAgent
                from phone_agent.agent import AgentConfig
                from phone_agent.model import ModelConfig

                model_config = ModelConfig(
                    base_url=os.environ.get("PHONE_AGENT_BASE_URL", "https://api-inference.modelscope.cn/v1"),
                    model_name=os.environ.get("PHONE_AGENT_MODEL", "ZhipuAI/AutoGLM-Phone-9B"),
                    api_key=os.environ.get("MODELSCOPE_API_KEY", "EMPTY"),
                )

                agent_config = AgentConfig(
                    max_steps=int(os.environ.get("PHONE_AGENT_MAX_STEPS", "100")),
                    device_id=os.environ.get("PHONE_AGENT_DEVICE_ID"),
                    verbose=True,
                    lang=os.environ.get("PHONE_AGENT_LANG", "cn"),
                )

                self.agent = PhoneAgent(model_config=model_config, agent_config=agent_config)

                self._log(f"模型: {model_config.model_name}", "info")
                self._log(f"API: {model_config.base_url}", "info")

                result = self.agent.run(task)

                self._log("=" * 50, "success")
                self._log("任务完成!", "success")
                self._log(f"结果: {result}", "success")
                self._log("=" * 50, "success")

            except Exception as e:
                self._log(f"错误: {e}", "error")
                import traceback
                self._log(traceback.format_exc(), "error")
            finally:
                sys.stdout, sys.stderr = old_stdout, old_stderr
                self.running = False
                self.agent = None
                self.root.after(0, lambda: self.start_btn.config(state=tk.NORMAL, bg=Theme.SUCCESS))
                self.root.after(0, lambda: self.stop_btn.config(state=tk.DISABLED, bg="#9e9e9e"))

        threading.Thread(target=run, daemon=True).start()

    def _stop_task(self):
        """Stop task."""
        self.running = False
        self._log("用户请求停止...", "warning")
        if self.agent:
            self.agent = None
        self.start_btn.config(state=tk.NORMAL, bg=Theme.SUCCESS)
        self.stop_btn.config(state=tk.DISABLED, bg="#9e9e9e")

    def _show_disclaimer(self, force_agree=True):
        """显示免责声明弹窗。

        Args:
            force_agree: 如果为True，用户必须同意才能关闭；否则可以直接关闭
        """
        dialog = tk.Toplevel(self.root)
        dialog.title("免责声明")
        dialog.geometry("600x620")
        dialog.configure(bg=Theme.BG_MAIN)
        dialog.transient(self.root)
        dialog.grab_set()

        # 如果需要强制同意，禁止关闭窗口
        if force_agree:
            dialog.protocol("WM_DELETE_WINDOW", lambda: None)

        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 600) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 620) // 2
        dialog.geometry(f"+{x}+{y}")

        # 标题
        tk.Label(dialog, text="免责声明", font=(Theme.FONT_FAMILY, 14, "bold"),
                bg=Theme.BG_MAIN, fg=Theme.ERROR).pack(pady=(15, 10))

        # 内容区域
        content_frame = tk.Frame(dialog, bg=Theme.BG_CARD, padx=15, pady=15)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)

        # 使用Text组件显示免责声明内容
        disclaimer_text = tk.Text(content_frame, font=(Theme.FONT_FAMILY, 10),
                                  bg=Theme.BG_CARD, fg=Theme.TEXT_PRIMARY,
                                  wrap=tk.WORD, relief="flat", height=18)
        disclaimer_text.pack(fill=tk.BOTH, expand=True)

        disclaimer_content = """1. 非责任声明

仅限于合法学习目的：本项目提供的所有代码、文档及相关资源仅可用于个人学习、研究或教育目的。任何个人或组织不得将其用于任何非法用途，包括但不限于破坏网络安全、侵犯他人隐私、进行未授权访问等违法行为。

作者不承担任何责任：使用者因使用、滥用或误用本项目内容而产生的任何直接或间接后果（包括但不限于法律风险、经济损失、安全漏洞等）均由使用者自行承担。作者或贡献者不承担任何法律责任。

禁止非法使用：严禁将本项目用于违反所在国家/地区法律法规的活动。若使用者违反本条款，其行为与作者及贡献者无关，使用者须独立承担全部责任。

2. 无担保声明

本项目按"原样"提供，作者及贡献者不提供任何明示或暗示的担保，包括但不限于适用性、安全性、稳定性等。使用者须自行评估项目风险。"""

        disclaimer_text.insert("1.0", disclaimer_content)
        disclaimer_text.config(state=tk.DISABLED)

        # 底部按钮区域
        bottom_frame = tk.Frame(dialog, bg=Theme.BG_MAIN)
        bottom_frame.pack(fill=tk.X, padx=15, pady=15)

        if force_agree:
            # 已阅读复选框
            read_var = tk.BooleanVar(value=False)
            read_check = tk.Checkbutton(bottom_frame, text="我已阅读并理解以上免责声明",
                                        variable=read_var, bg=Theme.BG_MAIN,
                                        fg=Theme.TEXT_PRIMARY, activebackground=Theme.BG_MAIN,
                                        font=(Theme.FONT_FAMILY, 11))
            read_check.pack(pady=(0, 15))

            # 按钮行
            btn_row = tk.Frame(bottom_frame, bg=Theme.BG_MAIN)
            btn_row.pack()

            # 拒绝按钮
            refuse_btn = tk.Button(btn_row, text="拒绝并退出", font=(Theme.FONT_FAMILY, 11),
                                   bg=Theme.ERROR, fg="white", relief="flat", padx=35, pady=10,
                                   cursor="hand2", command=lambda: self.root.destroy())
            refuse_btn.pack(side=tk.LEFT, padx=(0, 20))

            # 同意按钮（初始禁用）
            agree_btn = tk.Button(btn_row, text="同意并继续", font=(Theme.FONT_FAMILY, 12, "bold"),
                                  bg="#9e9e9e", fg="white", relief="flat", padx=50, pady=12,
                                  state=tk.DISABLED)
            agree_btn.pack(side=tk.LEFT)

            def on_check():
                if read_var.get():
                    agree_btn.config(state=tk.NORMAL, bg=Theme.SUCCESS, cursor="hand2")
                else:
                    agree_btn.config(state=tk.DISABLED, bg="#9e9e9e", cursor="")

            def on_agree():
                if read_var.get():
                    dialog.destroy()

            read_check.config(command=on_check)
            agree_btn.config(command=on_agree)
        else:
            # 非强制模式，直接显示关闭按钮
            close_btn = tk.Button(bottom_frame, text="关闭", font=(Theme.FONT_FAMILY, 12, "bold"),
                                  bg=Theme.ACCENT, fg="white", relief="flat", padx=50, pady=12,
                                  cursor="hand2", command=dialog.destroy)
            close_btn.pack()

    def run(self):
        """Run app."""
        self.root.mainloop()


def main():
    """Main entry."""
    app = PhoneAgentGUI()
    app.run()


if __name__ == "__main__":
    main()