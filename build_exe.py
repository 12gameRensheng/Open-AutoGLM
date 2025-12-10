#!/usr/bin/env python3
"""
Phone Agent EXE Build Script.

This script builds the Phone Agent CLI into a standalone executable.
Works with conda environments on Windows.

Usage:
    python build_exe.py [--onefile] [--clean] [--upx]
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], description: str) -> bool:
    """Run a command and return success status."""
    print(f"\n{'='*50}")
    print(f"{description}...")
    print(f"{'='*50}")
    print(f"Running: {' '.join(cmd)}\n")

    result = subprocess.run(cmd, shell=False)
    if result.returncode != 0:
        print(f"\nERROR: {description} failed with code {result.returncode}")
        return False
    return True


def check_pyinstaller() -> bool:
    """Check if PyInstaller is installed, install if not."""
    try:
        import PyInstaller

        print(f"PyInstaller version: {PyInstaller.__version__}")
        return True
    except ImportError:
        print("PyInstaller not found. Installing...")
        return run_command(
            [sys.executable, "-m", "pip", "install", "--upgrade", "pyinstaller"],
            "Installing PyInstaller",
        )


def install_dependencies() -> bool:
    """Install project dependencies."""
    # Try editable install first
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-e", "."],
        capture_output=True,
    )

    if result.returncode != 0:
        # Fall back to requirements.txt
        req_file = Path(__file__).parent / "requirements.txt"
        if req_file.exists():
            return run_command(
                [sys.executable, "-m", "pip", "install", "-r", str(req_file)],
                "Installing dependencies from requirements.txt",
            )
    return True


def clean_build() -> None:
    """Clean previous build artifacts."""
    print("\nCleaning previous build...")
    project_root = Path(__file__).parent

    for folder in ["build", "dist"]:
        path = project_root / folder
        if path.exists():
            print(f"  Removing {path}")
            shutil.rmtree(path)

    # Clean __pycache__ directories
    for pycache in project_root.rglob("__pycache__"):
        if pycache.is_dir():
            shutil.rmtree(pycache)


def build_exe(use_spec: bool = True, onefile: bool = True, use_upx: bool = True) -> bool:
    """Build the executable."""
    project_root = Path(__file__).parent
    spec_file = project_root / "phone_agent.spec"

    if use_spec and spec_file.exists():
        # Use spec file
        cmd = [
            sys.executable,
            "-m",
            "PyInstaller",
            str(spec_file),
            "--clean",
        ]
    else:
        # Build without spec file
        cmd = [
            sys.executable,
            "-m",
            "PyInstaller",
            "--name=phone_agent",
            "--console",
            "--clean",
        ]

        if onefile:
            cmd.append("--onefile")

        if use_upx:
            cmd.append("--upx-dir=.")

        # Add hidden imports
        hidden_imports = [
            "PIL",
            "PIL.Image",
            "openai",
            "httpx",
            "httpcore",
            "certifi",
            "pydantic",
            "pydantic_core",
            "dotenv",
            "phone_agent",
            "phone_agent.agent",
            "phone_agent.adb",
            "phone_agent.actions",
            "phone_agent.config",
            "phone_agent.model",
        ]
        for imp in hidden_imports:
            cmd.extend(["--hidden-import", imp])

        # Add data files
        cmd.extend(["--add-data", "phone_agent/config;phone_agent/config"])

        # Entry point
        cmd.append(str(project_root / "main.py"))

    return run_command(cmd, "Building executable")


def verify_build() -> bool:
    """Verify the build was successful."""
    project_root = Path(__file__).parent
    exe_path = project_root / "dist" / "phone_agent.exe"

    if not exe_path.exists():
        print(f"\nERROR: Executable not found at {exe_path}")
        return False

    # Copy .env.example to dist directory
    env_example = project_root / ".env.example"
    dist_env_example = project_root / "dist" / ".env.example"
    if env_example.exists():
        shutil.copy(env_example, dist_env_example)
        print(f"\nCopied .env.example to {dist_env_example}")

    # Copy contact QR code to dist directory
    qrcode_file = project_root / "contact_qrcode.png"
    dist_qrcode = project_root / "dist" / "contact_qrcode.png"
    if qrcode_file.exists():
        shutil.copy(qrcode_file, dist_qrcode)
        print(f"Copied contact_qrcode.png to {dist_qrcode}")

    size_mb = exe_path.stat().st_size / (1024 * 1024)
    print(f"\n{'='*50}")
    print("BUILD SUCCESSFUL!")
    print(f"{'='*50}")
    print(f"\nExecutable: {exe_path}")
    print(f"Size: {size_mb:.1f} MB")

    print("\nUsage:")
    print("  1. Copy dist\\.env.example to dist\\.env")
    print("  2. Edit dist\\.env with your configuration")
    print("  3. Run the exe from the dist directory")

    print("\nExamples:")
    print(f"  cd dist && phone_agent.exe --help")
    print(f"  cd dist && phone_agent.exe --list-devices")
    print(f'  cd dist && phone_agent.exe "Open Chrome browser"')

    return True


def main():
    parser = argparse.ArgumentParser(description="Build Phone Agent executable")
    parser.add_argument(
        "--no-spec",
        action="store_true",
        help="Don't use spec file, build from scratch",
    )
    parser.add_argument(
        "--onedir",
        action="store_true",
        help="Create one-directory bundle instead of one-file",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean build artifacts before building",
    )
    parser.add_argument(
        "--no-upx",
        action="store_true",
        help="Disable UPX compression",
    )
    parser.add_argument(
        "--skip-deps",
        action="store_true",
        help="Skip dependency installation",
    )
    args = parser.parse_args()

    print("=" * 50)
    print("Phone Agent EXE Build Script")
    print("=" * 50)
    print(f"Python: {sys.executable}")
    print(f"Version: {sys.version}")

    # Clean if requested
    if args.clean:
        clean_build()

    # Check/install PyInstaller
    if not check_pyinstaller():
        sys.exit(1)

    # Install dependencies
    if not args.skip_deps:
        install_dependencies()
        # Install optional dotenv
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "python-dotenv"],
            capture_output=True,
        )

    # Clean build directories
    clean_build()

    # Build
    if not build_exe(
        use_spec=not args.no_spec,
        onefile=not args.onedir,
        use_upx=not args.no_upx,
    ):
        sys.exit(1)

    # Verify
    if not verify_build():
        sys.exit(1)


if __name__ == "__main__":
    main()
