# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['D:\\aicode\\tools\\Open-AutoGLM\\dist\\ui_main.py'],
    pathex=[],
    binaries=[],
    datas=[('D:\\aicode\\tools\\Open-AutoGLM\\phone_agent', 'phone_agent')],
    hiddenimports=['phone_agent', 'phone_agent.agent', 'phone_agent.model', 'phone_agent.model.client', 'phone_agent.adb', 'phone_agent.adb.device', 'phone_agent.adb.screenshot', 'phone_agent.adb.input', 'phone_agent.adb.connection', 'phone_agent.actions', 'phone_agent.actions.handler', 'phone_agent.config', 'phone_agent.config.apps', 'phone_agent.config.prompts', 'phone_agent.config.prompts_zh', 'phone_agent.config.prompts_en', 'phone_agent.config.i18n', 'openai', 'httpx', 'PIL', 'PIL.Image'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'numpy', 'scipy', 'pandas', 'pytest'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='PhoneAgent',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=['PIL*', '_avif*', '*.pyd'],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
