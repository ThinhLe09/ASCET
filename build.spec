# -*- mode: python ; coding: utf-8 -*-
import os

# 项目根目录
PROJECT_ROOT = r'C:\ZJR\AscetTool'

# 验证项目根目录
if not os.path.exists(PROJECT_ROOT):
    raise Exception(f"项目根目录不存在: {PROJECT_ROOT}")

print(f"项目根目录: {PROJECT_ROOT}")

# 收集SVG文件 - 确保包含所有SVG文件
svg_datas = []
svg_path = os.path.join(PROJECT_ROOT, 'svg')
if os.path.exists(svg_path):
    for file in os.listdir(svg_path):
        if file.endswith(('.svg', '.ico', '.png', '.jpg', '.jpeg')):
            src_file = os.path.join(svg_path, file)
            svg_datas.append((src_file, 'svg'))
            print(f"打包资源文件: svg/{file}")
else:
    print(f"警告: SVG目录不存在: {svg_path}")

# 收集知识库文件 - 修复版本
kb_datas = []
kb_path = os.path.join(PROJECT_ROOT, 'RAG', 'code_analysis_knowledge')

print(f"\n=== 检查知识库目录 ===")
print(f"知识库路径: {kb_path}")

if os.path.exists(kb_path):
    print(f"✓ 知识库目录存在")
    
    # 检查目录是否为空
    all_files = []
    for root, dirs, files in os.walk(kb_path):
        all_files.extend(files)
    
    if not all_files:
        print("⚠️  警告: 知识库目录为空，没有找到任何文件")
    else:
        print(f"发现 {len(all_files)} 个文件")
    
    file_count = 0
    for root, dirs, files in os.walk(kb_path):
        print(f"扫描目录: {root}")
        for file in files:
            src = os.path.join(root, file)
            rel_path = os.path.relpath(root, kb_path)
            
            # 修复：确保正确的目标路径结构
            if rel_path == '.':
                # 根目录下的文件直接放到 RAG/code_analysis_knowledge/
                dst_dir = os.path.join('RAG', 'code_analysis_knowledge')
            else:
                # 子目录文件保持相对路径结构
                dst_dir = os.path.join('RAG', 'code_analysis_knowledge', rel_path).replace('\\', '/')
            
            kb_datas.append((src, dst_dir))
            file_count += 1
            rel_src = os.path.relpath(src, PROJECT_ROOT)
            print(f"  ✓ 打包知识库文件: {rel_src} -> {dst_dir}/{file}")
    
    print(f"总共收集到 {file_count} 个知识库文件")
    
    # 额外添加整个RAG目录结构，确保目录结构完整
    if file_count > 0:
        # 添加空的 __init__.py 文件以确保目录结构
        init_files = [
            (os.path.join(PROJECT_ROOT, 'create_empty_init.py'), 'RAG'),
            (os.path.join(PROJECT_ROOT, 'create_empty_init.py'), os.path.join('RAG', 'code_analysis_knowledge'))
        ]
        
        # 创建临时的 __init__.py 文件（如果不存在）
        temp_init_path = os.path.join(PROJECT_ROOT, 'create_empty_init.py')
        if not os.path.exists(temp_init_path):
            try:
                with open(temp_init_path, 'w') as f:
                    f.write('# Auto-generated for directory structure\n')
                print(f"创建临时初始化文件: {temp_init_path}")
            except Exception as e:
                print(f"无法创建临时文件: {e}")
else:
    print(f"❌ 错误: 知识库目录不存在: {kb_path}")
    # 尝试列出RAG目录下的内容
    rag_path = os.path.join(PROJECT_ROOT, 'RAG')
    if os.path.exists(rag_path):
        print(f"RAG目录内容: {os.listdir(rag_path)}")

# Python模块文件
python_modules = [
    'RagCoreV1.py',
    'Structurefliter.py', 
    'token_tracker.py',
    'AscetToolCallv14.py',
    'AscetdsdTool.py',
    'model_config.py',
    'response_handler.py',
    'dSD_GenToolV10.py',
    'AscetAgentv8GPTNVV3.py',
    'ai_error_arbitrator.py',
    'util/detect_current_ascet.py',
    'util/Spinner.py'
]

module_datas = []
for module in python_modules:
    module_path = os.path.join(PROJECT_ROOT, module)
    if os.path.exists(module_path):
        module_datas.append((module_path, '.'))
        print(f"打包模块: {module}")
    else:
        print(f"警告: 模块文件不存在: {module}")

# 验证所有收集到的数据
print(f"\n=== 打包文件汇总 ===")
print(f"SVG文件: {len(svg_datas)} 个")
print(f"知识库文件: {len(kb_datas)} 个") 
print(f"模块文件: {len(module_datas)} 个")
print(f"总文件数: {len(svg_datas) + len(kb_datas) + len(module_datas)} 个")

if len(kb_datas) == 0:
    print("⚠️  警告: 没有收集到任何知识库文件！")
    print("请检查以下路径是否存在且包含文件:")
    print(f"  - {kb_path}")

# 设置图标路径
icon_path = None
potential_icon_path = os.path.join(PROJECT_ROOT, 'svg', 'logo.ico')

if potential_icon_path and os.path.exists(potential_icon_path):
    icon_path = potential_icon_path
    print(f"✓ 使用ICO图标: {icon_path}")
else:
    print(f"警告: 图标文件不存在: {potential_icon_path}")
    print("将使用默认图标")

# 添加运行时hook，确保目录结构
def Entrypoint(dist, group, name, **kwargs):
    import pkg_resources
    # 获取入口点
    ep = pkg_resources.get_entry_info(dist, group, name)
    # 修改sys.argv[0]以确保正确的路径解析
    script = '''
import sys
import os
# 确保RAG目录路径正确
if hasattr(sys, '_MEIPASS'):
    # PyInstaller环境下，确保RAG目录可访问
    rag_path = os.path.join(sys._MEIPASS, 'RAG')
    if os.path.exists(rag_path):
        print(f"RAG目录已找到: {rag_path}")
    else:
        print(f"警告: RAG目录未找到: {rag_path}")
        # 尝试创建目录（如果需要）
        try:
            os.makedirs(rag_path, exist_ok=True)
            print(f"已创建RAG目录: {rag_path}")
        except Exception as e:
            print(f"无法创建RAG目录: {e}")

%s
''' % (ep.module_name,)
    
    return script

a = Analysis(
    ['GUImainv93.py'],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=[
        *svg_datas,
        *kb_datas,
        *module_datas,
        # 明确添加整个RAG目录（作为备选方案）
        (os.path.join(PROJECT_ROOT, 'RAG'), 'RAG'),
    ],
    hiddenimports=[
        # PySide6相关
        'PySide6.QtCore',
        'PySide6.QtWidgets',
        'PySide6.QtGui',
        'PySide6.QtSvg',
        
        # 数据处理
        'numpy',
        'pandas',
        
        # 网络和文档
        'requests',
        'markdown',
        
        # 其他检测到的依赖
        'faiss',
        'win32com.client',
        'pythoncom',
        'pickle',
        'json',
        'xml.etree.ElementTree',
        'hashlib',
        'pathlib',
        'tqdm',
        're',
        'time',
        'datetime',
        'traceback',
        'shutil',
        'glob',
        'math',
        
        # PySide6额外的隐藏导入
        'PySide6.QtOpenGL',
        'PySide6.QtOpenGLWidgets', 
        'PySide6.QtPrintSupport',
        'PySide6.QtNetwork',
        'shiboken6',
        
        # RAG相关的额外导入
        'faiss_cpu',
      
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'scipy',
        # 排除PyQt5相关模块
        'PyQt5',
        'PyQt5.QtCore',
        'PyQt5.QtWidgets',
        'PyQt5.QtGui',
        'PyQt5.QtSvg',
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
    name='AscetUnitCopilotV3_3',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AscetUnitCopilotV3_3'
)

# 清理临时文件
temp_init_path = os.path.join(PROJECT_ROOT, 'create_empty_init.py')
if os.path.exists(temp_init_path):
    try:
        os.remove(temp_init_path)
        print(f"清理临时文件: {temp_init_path}")
    except Exception as e:
        print(f"清理临时文件失败: {e}")