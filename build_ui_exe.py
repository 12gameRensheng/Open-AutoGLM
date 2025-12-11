#!/usr/bin/env python3
"""
Build script for Phone Agent GUI.

Creates a standalone exe file that users can run directly.
No external dependencies required at runtime.

Usage:
    python build_ui_exe.py

Output:
    dist/PhoneAgent.exe
"""

import subprocess
import sys
import shutil
from pathlib import Path

# Paths
ROOT_DIR = Path(__file__).parent.resolve()
DIST_DIR = ROOT_DIR / "dist"
UI_MAIN = DIST_DIR / "ui_main.py"
OUTPUT_NAME = "PhoneAgent"


def check_pyinstaller():
    """Check if PyInstaller is installed."""
    try:
        import PyInstaller
        print(f"PyInstaller version: {PyInstaller.__version__}")
        return True
    except ImportError:
        print("PyInstaller not found. Installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
        return True


def build_exe():
    """Build the exe file."""
    print("=" * 50)
    print("Building Phone Agent GUI...")
    print("=" * 50)

    # Check PyInstaller
    check_pyinstaller()

    # Clean previous build
    build_dir = ROOT_DIR / "build"
    spec_file = ROOT_DIR / f"{OUTPUT_NAME}.spec"
    if build_dir.exists():
        shutil.rmtree(build_dir)
    if spec_file.exists():
        spec_file.unlink()

    # PyInstaller command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",                    # Single exe file
        "--windowed",                   # No console window
        "--name", OUTPUT_NAME,          # Output name
        "--distpath", str(DIST_DIR),    # Output to dist folder
        "--workpath", str(build_dir),   # Build temp files
        "--specpath", str(ROOT_DIR),    # Spec file location
        # Add phone_agent package
        "--add-data", f"{ROOT_DIR / 'phone_agent'};phone_agent",
        # Hidden imports for phone_agent dependencies
        "--hidden-import", "phone_agent",
        "--hidden-import", "phone_agent.agent",
        "--hidden-import", "phone_agent.model",
        "--hidden-import", "phone_agent.model.client",
        "--hidden-import", "phone_agent.adb",
        "--hidden-import", "phone_agent.adb.device",
        "--hidden-import", "phone_agent.adb.screenshot",
        "--hidden-import", "phone_agent.adb.input",
        "--hidden-import", "phone_agent.adb.connection",
        "--hidden-import", "phone_agent.actions",
        "--hidden-import", "phone_agent.actions.handler",
        "--hidden-import", "phone_agent.config",
        "--hidden-import", "phone_agent.config.apps",
        "--hidden-import", "phone_agent.config.prompts",
        "--hidden-import", "phone_agent.config.prompts_zh",
        "--hidden-import", "phone_agent.config.prompts_en",
        "--hidden-import", "phone_agent.config.i18n",
        "--hidden-import", "openai",
        "--hidden-import", "httpx",
        "--hidden-import", "PIL",
        "--hidden-import", "PIL.Image",
        # Exclude unnecessary modules to reduce size
        "--exclude-module", "matplotlib",
        "--exclude-module", "numpy",
        "--exclude-module", "scipy",
        "--exclude-module", "pandas",
        "--exclude-module", "pytest",
        # Exclude pyd files from UPX compression (fixes PIL avif extraction error)
        "--upx-exclude", "PIL*",
        "--upx-exclude", "_avif*",
        "--upx-exclude", "*.pyd",
        # Main script
        str(UI_MAIN),
    ]

    print("\nRunning PyInstaller...")
    print(" ".join(cmd))
    print()

    result = subprocess.run(cmd)

    if result.returncode == 0:
        exe_path = DIST_DIR / f"{OUTPUT_NAME}.exe"
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print()
            print("=" * 50)
            print(f"Build successful!")
            print(f"Output: {exe_path}")
            print(f"Size: {size_mb:.1f} MB")
            print("=" * 50)
            print()
            print("Usage:")
            print(f"  1. Copy the following files to a folder:")
            print(f"     - {OUTPUT_NAME}.exe")
            print(f"     - .env (or .env.example)")
            print(f"     - 软件包/ folder (with ADBKeyboard.apk)")
            print(f"  2. Double-click {OUTPUT_NAME}.exe to run")
            return True
        else:
            print(f"Error: {exe_path} not found")
            return False
    else:
        print(f"Build failed with code {result.returncode}")
        return False


def clean():
    """Clean build artifacts."""
    print("Cleaning build artifacts...")

    build_dir = ROOT_DIR / "build"
    spec_file = ROOT_DIR / f"{OUTPUT_NAME}.spec"

    if build_dir.exists():
        shutil.rmtree(build_dir)
        print(f"  Removed {build_dir}")

    if spec_file.exists():
        spec_file.unlink()
        print(f"  Removed {spec_file}")

    print("Clean complete.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Build Phone Agent GUI exe")
    parser.add_argument("--clean", action="store_true", help="Clean build artifacts")
    args = parser.parse_args()

    if args.clean:
        clean()
    else:
        build_exe()
