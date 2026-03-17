# -*- mode: python ; coding: utf-8 -*-
import os
from pathlib import Path

from PyInstaller.utils.hooks import (
    collect_submodules,
    collect_data_files,
    collect_dynamic_libs,
)
from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT
from PyInstaller.utils.hooks.qt import pyside6_library_info

# === 项目根目录（按你的路径）===
PROJECT_ROOT = Path(r"C:\ZJR\AscetTool").resolve()
if not PROJECT_ROOT.exists():
    raise SystemExit(f"项目根目录不存在: {PROJECT_ROOT}")
print(f"项目根目录: {PROJECT_ROOT}")

# 资源目录
SVG_DIR = PROJECT_ROOT / "svg"
KB_DIR = PROJECT_ROOT / "RAG" / "code_analysis_knowledge"
RAG_DIR = PROJECT_ROOT / "RAG"

# 图标
ICON_PATH = SVG_DIR / "logo.ico"
icon = str(ICON_PATH) if ICON_PATH.exists() else None
if icon:
    print(f"✓ 使用ICO图标: {icon}")
else:
    print(f"警告: 图标文件不存在: {ICON_PATH}，将使用默认图标")

# === datas：用 Tree 直接收整目录（含子目录）===
# 第二个参数为打包后的目标前缀路径
datas = []
if SVG_DIR.exists():
    datas.append((str(SVG_DIR), "svg"))  # 整个 svg/ 目录
else:
    print(f"警告: SVG目录不存在: {SVG_DIR}")

if KB_DIR.exists():
    datas.append((str(KB_DIR), "RAG/code_analysis_knowledge"))  # 知识库
    # 保险：把 RAG 根也带上（如需其他资源）
    if RAG_DIR.exists():
        datas.append((str(RAG_DIR), "RAG"))
else:
    print(f"❌ 错误: 知识库目录不存在: {KB_DIR}")
    if RAG_DIR.exists():
        print(f"RAG目录内容: {os.listdir(RAG_DIR)}")

# === binaries：faiss/faiss_cpu 的本地动态库（若有）===
binaries = []
try:
    binaries += collect_dynamic_libs("faiss")  # import 名通常是 faiss
except Exception:
    pass
try:
    binaries += collect_dynamic_libs("faiss_cpu")  # 兼容 import 名为 faiss_cpu 的场景
except Exception:
    pass

# === hiddenimports：PySide6 常见模块 + 你的用到的模块 ===
hiddenimports = [
    # PySide6 基础
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "PySide6.QtSvg",
    "PySide6.QtOpenGL",
    "PySide6.QtOpenGLWidgets",
    "PySide6.QtPrintSupport",
    "PySide6.QtNetwork",
    "shiboken6",

    # 数据/网络/文档
    "numpy",
    "pandas",
    "requests",
    "markdown",

    # 其他
    "tqdm",

    # Windows 相关
    "win32com.client",
    "pythoncom",

    # RAG/FAISS
    "faiss",       # 若你的代码 import faiss
    "faiss_cpu",   # 若你的代码 import faiss_cpu
]

# 你点名要额外打包的模块文件（不靠 import 链收集时）
manual_module_files = [
    "RagCoreV1.py",
    "Structurefliter.py",
    "token_tracker.py",
    "AscetToolCallv14.py",
    "AscetdsdTool.py",
    "model_config.py",
    "response_handler.py",
    "dSD_GenToolV10.py",
    "AscetAgentv8GPTNVV3.py",
    "ai_error_arbitrator.py",
    "util/detect_current_ascet.py",
    "util/Spinner.py",
]

# 把这些模块当作普通数据文件塞进根目录（保持相对结构）
for rel in manual_module_files:
    src = PROJECT_ROOT / rel
    if src.exists():
        # 目标目录：如果包含子目录，保持相同结构
        dst = str(Path(rel).parent) if Path(rel).parent.as_posix() != "." else "."
        datas.append((str(src), dst))
        print(f"打包模块文件: {rel}")
    else:
        print(f"警告: 模块文件不存在: {rel}")

# 入口脚本
entry_script = str(PROJECT_ROOT / "GUImainv93.py")

a = Analysis(
    [entry_script],
    pathex=[str(PROJECT_ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],        # 如有自定义 hook，可把目录加进来
    hooksconfig={},
    runtime_hooks=[],    # 如需在启动时设置环境变量，可放一个 py 文件到这里
    excludes=[
        "tkinter",
        "matplotlib",     # 你明确排除
        "scipy",
        # 排除 PyQt5（避免与 PySide6 混淆）
        "PyQt5",
        "PyQt5.QtCore",
        "PyQt5.QtWidgets",
        "PyQt5.QtGui",
        "PyQt5.QtSvg",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="AscetUnitCopilotV3_3",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,         # GUI 程序用 False
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="AscetUnitCopilotV3_3",
)
