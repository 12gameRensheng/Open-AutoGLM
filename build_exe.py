#!/usr/bin/env python3
"""
Build script to package main.py into a single executable file.
Usage: python build_exe.py
"""

import subprocess
import sys
import os


def check_pyinstaller():
    """Check if PyInstaller is installed."""
    try:
        import PyInstaller
        print(f"PyInstaller version: {PyInstaller.__version__}")
        return True
    except ImportError:
        print("PyInstaller not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        return True


def build_exe():
    """Build the executable."""
    # Get the script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    main_py = os.path.join(script_dir, "main.py")

    if not os.path.exists(main_py):
        print(f"Error: {main_py} not found!")
        sys.exit(1)

    print("Building executable...")
    print("-" * 50)

    # PyInstaller command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",           # Single file output
        "--clean",             # Clean cache before building
        "--noconfirm",         # Replace output without asking
        "--name", "PhoneAgent",  # Output name
        "--add-data", f"phone_agent{os.pathsep}phone_agent",  # Include phone_agent package
        "--hidden-import", "phone_agent",
        "--hidden-import", "phone_agent.adb",
        "--hidden-import", "phone_agent.adb.connection",
        "--hidden-import", "phone_agent.adb.device",
        "--hidden-import", "phone_agent.adb.input",
        "--hidden-import", "phone_agent.adb.screenshot",
        "--hidden-import", "phone_agent.model",
        "--hidden-import", "phone_agent.model.client",
        "--hidden-import", "phone_agent.actions",
        "--hidden-import", "phone_agent.actions.handler",
        "--hidden-import", "phone_agent.config",
        "--hidden-import", "phone_agent.config.apps",
        "--hidden-import", "phone_agent.config.i18n",
        "--hidden-import", "phone_agent.config.prompts",
        "--hidden-import", "phone_agent.config.prompts_en",
        "--hidden-import", "phone_agent.config.prompts_zh",
        "--hidden-import", "phone_agent.agent",
        "--hidden-import", "PIL",
        "--hidden-import", "PIL.Image",
        "--hidden-import", "openai",
        "--collect-all", "phone_agent",
        "--collect-all", "openai",
        main_py
    ]

    print(f"Running: {' '.join(cmd)}")
    print("-" * 50)

    # Change to script directory
    os.chdir(script_dir)

    # Run PyInstaller
    result = subprocess.run(cmd)

    if result.returncode == 0:
        exe_path = os.path.join(script_dir, "dist", "PhoneAgent.exe")
        print("-" * 50)
        print("Build successful!")
        print(f"Executable: {exe_path}")
        print("\nUsage: Simply double-click PhoneAgent.exe to run")
    else:
        print("-" * 50)
        print("Build failed!")
        sys.exit(1)


if __name__ == "__main__":
    print("=" * 50)
    print("PhoneAgent - Build Script")
    print("=" * 50)

    check_pyinstaller()
    build_exe()
