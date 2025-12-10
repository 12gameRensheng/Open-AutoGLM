# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Phone Agent.

Usage:
    pyinstaller phone_agent.spec

Note:
    - .env file is NOT bundled into the exe
    - The exe will read .env from the current working directory at runtime
    - Users should create a .env file in the same directory as the exe
"""

import sys
from pathlib import Path

block_cipher = None

# Get the project root directory
project_root = Path(SPECPATH)

# Collect all phone_agent package data
phone_agent_path = project_root / 'phone_agent'

a = Analysis(
    ['main.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        # Include the phone_agent package config files
        # NOTE: Do NOT include .env files - they should be read from cwd at runtime
        (str(phone_agent_path / 'config'), 'phone_agent/config'),
    ],
    hiddenimports=[
        # Core dependencies
        'PIL',
        'PIL.Image',
        'openai',
        'openai.resources',
        'openai.resources.chat',
        'openai.resources.chat.completions',
        'openai.resources.models',
        'httpx',
        'httpcore',
        'certifi',
        'charset_normalizer',
        'idna',
        'urllib3',
        'anyio',
        'sniffio',
        'h11',
        'distro',
        'tqdm',
        'pydantic',
        'pydantic_core',
        'annotated_types',
        'typing_extensions',
        # Phone agent modules
        'phone_agent',
        'phone_agent.agent',
        'phone_agent.adb',
        'phone_agent.adb.connection',
        'phone_agent.adb.device',
        'phone_agent.adb.input',
        'phone_agent.adb.screenshot',
        'phone_agent.actions',
        'phone_agent.actions.handler',
        'phone_agent.config',
        'phone_agent.config.apps',
        'phone_agent.config.i18n',
        'phone_agent.config.prompts',
        'phone_agent.config.prompts_en',
        'phone_agent.config.prompts_zh',
        'phone_agent.model',
        'phone_agent.model.client',
        # Optional dotenv for runtime .env loading
        'dotenv',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unnecessary modules to reduce size
        'tkinter',
        'matplotlib',
        'numpy',
        'scipy',
        'pandas',
        'pytest',
        'black',
        'mypy',
        'ruff',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='phone_agent',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # CLI application, needs console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon path here if you have one: icon='icon.ico'
)
