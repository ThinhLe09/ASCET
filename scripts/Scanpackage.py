#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, ast, argparse, csv, pathlib, re
from collections import defaultdict
from typing import Set, Dict, List, Tuple

# 3.10+ 有 stdlib 模块名集合；老版本兜底一个最小集合
try:
    from sys import stdlib_module_names as _stdlib
    _STDLIB = set(_stdlib)
except Exception:
    _STDLIB = {
        "sys","os","re","json","time","math","pathlib","typing","itertools",
        "functools","subprocess","threading","multiprocessing","asyncio",
        "logging","argparse","collections","dataclasses","enum","inspect",
        "importlib","unittest","http","urllib","email","hashlib","hmac",
        "zipfile","tarfile","tempfile","shutil","contextlib","statistics",
        "sqlite3","uuid","base64","heapq","pickle","glob","csv"
    }

# 尝试映射 顶级包名 -> pip 发行包
try:
    from importlib.metadata import packages_distributions
    _PKG_MAP = packages_distributions()  # {top_level_module: [dist1, dist2]}
except Exception:
    _PKG_MAP = {}

IGNORE_DIRS = {".git", ".venv", "venv", ".mypy_cache", ".pytest_cache", "__pycache__", "build", "dist", ".eggs", ".idea", ".vscode", ".ruff_cache"}
PY_FILE_RE = re.compile(r".*\.pyi?$")

def iter_py_files(root: pathlib.Path):
    for dirpath, dirnames, filenames in os.walk(root):
        # 过滤常见目录
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS and not d.startswith(".")]
        for fn in filenames:
            if PY_FILE_RE.match(fn):
                yield pathlib.Path(dirpath) / fn

def extract_imports_from_file(path: pathlib.Path) -> List[Tuple[str, int]]:
    """返回 [(top_level_module, lineno), ...]"""
    out = []
    try:
        code = path.read_text(encoding="utf-8")
    except Exception:
        try:
            code = path.read_text(encoding="latin-1")
        except Exception:
            return out
    try:
        tree = ast.parse(code, filename=str(path))
    except SyntaxError:
        return out

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = (alias.name.split(".")[0]).strip()
                if top:
                    out.append((top, node.lineno))
        elif isinstance(node, ast.ImportFrom):
            if node.module is None:  # from . import x
                continue
            top = node.module.split(".")[0]
            if top:
                out.append((top, node.lineno))
        # 粗略捕捉 importlib.import_module("pkg.sub")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if getattr(node.func, "attr", "") == "import_module":
                if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                    s = node.args[0].value
                    top = s.split(".")[0]
                    if top:
                        out.append((top, node.lineno))
    return out

def main():
    ap = argparse.ArgumentParser(description="扫描项目用到的 Python 包（静态）")
    ap.add_argument("root", nargs="?", default=".", help="项目根目录（默认当前目录）")
    args = ap.parse_args()
    root = pathlib.Path(args.root).resolve()

    usage: Dict[str, List[Tuple[str,int]]] = defaultdict(list)  # top -> [(file, line)]
    files = list(iter_py_files(root))
    for f in files:
        for top, lineno in extract_imports_from_file(f):
            usage[top].append((str(f.relative_to(root)), lineno))

    # 过滤：排除标准库、自身包（项目顶级包名）
    project_top_names: Set[str] = set(p.name for p in root.iterdir() if p.is_dir() and (p / "__init__.py").exists())
    results = []
    for top, refs in sorted(usage.items()):
        if top in _STDLIB:
            continue
        if top in project_top_names:
            continue
        dists = _PKG_MAP.get(top, [])
        results.append((top, ", ".join(dists) if dists else "-", len(refs), refs))

    # 输出 Markdown
    md_path = root / "imports_report.md"
    with md_path.open("w", encoding="utf-8") as f:
        f.write("# Imports Report\n\n")
        f.write("| 顶级包 | pip 发行包 | 引用次数 | 示例位置（最多 5 个） |\n")
        f.write("|---|---|---:|---|\n")
        for top, dist, cnt, refs in results:
            sample = "; ".join(f"{file}:{lineno}" for file, lineno in refs[:5])
            f.write(f"| `{top}` | {dist} | {cnt} | {sample} |\n")

    # 输出 CSV（便于表格处理）
    csv_path = root / "imports_report.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as cf:
        writer = csv.writer(cf)
        writer.writerow(["top_module", "pip_distribution", "ref_count", "all_refs(file:line)"])
        for top, dist, cnt, refs in results:
            writer.writerow([top, dist, cnt, " | ".join(f"{f}:{ln}" for f, ln in refs)])

    # 控制台简表
    print(f"共发现 {len(results)} 个疑似第三方包：")
    for top, dist, cnt, refs in results[:30]:  # 控制台只列前 30 个
        print(f"- {top:<20} pkg: {dist:<30} refs: {cnt}")

    print(f"\n已生成：{md_path}")
    print(f"已生成：{csv_path}")
    print("\n提示：")
    print("1) 列里的“pip 发行包”可能为空（找不到映射），这类包名通常与分发名不同，如 'cv2' -> 'opencv-python'。")
    print("2) 静态分析看不到运行期条件导入/插件式导入，若要更保险，建议结合一次运行时导入日志。")
    print("   在入口最顶部加：")
    print("   import sys, atexit, time; atexit.register(lambda: open(f\"imported_modules_{int(time.time())}.txt\",\"w\").write('\\n'.join(sorted(sys.modules.keys()))))")

if __name__ == "__main__":
    main()
