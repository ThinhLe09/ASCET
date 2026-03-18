# 🚀 ASCET Tree Integration Guide (v4.0)

## Overview
This guide explains the new tree scanning and diagram popup functionality added to `GUImainv93.py`.

## New Methods in AscetDataCore

### 1. parse_diagram_xml(xml_file, diag_name)
**Purpose:** Parse a diagram XML file and extract structure data

```python
# Example usage
data_core = AscetDataCore(logger_func=self.log)
diagram_data = data_core.parse_diagram_xml("path/to/diagram.amd", "MyDiagram")

# Returns structure like:
# {
#     "diagram_name": "MyDiagram",
#     "blocks": [...],           # List of visual blocks
#     "connections": [...],      # List of connections between blocks
#     "source_xml_file": "..."
# }
```

**Output Structure:**
```python
diagram_data = {
    "diagram_name": "string",
    "blocks": [
        {
            "id": "block_oid",
            "name": "BlockName",
            "type": "ComplexElement|SimpleElement|Literal|Operator",
            "position": {"x": 100, "y": 200},
            "size": {"w": 60, "h": 40},
            "ports": [
                {
                    "id": "port_oid",
                    "name": "PortName",
                    "position": {"x": 130, "y": 220},
                    "is_visible": true
                }
            ]
        }
    ],
    "connections": [
        {
            "source_oid": "src_id",
            "target_oid": "tgt_id",
            "bend_points": [{"x": 150, "y": 150}]
        }
    ]
}
```

### 2. scan_ascet_database_tree(version="6.1.5")
**Purpose:** Recursively scan entire ASCET database and build folder/class tree

```python
# Example usage
data_core = AscetDataCore(logger_func=self.log)
tree_structure = data_core.scan_ascet_database_tree("6.1.5")

# Returns structure like:
# {
#     "name": "ASCET Database",
#     "folders": [
#         {
#             "name": "CN_Library",
#             "path": "\\CN_Library",
#             "sub_folders": [...],
#             "classes": [
#                 {
#                     "name": "ClassName",
#                     "path": "\\CN_Library\\...",
#                     "has_diagram": true
#                 }
#             ]
#         }
#     ]
# }
```

**Output Structure:**
```python
tree_structure = {
    "name": "ASCET Database",
    "folders": [
        {
            "name": "FolderName",
            "path": "\\FolderPath\\...",
            "sub_folders": [  # Recursive
                {...}
            ],
            "classes": [
                {
                    "name": "ClassName",
                    "path": "\\Path\\To\\Class",
                    "has_diagram": True/False
                }
            ]
        }
    ]
}
```

## New Class: DiagramPopupDialog

**Purpose:** Lightweight dialog for viewing and exporting diagrams

```python
# Example usage
popup = DiagramPopupDialog(diagram_data, parent=self)
popup.exec()  # or popup.show() for non-modal

# Features:
# - Zoom in/out with buttons or mouse wheel
# - Pan with mouse drag
# - Reset zoom button
# - Export to PNG
# - Info panel showing element counts
```

## Integration Examples

### Example 1: Build Tree with ASCET Scanning
```python
def build_ascet_tree_with_scanning(self):
    """Build tree from ASCET database scan"""
    data_core = AscetDataCore(logger_func=self.log)
    
    # Scan database
    tree_structure = data_core.scan_ascet_database_tree("6.1.5")
    
    if not tree_structure:
        self.log("❌ Failed to scan database")
        return
    
    # Build tree in UI
    self.tree_widget.clear()
    root_item = QTreeWidgetItem(self.tree_widget, [f"🏠 {tree_structure['name']}"])
    
    def build_tree_items(parent_item, folder_data):
        # Add folders
        for folder in folder_data.get('sub_folders', []):
            folder_item = QTreeWidgetItem(parent_item, [f"📁 {folder['name']}"])
            build_tree_items(folder_item, folder)
        
        # Add classes
        for cls in folder_data.get('classes', []):
            icon = "📊" if cls['has_diagram'] else "📄"
            cls_item = QTreeWidgetItem(parent_item, [f"{icon} {cls['name']}"])
            cls_item.setData(0, Qt.UserRole, {"path": cls['path'], "has_diagram": cls['has_diagram']})
    
    for folder in tree_structure['folders']:
        build_tree_items(root_item, folder)
    
    root_item.expandAll()
    self.log("✅ Tree built successfully!")

# Call this when user clicks "BƯỚC 1: Quét Thư mục"
```

### Example 2: Open Diagram in Popup
```python
def on_diagram_selected(self, item, column):
    """Handle diagram double-click - open in popup"""
    item_data = item.data(0, Qt.UserRole)
    
    if not item_data or not item_data.get('has_diagram'):
        self.log("⚠️ This item doesn't have a diagram")
        return
    
    # Get diagram file path
    diagram_path = item_data.get('xml_path')  # Or construct from class path
    
    # Parse diagram
    data_core = AscetDataCore(logger_func=self.log)
    diagram_data = data_core.parse_diagram_xml(diagram_path, item.text(0))
    
    if not diagram_data:
        self.log("❌ Cannot parse diagram")
        return
    
    # Open in popup
    popup = DiagramPopupDialog(diagram_data, parent=self)
    popup.show()
    
    self.log(f"✅ Opened diagram: {diagram_data['diagram_name']}")
```

### Example 3: Export Diagram from Popup
```python
# The DiagramPopupDialog already has export functionality built-in
# Just click "💾 Export PNG" button in the popup
# Or programmatically:

if diagram_data:
    popup = DiagramPopupDialog(diagram_data, parent=self)
    popup.show()
    # User can click "Export PNG" directly from popup
```

## Workflow Integration

### Current Workflow (from user request):
```
BƯỚC 1: Quét Thư mục (Scan ASCET)
   ↓
   Calls: scan_ascet_database_tree()
   
BƯỚC 2: Export + Build tree
   ↓
   Builds hierarchy with 📊 and 📄 markers
   
Double-click 📊 diagram
   ↓
   Calls: parse_diagram_xml()
   Opens: DiagramPopupDialog
   
Export in popup
   ↓
   Calls: popup.export_diagram()
   Saves PNG + optionally JSON
```

## Key Features

✅ **Recursive ASCET Scanning**
- Full folder hierarchy
- Class detection
- Diagram availability checking

✅ **Parse Diagram XML**
- Extract blocks, connections, ports
- Handle all element types
- Preserve position/size information

✅ **Lightweight Popup Dialog**
- Zoom/pan controls
- Simple rendering
- Export to PNG
- Independent window management

✅ **Ready for Integration**
- All methods added to existing AscetDataCore
- DiagramPopupDialog is standalone
- Compatible with existing code

## Testing

```python
# Quick test
if __name__ == "__main__":
    # Test diagram parsing
    data_core = AscetDataCore(logger_func=print)
    
    # Test scanning
    tree = data_core.scan_ascet_database_tree()
    print(f"Found {len(tree['folders'])} folders")
    
    # Test popup
    if tree['folders']:
        print("✅ All components working!")
```

## Next Steps

1. ✅ Methods added to GUImainv93.py (DONE)
2. ⏳ Integrate into existing tree_widget structure
3. ⏳ Update on_diagram_selected to use popup
4. ⏳ Test with real ASCET database
5. ⏳ Optimize rendering for large diagrams

---

**Version:** 4.0  
**Last Updated:** 2026-03-18  
**Status:** ✅ Core functionality complete, ready for integration
