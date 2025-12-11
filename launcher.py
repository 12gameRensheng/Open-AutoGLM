#!/usr/bin/env python3
"""
Phone Agent 启动器 - 简易 GUI 界面
"""

import os
import sys
import subprocess
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox


class PhoneAgentLauncher:
    """Phone Agent 简易启动器"""

    # 默认值
    DEFAULT_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
    DEFAULT_MODEL = "autoglm-phone"
    ZHIPU_URL = "https://open.bigmodel.cn/usercenter/apikeys"

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Phone Agent 启动器")
        self.root.geometry("520x350")
        self.root.resizable(False, False)

        # 居中窗口
        self.center_window()

        # 创建界面
        self.create_ui()

    def center_window(self):
        """窗口居中显示"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"+{x}+{y}")

    def create_ui(self):
        """创建用户界面"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 标题
        title_label = ttk.Label(
            main_frame,
            text="Phone Agent 启动器",
            font=("Microsoft YaHei UI", 16, "bold")
        )
        title_label.pack(pady=(0, 20))

        # 配置框架
        config_frame = ttk.LabelFrame(main_frame, text="配置信息", padding="10")
        config_frame.pack(fill=tk.X, pady=(0, 15))

        # Base URL (只读)
        url_frame = ttk.Frame(config_frame)
        url_frame.pack(fill=tk.X, pady=5)
        ttk.Label(url_frame, text="接口地址:", width=12).pack(side=tk.LEFT)
        self.url_var = tk.StringVar(value=self.DEFAULT_BASE_URL)
        url_entry = ttk.Entry(url_frame, textvariable=self.url_var, state="readonly", width=45)
        url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Model (只读)
        model_frame = ttk.Frame(config_frame)
        model_frame.pack(fill=tk.X, pady=5)
        ttk.Label(model_frame, text="模型名称:", width=12).pack(side=tk.LEFT)
        self.model_var = tk.StringVar(value=self.DEFAULT_MODEL)
        model_entry = ttk.Entry(model_frame, textvariable=self.model_var, state="readonly", width=45)
        model_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # API Key (用户输入)
        apikey_frame = ttk.Frame(config_frame)
        apikey_frame.pack(fill=tk.X, pady=5)
        ttk.Label(apikey_frame, text="API 密钥:", width=12).pack(side=tk.LEFT)
        self.apikey_var = tk.StringVar()
        self.apikey_entry = ttk.Entry(apikey_frame, textvariable=self.apikey_var, width=45, show="*")
        self.apikey_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 显示/隐藏密钥
        self.show_key_var = tk.BooleanVar(value=False)
        show_key_cb = ttk.Checkbutton(
            config_frame,
            text="显示 API 密钥",
            variable=self.show_key_var,
            command=self.toggle_apikey_visibility
        )
        show_key_cb.pack(anchor=tk.W, pady=(5, 0))

        # 按钮框架
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)

        # 获取 API Key 按钮
        get_key_btn = ttk.Button(
            btn_frame,
            text="获取 API 密钥 (智谱官网)",
            command=self.open_zhipu_website
        )
        get_key_btn.pack(side=tk.LEFT, padx=(0, 10))

        # 启动按钮
        self.launch_btn = ttk.Button(
            btn_frame,
            text="启动 Phone Agent",
            command=self.launch_agent,
            style="Accent.TButton"
        )
        self.launch_btn.pack(side=tk.RIGHT)

        # 状态标签
        self.status_var = tk.StringVar(value="请输入 API 密钥后点击启动")
        status_label = ttk.Label(
            main_frame,
            textvariable=self.status_var,
            foreground="gray"
        )
        status_label.pack(pady=(10, 0))

        # 提示信息
        tip_label = ttk.Label(
            main_frame,
            text="提示: 请确保手机已连接并开启 USB 调试",
            foreground="blue"
        )
        tip_label.pack(pady=(5, 0))

        # 聚焦到密钥输入框
        self.apikey_entry.focus()

    def toggle_apikey_visibility(self):
        """切换密钥显示/隐藏"""
        if self.show_key_var.get():
            self.apikey_entry.config(show="")
        else:
            self.apikey_entry.config(show="*")

    def open_zhipu_website(self):
        """打开智谱官网获取 API Key"""
        webbrowser.open(self.ZHIPU_URL)
        self.status_var.set("已在浏览器中打开智谱官网...")

    def get_exe_path(self):
        """获取 PhoneAgent.exe 的路径"""
        # 检查是否作为打包后的 exe 运行
        if getattr(sys, 'frozen', False):
            exe_dir = os.path.dirname(sys.executable)
        else:
            exe_dir = os.path.dirname(os.path.abspath(__file__))

        # 在同目录或 dist 目录查找
        possible_paths = [
            os.path.join(exe_dir, "PhoneAgent.exe"),
            os.path.join(exe_dir, "dist", "PhoneAgent.exe"),
            os.path.join(os.path.dirname(exe_dir), "dist", "PhoneAgent.exe"),
        ]

        for path in possible_paths:
            if os.path.exists(path):
                return path

        return None

    def launch_agent(self):
        """启动 Phone Agent"""
        apikey = self.apikey_var.get().strip()

        if not apikey:
            messagebox.showwarning("警告", "请输入 API 密钥！")
            self.apikey_entry.focus()
            return

        # 查找 PhoneAgent.exe
        exe_path = self.get_exe_path()

        if exe_path is None:
            messagebox.showerror(
                "错误",
                "找不到 PhoneAgent.exe！\n\n"
                "请确保 PhoneAgent.exe 与启动器在同一目录下。"
            )
            return

        # 构建命令
        cmd = [
            exe_path,
            "--base-url", self.DEFAULT_BASE_URL,
            "--model", self.DEFAULT_MODEL,
            "--apikey", apikey
        ]

        self.status_var.set("正在启动 Phone Agent...")
        self.launch_btn.config(state="disabled")
        self.root.update()

        try:
            # 在新控制台窗口中启动
            if sys.platform == "win32":
                subprocess.Popen(
                    cmd,
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
            else:
                subprocess.Popen(cmd)

            self.status_var.set("Phone Agent 已成功启动！")

            # 1.5秒后关闭启动器
            self.root.after(1500, self.root.destroy)

        except Exception as e:
            messagebox.showerror("错误", f"启动失败：\n{e}")
            self.status_var.set("启动失败！")
            self.launch_btn.config(state="normal")

    def run(self):
        """运行应用"""
        self.root.mainloop()


def main():
    """主入口"""
    app = PhoneAgentLauncher()
    app.run()


if __name__ == "__main__":
    main()
