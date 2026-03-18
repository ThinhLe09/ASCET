# 📋 Example Implementation: Integrated Tree Building
# Use this file as a reference for implementing the tree functionality in GUImainv93.py

import sys
import os
from typing import Dict, Any
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTreeWidget, QTreeWidgetItem, QMessageBox
from PySide6.QtCore import Qt

# This assumes you have imported the updated GUImainv93 module


class TreeIntegrationExample:
    """
    Example implementation showing how to integrate the new tree scanning
    and popup functionality into the existing GUImainv93.py main window.
    
    These methods should be added to the AscetAgentMainWindow class.
    """
    
    # =====================================================================
    # STEP 1: Scan ASCET Database with Full Tree Hierarchy
    # =====================================================================
    
    def step1_scan_ascet_database_tree(self):
        """
        Replaces or enhances existing step1_auto_detect_folders method.
        Scans entire ASCET database and builds complete folder/class tree.
        """
        self.log("=" * 80)
        self.log("BƯỚC 1: Quét Cây ASCET Database Đầy Đủ")
        self.log("=" * 80)
        
        # Show loading indicator
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        
        try:
            # Scan database
            self.log("🔍 Đang quét cây database ASCET...")
            tree_structure = self.data_core.scan_ascet_database_tree("6.1.5")
            
            if not tree_structure:
                self.log("❌ Quét database thất bại")
                self.progress_bar.setVisible(False)
                return
            
            # Build UI tree
            self.log("📊 Đang xây dựng cây hiển thị...")
            self._build_tree_from_ascet_structure(tree_structure)
            
            folder_count = len(tree_structure.get('folders', []))
            self.log(f"✅ Quét thành công: {folder_count} folders")
            self.log("💡 Gợi ý: Double-click 📊 để mở diagram trong popup")
            
        except Exception as e:
            self.log(f"❌ Lỗi: {str(e)}")
        
        finally:
            self.progress_bar.setVisible(False)
    
    # =====================================================================
    # Helper: Build Tree from ASCET Structure
    # =====================================================================
    
    def _build_tree_from_ascet_structure(self, tree_structure: Dict):
        """
        Build QTreeWidget from ASCET database structure.
        
        Tree format:
        🏠 ASCET Database
        ├── 📁 Folder1
        │   ├── 📊 Class With Diagram
        │   ├── 📄 Class Without Diagram
        │   └── 📁 SubFolder
        │       └── 📊 Another Diagram
        └── 📁 Folder2
            └── 📊 Diagram Class
        """
        self.tree_widget.clear()
        self.available_classes.clear()
        
        # Create root item
        root_name = tree_structure.get('name', 'ASCET Database')
        root_item = QTreeWidgetItem(self.tree_widget, [f"🏠 {root_name}"])
        root_item.setExpanded(True)
        
        # Recursively build tree
        for folder in tree_structure.get('folders', []):
            folder_item = self._build_folder_tree_item(folder)
            if folder_item:
                root_item.addChild(folder_item)
        
        # Expand all items
        self.tree_widget.expandAll()
    
    def _build_folder_tree_item(self, folder_data: Dict) -> QTreeWidgetItem:
        """
        Recursively create QTreeWidgetItem for folder and its contents.
        """
        folder_name = folder_data.get('name', 'Unknown')
        folder_path = folder_data.get('path', '')
        
        # Create folder item
        folder_item = QTreeWidgetItem([f"📁 {folder_name}"])
        folder_item.setData(0, Qt.UserRole, {
            "type": "folder",
            "path": folder_path
        })
        
        # Add sub-folders recursively
        for subfolder in folder_data.get('sub_folders', []):
            subfolder_item = self._build_folder_tree_item(subfolder)
            if subfolder_item:
                folder_item.addChild(subfolder_item)
        
        # Add classes
        for class_data in folder_data.get('classes', []):
            class_name = class_data.get('name', 'Unknown')
            class_path = class_data.get('path', '')
            has_diagram = class_data.get('has_diagram', False)
            
            # Use emoji to indicate diagram availability
            icon = "📊" if has_diagram else "📄"
            class_item = QTreeWidgetItem([f"{icon} {class_name}"])
            
            # Store metadata
            class_item.setData(0, Qt.UserRole, {
                "type": "class",
                "name": class_name,
                "path": class_path,
                "has_diagram": has_diagram,
                "xml_path": class_path  # Can be used to construct XML export path
            })
            
            # Store for quick lookup
            display_name = f"{icon} {class_name}"
            self.available_classes[display_name] = {
                "name": class_name,
                "path": class_path,
                "has_diagram": has_diagram,
                "type": "ascet_class"
            }
            
            folder_item.addChild(class_item)
        
        return folder_item
    
    # =====================================================================
    # STEP 2: Handle Diagram Selection - Open in Popup
    # =====================================================================
    
    def on_tree_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        """
        Replace existing on_diagram_selected method.
        Opens diagram in lightweight popup dialog.
        """
        item_data = item.data(0, Qt.UserRole)
        
        if not item_data:
            return
        
        item_type = item_data.get('type', '')
        
        if item_type == 'class' and item_data.get('has_diagram'):
            self._open_diagram_in_popup(item, item_data)
        elif item_type == 'folder':
            self.log(f"📁 Folder: {item_data.get('name', 'Unknown')}")
    
    def _open_diagram_in_popup(self, item: QTreeWidgetItem, item_data: Dict):
        """
        Open diagram in a lightweight popup dialog.
        """
        class_name = item_data.get('name', 'Unknown')
        class_path = item_data.get('path', '')
        
        self.log(f"🔍 Đang tải diagram: {class_name}...")
        
        try:
            # Parse diagram XML
            # Note: You may need to export the class to XML first
            xml_path = self._export_class_to_xml(class_path)
            
            if not xml_path:
                self.log(f"❌ Không thể xuất XML cho class: {class_name}")
                return
            
            # Parse diagram
            diagram_data = self.data_core.parse_diagram_xml(xml_path, class_name)
            
            if not diagram_data:
                self.log(f"❌ Không thể parse diagram XML")
                return
            
            # Open in popup
            from GUImainv93 import DiagramPopupDialog  # Import the popup class
            popup = DiagramPopupDialog(diagram_data, parent=self)
            popup.show()
            
            self.log(f"✅ Mở diagram: {class_name}")
            self.log(f"   Blocks: {len(diagram_data.get('blocks', []))} | "
                    f"Connections: {len(diagram_data.get('connections', []))}")
            
        except Exception as e:
            self.log(f"❌ Lỗi mở diagram: {str(e)}")
    
    def _export_class_to_xml(self, class_path: str) -> str:
        """
        Helper: Export class to XML if needed.
        Returns path to XML file.
        """
        # This is a placeholder - implement based on your ASCET API knowledge
        # You might need to:
        # 1. Connect to ASCET via COM
        # 2. Find the class by path
        # 3. Export it to XML
        # 4. Return the XML path
        
        # For now, return None (implement later with actual ASCET export)
        return None
    
    # =====================================================================
    # ALTERNATIVE: Work with XML Exports
    # =====================================================================
    
    def scan_xml_directory_for_diagrams(self):
        """
        Alternative method: Scan pre-exported XML directory for diagrams.
        Use this if direct ASCET COM access is unreliable.
        """
        self.log("=" * 80)
        self.log("BƯỚC 1 (Phương Án B): Quét XML Directory")
        self.log("=" * 80)
        
        # Open folder dialog
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Chọn folder chứa XML exports",
            self.settings.value("paths/last_xml_directory", "")
        )
        
        if not folder_path:
            return
        
        # Save path
        self.settings.setValue("paths/last_xml_directory", folder_path)
        
        # Scan and build tree
        self.log(f"🔍 Đang quét: {folder_path}")
        self.log("📊 Đang xây dựng cây từ XML...")
        
        self._build_tree_from_xml_directory(folder_path)
        
        self.log("✅ Quét XML directory hoàn tất")
    
    def _build_tree_from_xml_directory(self, root_path: str):
        """
        Build tree from XML files in directory structure.
        """
        self.tree_widget.clear()
        self.available_classes.clear()
        
        root_item = QTreeWidgetItem(self.tree_widget, [f"🏠 {os.path.basename(root_path)}"])
        root_item.setExpanded(True)
        
        for root_dir, dirs, files in os.walk(root_path):
            # Create folder item
            rel_path = os.path.relpath(root_dir, root_path)
            if rel_path == '.':
                parent_item = root_item
            else:
                folder_name = os.path.basename(root_dir)
                parent_item = QTreeWidgetItem(root_item, [f"📁 {folder_name}"])
            
            # Process XML files
            for file in files:
                if file.endswith('.amd'):
                    file_path = os.path.join(root_dir, file)
                    
                    # Check if it's a diagram
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            if '<SimpleElement' in content or '<Connection' in content:
                                # It's a diagram
                                clean_name = file.replace('.specification.amd', '').replace('.dp.amd', '').replace('.amd', '')
                                diagram_item = QTreeWidgetItem(parent_item, [f"📊 {clean_name}"])
                                
                                diagram_item.setData(0, Qt.UserRole, {
                                    "type": "diagram",
                                    "name": clean_name,
                                    "xml_path": file_path,
                                    "has_diagram": True
                                })
                                
                                # Store for lookup
                                display_name = f"📊 {clean_name}"
                                self.available_classes[display_name] = {
                                    "name": clean_name,
                                    "path": file_path,
                                    "has_diagram": True,
                                    "type": "xml_diagram"
                                }
                    except:
                        pass
        
        self.tree_widget.expandAll()


# =====================================================================
# Summary: Integration Checklist
# =====================================================================

"""
To integrate these changes into GUImainv93.py:

✅ DONE: Methods added to AscetDataCore
   - parse_diagram_xml()
   - scan_ascet_database_tree()
   - _scan_folder_recursive()

✅ DONE: DiagramPopupDialog class added

⏳ TODO: Add to AscetAgentMainWindow class:
   1. Step 1 method:
      - Rename/enhance step1_auto_detect_folders()
      - Or add new step1_scan_ascet_database_tree()
      - Or add both for flexibility
   
   2. Update tree building methods:
      - _build_tree_from_ascet_structure()
      - _build_folder_tree_item()
   
   3. Update diagram selection handler:
      - on_tree_item_double_clicked() (or rename existing)
      - _open_diagram_in_popup()
      - _export_class_to_xml() (helper)
   
   4. Optional: XML scanning method:
      - scan_xml_directory_for_diagrams()
      - _build_tree_from_xml_directory()

✅ BENEFITS:
   - Full ASCET database hierarchy in tree view
   - Emoji markers for diagram availability (📊 vs 📄)
   - Lightweight popup for diagram viewing
   - Zoom/pan/export in popup window
   - No changes to main window when popup is open
   - Multiple popups can be open simultaneously

🎯 WORKFLOW:
   BƯỚC 1: Quét Thư mục (ASCET or XML)
   ↓
   BƯỚC 2: Auto-build tree with full hierarchy
   ↓
   Double-click 📊 diagram
   ↓
   Popup opens with zoom/pan/export
   ↓
   Export from popup (PNG + optional JSON)
"""
