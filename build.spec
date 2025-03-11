# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['image_processor.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('icon.png', '.'),  # 包含图标文件
        ('config.py', '.'),  # 包含配置文件
    ],
    hiddenimports=['PIL', 'boto3'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='盼趣图片压缩工具',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 设置为 False 不显示控制台窗口
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.png'  # 设置程序图标
) 