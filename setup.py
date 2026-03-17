#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ASCET Unit Copilot Auto Build Script
Automatically invoke PyInstaller and handle knowledge base folder packaging
"""

import os
import sys
import json
import shutil
import subprocess
import time
from pathlib import Path
from typing import List, Dict, Tuple


class PackagingConfig:
    """Packaging configuration management"""
    
    def __init__(self, config_file: str = "build_config.json"):
        self.config_file = config_file
        self.default_config = {
            "spec_file": "buildv1.spec",
            "main_file": "GUImainv93.py",
            "exe_name": "AscetUnitCopilotV3_3",
            "output_dir": "AscetUnitCopilotV3_3",
            "required_modules": [
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
                "util/Spinner.py"
            ],
            "resource_directories": [
                {"source": "svg", "target": "svg"},
                {"source": "RAG", "target": "RAG"}
            ],
            "exclude_patterns": [
                "*.pyc",
                "__pycache__",
                ".git",
                ".gitignore",
                "*.log",
                "test_*",
                "*_test.py"
            ]
        }
        self.config = self.load_config()
    
    def load_config(self) -> dict:
        """Load configuration from file or create default"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                print(f"Loaded configuration from: {self.config_file}")
                return {**self.default_config, **config}  # Merge with defaults
            except Exception as e:
                print(f"Failed to load config file: {e}")
                print("Using default configuration")
        else:
            self.save_config(self.default_config)
            print(f"Created default config file: {self.config_file}")
        
        return self.default_config.copy()
    
    def save_config(self, config: dict = None):
        """Save current configuration to file"""
        config_to_save = config or self.config
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_to_save, f, indent=2, ensure_ascii=False)
            print(f"Configuration saved to: {self.config_file}")
        except Exception as e:
            print(f"Failed to save config: {e}")
    
    def update_config(self, updates: dict):
        """Update configuration"""
        self.config.update(updates)
        self.save_config()


class AutoBuilder:
    def __init__(self, config_file: str = None):
        self.project_root = Path(__file__).parent.absolute()
        self.packaging_config = PackagingConfig(config_file or "build_config.json")
        self.config = self.packaging_config.config
        
        # Dynamic paths based on config
        self.spec_file = self.config["spec_file"]
        self.dist_dir = self.project_root / "dist"
        self.build_dir = self.project_root / "build"
        self.exe_dir = self.dist_dir / self.config["output_dir"]
        
        # RAG knowledge base paths
        self.rag_source_dir = self.project_root / "RAG" / "code_analysis_knowledge"
        self.rag_target_dir = self.exe_dir / "RAG" / "code_analysis_knowledge"
        
        print(f"Project Root: {self.project_root}")
        print(f"SPEC File: {self.spec_file}")
        print(f"Main File: {self.config['main_file']}")
        print(f"Output Directory: {self.exe_dir}")
    
    def check_prerequisites(self) -> bool:
        """Check packaging prerequisites"""
        print("\n" + "="*50)
        print("Checking Prerequisites...")
        print("="*50)
        
        checks_passed = True
        
        # Check SPEC file
        spec_path = self.project_root / self.spec_file
        if not spec_path.exists():
            print(f"ERROR: SPEC file not found: {spec_path}")
            checks_passed = False
        else:
            print(f"OK: SPEC file exists: {spec_path}")
        
        # Check PyInstaller
        try:
            result = subprocess.run(['pyinstaller', '--version'], 
                                 capture_output=True, text=True)
            if result.returncode == 0:
                print(f"OK: PyInstaller version: {result.stdout.strip()}")
            else:
                print("ERROR: PyInstaller not available")
                checks_passed = False
        except FileNotFoundError:
            print("ERROR: PyInstaller not installed. Run: pip install pyinstaller")
            checks_passed = False
        
        # Check main program file
        main_file = self.project_root / self.config["main_file"]
        if not main_file.exists():
            print(f"ERROR: Main program file not found: {main_file}")
            checks_passed = False
        else:
            print(f"OK: Main program file exists: {main_file}")
        
        # Check PySide6
        try:
            import PySide6
            print(f"OK: PySide6 installed: {PySide6.__version__}")
        except ImportError:
            print("ERROR: PySide6 not installed. Run: pip install PySide6")
            checks_passed = False
        
        # Check required modules
        missing_modules = []
        for module in self.config["required_modules"]:
            module_path = self.project_root / module
            if not module_path.exists():
                missing_modules.append(module)
        
        if missing_modules:
            print(f"WARNING: Missing optional modules: {len(missing_modules)}")
            for module in missing_modules:
                print(f"  - {module}")
        else:
            print(f"OK: All {len(self.config['required_modules'])} required modules found")
        
        # Check knowledge base directory
        if self.rag_source_dir.exists():
            file_count = len(list(self.rag_source_dir.rglob("*.*")))
            print(f"OK: RAG knowledge base directory exists with {file_count} files")
        else:
            print(f"WARNING: RAG knowledge base directory not found: {self.rag_source_dir}")
        
        # Check resource directories
        for resource in self.config["resource_directories"]:
            src_path = self.project_root / resource["source"]
            if src_path.exists():
                if src_path.is_dir():
                    file_count = len(list(src_path.rglob("*.*")))
                    print(f"OK: Resource directory '{resource['source']}' contains {file_count} files")
                else:
                    print(f"OK: Resource file '{resource['source']}' exists")
            else:
                is_optional = resource.get("optional", False)
                status = "WARNING" if is_optional else "ERROR"
                print(f"{status}: Resource '{resource['source']}' not found")
                if not is_optional:
                    checks_passed = False
        
        return checks_passed
    
    def clean_build_dirs(self):
        """Clean build directories"""
        print("\n" + "="*50)
        print("Cleaning Build Directories...")
        print("="*50)
        
        dirs_to_clean = [self.dist_dir, self.build_dir]
        
        for dir_path in dirs_to_clean:
            if dir_path.exists():
                print(f"Removing directory: {dir_path}")
                shutil.rmtree(dir_path, ignore_errors=True)
                time.sleep(0.5)  # Wait for filesystem
            else:
                print(f"Directory does not exist, skipping: {dir_path}")
    
    def run_pyinstaller(self) -> bool:
        """Run PyInstaller"""
        print("\n" + "="*50)
        print("Running PyInstaller...")
        print("="*50)
        
        cmd = ['pyinstaller', '--clean', '--noconfirm', self.spec_file]
        print(f"Executing command: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(cmd, cwd=self.project_root, 
                                  capture_output=False, text=True)
            
            if result.returncode == 0:
                print("OK: PyInstaller executed successfully")
                return True
            else:
                print(f"ERROR: PyInstaller failed with return code: {result.returncode}")
                return False
                
        except Exception as e:
            print(f"ERROR: PyInstaller execution exception: {e}")
            return False
    
    def copy_rag_knowledge_base(self) -> bool:
        """Manually copy RAG knowledge base folder (solve packaging issue)"""
        print("\n" + "="*50)
        print("Copying RAG Knowledge Base...")
        print("="*50)
        
        if not self.rag_source_dir.exists():
            print(f"WARNING: RAG source directory not found, skipping: {self.rag_source_dir}")
            return True
        
        if not self.exe_dir.exists():
            print(f"ERROR: Executable directory not found: {self.exe_dir}")
            return False
        
        try:
            # Ensure target parent directory exists
            self.rag_target_dir.parent.mkdir(parents=True, exist_ok=True)
            
            # Remove existing target directory if it exists
            if self.rag_target_dir.exists():
                print(f"Removing existing target directory: {self.rag_target_dir}")
                shutil.rmtree(self.rag_target_dir)
            
            # Copy entire knowledge base directory
            print(f"Copying: {self.rag_source_dir} -> {self.rag_target_dir}")
            shutil.copytree(self.rag_source_dir, self.rag_target_dir)
            
            # Count copied files
            copied_files = list(self.rag_target_dir.rglob("*.*"))
            print(f"OK: Successfully copied {len(copied_files)} files to knowledge base directory")
            
            # Show sample file list for verification
            if copied_files:
                print("Knowledge base file samples:")
                for i, file_path in enumerate(copied_files[:5]):  # Show first 5 files
                    rel_path = file_path.relative_to(self.rag_target_dir)
                    print(f"  - {rel_path}")
                if len(copied_files) > 5:
                    print(f"  ... and {len(copied_files) - 5} more files")
            
            return True
            
        except Exception as e:
            print(f"ERROR: Failed to copy RAG knowledge base: {e}")
            return False
    
    def copy_additional_resources(self) -> bool:
        """Copy other potentially missing resource files"""
        print("\n" + "="*50)
        print("Copying Additional Resources...")
        print("="*50)
        
        success_count = 0
        total_count = 0
        
        for resource in self.config["resource_directories"]:
            total_count += 1
            src_name = resource["source"]
            dst_name = resource["target"]
            is_optional = resource.get("optional", False)
            
            src_path = self.project_root / src_name
            dst_path = self.exe_dir / dst_name
            
            if src_path.exists():
                try:
                    # Skip if source is RAG (already handled separately)
                    if src_name == "RAG":
                        print(f"OK: Skipping RAG directory (handled separately)")
                        success_count += 1
                        continue
                    
                    if dst_path.exists():
                        if dst_path.is_dir():
                            shutil.rmtree(dst_path)
                        else:
                            dst_path.unlink()
                    
                    if src_path.is_dir():
                        shutil.copytree(src_path, dst_path)
                        file_count = len(list(dst_path.rglob("*.*")))
                        print(f"OK: Copied directory '{src_name}': {file_count} files")
                    else:
                        dst_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src_path, dst_path)
                        print(f"OK: Copied file '{src_name}'")
                    
                    success_count += 1
                    
                except Exception as e:
                    status = "WARNING" if is_optional else "ERROR"
                    print(f"{status}: Failed to copy '{src_name}': {e}")
                    if not is_optional:
                        return False
            else:
                status = "WARNING" if is_optional else "ERROR"
                print(f"{status}: Resource not found, skipping: {src_path}")
                if not is_optional:
                    return False
        
        print(f"Resource copying completed: {success_count}/{total_count} successful")
        return True
    
    def verify_build_result(self) -> bool:
        """Verify build results"""
        print("\n" + "="*50)
        print("Verifying Build Results...")
        print("="*50)
        
        # Check executable file
        exe_file = self.exe_dir / f"{self.config['exe_name']}.exe"
        if not exe_file.exists():
            print(f"ERROR: Executable file not found: {exe_file}")
            return False
        
        exe_size = exe_file.stat().st_size / (1024 * 1024)  # MB
        print(f"OK: Executable file exists: {exe_file.name} ({exe_size:.1f} MB)")
        
        # Check RAG knowledge base
        if self.rag_target_dir.exists():
            kb_files = list(self.rag_target_dir.rglob("*.*"))
            print(f"OK: RAG knowledge base included: {len(kb_files)} files")
        else:
            print(f"ERROR: RAG knowledge base directory missing: {self.rag_target_dir}")
            return False
        
        # Check critical components
        critical_components = [
            "PySide6",  # Check PySide6 directory or files
        ]
        
        for component in critical_components:
            found = list(self.exe_dir.rglob(f"*{component}*"))
            if found:
                print(f"OK: Found critical component: {component}")
            else:
                print(f"WARNING: Critical component not found: {component}")
        
        # Calculate final size statistics
        total_size = sum(f.stat().st_size for f in self.exe_dir.rglob("*") if f.is_file())
        total_size_mb = total_size / (1024 * 1024)
        total_files = len(list(self.exe_dir.rglob("*.*")))
        
        print(f"\nBuild Result Statistics:")
        print(f"  - Total Size: {total_size_mb:.1f} MB")
        print(f"  - Total Files: {total_files}")
        print(f"  - Output Directory: {self.exe_dir}")
        
        return True
    
    def create_launcher_script(self) -> bool:
        """Create launcher script (optional)"""
        print("\n" + "="*50)
        print("Creating Launcher Script...")
        print("="*50)
        
        # Create batch launcher script
        launcher_content = f"""@echo off
cd /d "%~dp0"
echo Starting ASCET Unit Copilot v3.3...
"{self.config['exe_name']}.exe"
if errorlevel 1 (
    echo.
    echo Program exited with error. Press any key to continue...
    pause >nul
)
"""
        
        launcher_path = self.exe_dir / "Launch ASCET Unit Copilot.bat"
        try:
            with open(launcher_path, 'w', encoding='gbk') as f:
                f.write(launcher_content)
            print(f"OK: Created launcher script: {launcher_path.name}")
            return True
        except Exception as e:
            print(f"WARNING: Failed to create launcher script: {e}")
            return False
    
    def generate_file_manifest(self) -> bool:
        """Generate manifest of packaged files"""
        print("\n" + "="*50)
        print("Generating File Manifest...")
        print("="*50)
        
        try:
            manifest = {
                "build_info": {
                    "build_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "project_root": str(self.project_root),
                    "exe_name": self.config["exe_name"],
                    "spec_file": self.spec_file
                },
                "files": [],
                "statistics": {}
            }
            
            # Collect all files
            all_files = list(self.exe_dir.rglob("*"))
            file_list = []
            total_size = 0
            
            for file_path in all_files:
                if file_path.is_file():
                    rel_path = file_path.relative_to(self.exe_dir)
                    file_size = file_path.stat().st_size
                    total_size += file_size
                    
                    file_info = {
                        "path": str(rel_path).replace("\\", "/"),
                        "size": file_size,
                        "size_mb": round(file_size / (1024 * 1024), 2)
                    }
                    file_list.append(file_info)
            
            # Sort by size (largest first)
            file_list.sort(key=lambda x: x["size"], reverse=True)
            manifest["files"] = file_list
            
            # Statistics
            manifest["statistics"] = {
                "total_files": len(file_list),
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2)
            }
            
            # Save manifest
            manifest_path = self.exe_dir / "build_manifest.json"
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2, ensure_ascii=False)
            
            print(f"OK: Generated file manifest: {manifest_path}")
            print(f"    Total files: {len(file_list)}")
            print(f"    Total size: {manifest['statistics']['total_size_mb']} MB")
            
            return True
            
        except Exception as e:
            print(f"WARNING: Failed to generate file manifest: {e}")
            return False
    
    def build(self) -> bool:
        """Execute complete build process"""
        print("ASCET Unit Copilot Auto Build Script")
        print("=" * 60)
        
        start_time = time.time()
        
        # Step 1: Check prerequisites
        if not self.check_prerequisites():
            print("\nERROR: Prerequisites check failed, terminating build")
            return False
        
        # Step 2: Clean build directories
        self.clean_build_dirs()
        
        # Step 3: Run PyInstaller
        if not self.run_pyinstaller():
            print("\nERROR: PyInstaller execution failed, terminating build")
            return False
        
        # Step 4: Manually copy RAG knowledge base
        if not self.copy_rag_knowledge_base():
            print("\nERROR: RAG knowledge base copy failed, terminating build")
            return False
        
        # Step 5: Copy additional resources
        if not self.copy_additional_resources():
            print("\nERROR: Additional resources copy failed, terminating build")
            return False
        
        # Step 6: Create launcher script
        self.create_launcher_script()
        
        # Step 7: Generate file manifest
        self.generate_file_manifest()
        
        # Step 8: Verify build results
        if not self.verify_build_result():
            print("\nERROR: Build result verification failed")
            return False
        
        # Build completed
        elapsed_time = time.time() - start_time
        print("\n" + "="*60)
        print(f"BUILD SUCCESSFUL! Time taken: {elapsed_time:.1f} seconds")
        print(f"Output Directory: {self.exe_dir}")
        print(f"Executable File: {self.config['exe_name']}.exe")
        print("="*60)
        
        return True


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="ASCET Unit Copilot Auto Build Script")
    parser.add_argument("--config", "-c", help="Configuration file path", default="build_config.json")
    parser.add_argument("--create-config", action="store_true", help="Create default configuration file")
    parser.add_argument("--verify-only", action="store_true", help="Only verify prerequisites without building")
    
    args = parser.parse_args()
    
    if args.create_config:
        config = PackagingConfig(args.config)
        config.save_config()
        print(f"Created configuration file: {args.config}")
        return 0
    
    builder = AutoBuilder(args.config)
    
    if args.verify_only:
        success = builder.check_prerequisites()
        print(f"\nPrerequisites check: {'PASSED' if success else 'FAILED'}")
        return 0 if success else 1
    
    try:
        success = builder.build()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n\nUser interrupted build process")
        return 1
    except Exception as e:
        print(f"\n\nBuild process exception: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())