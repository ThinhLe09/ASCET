import sys
import os
import shutil
import tempfile
import win32com.client
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QPushButton, QTreeWidget, QTreeWidgetItem, QComboBox, QMessageBox)

class AscetTreeApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Trích xuất Cây Thư Mục ASCET")
        self.resize(500, 700)
        self.diagram_files = {}

        # GIAO DIỆN
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self.btn_get_db = QPushButton("1. Kết nối ASCET & Quét Database")
        self.btn_get_db.setStyleSheet("background-color: #8e44ad; color: white; padding: 10px; font-weight: bold;")
        self.btn_get_db.clicked.connect(self.get_db_folders)
        layout.addWidget(self.btn_get_db)

        self.cb_folders = QComboBox()
        layout.addWidget(self.cb_folders)

        self.btn_build_tree = QPushButton("2. Kéo Data & Dựng Cây 📊")
        self.btn_build_tree.setStyleSheet("background-color: #2b5797; color: white; padding: 10px; font-weight: bold;")
        self.btn_build_tree.clicked.connect(self.extract_and_build_tree)
        layout.addWidget(self.btn_build_tree)

        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabel("Cấu trúc thư mục & Sơ đồ")
        layout.addWidget(self.tree_widget)

    # LOGIC 1: KẾT NỐI COM API ĐỂ LẤY FOLDER TRONG ASCET
    def get_ascet_instance(self):
        try:
            return win32com.client.GetActiveObject("Ascet.Ascet.6.1.5")
        except:
            return win32com.client.Dispatch("Ascet.Ascet.6.1.5")

    def get_db_folders(self):
        self.cb_folders.clear()
        try:
            ascet = self.get_ascet_instance()
            db = ascet.GetCurrentDataBase()
            
            try: folders = db.GetAllFolders()
            except: folders = db.GetAllAscetFolders()

            found_names = sorted([f.GetName() if hasattr(f, 'GetName') else str(f) for f in folders])
            self.cb_folders.addItems(found_names)
            QMessageBox.information(self, "Thành công", f"Đã quét được {len(found_names)} thư mục từ Database đang mở!")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi kết nối", f"Không thể lấy data từ ASCET:\n{str(e)}")

    # LOGIC 2: EXPORT FOLDER VÀ ĐỔ VÀO TREE
    def extract_and_build_tree(self):
        folder_name = self.cb_folders.currentText()
        if not folder_name: return

        # Tạo thư mục tạm để hứng file export
        temp_base = tempfile.gettempdir()
        output_dir = os.path.join(temp_base, "ASCET_Auto_Exports")
        
        # Dọn dẹp cache cũ nếu có
        if os.path.exists(output_dir):
            try: shutil.rmtree(output_dir)
            except: pass
        os.makedirs(output_dir, exist_ok=True)

        try:
            # Ép ASCET xuất XML của folder đang chọn ra máy
            ascet = self.get_ascet_instance()
            db = ascet.GetCurrentDataBase()
            try: ascet_obj = db.GetFolder(folder_name)
            except: ascet_obj = db.GetItemInFolder(folder_name, "\\")

            if not ascet_obj: return

            safe_name = ascet_obj.GetName()[:30]
            xml_path = os.path.normpath(os.path.join(output_dir, f"{safe_name}_MasterDatabase.xml"))
            
            ascet_obj.ExportXMLToFile(xml_path, True)

            # Bắt đầu duyệt file vừa export để vẽ lên cây
            self.build_tree(xml_path, output_dir, ascet_obj.GetName())

        except Exception as e:
            QMessageBox.critical(self, "Lỗi Export", f"Lỗi khi kéo data:\n{str(e)}")

    # LOGIC 3: VẼ CÂY (Giống hệt hàm cũ nhưng giờ đã có file thật)
    def build_tree(self, xml_path, output_dir, root_name):
        self.diagram_files.clear()
        self.tree_widget.clear()
        tree_nodes = {output_dir: QTreeWidgetItem(self.tree_widget, [root_name])}

        for root_dir, _, files in os.walk(xml_path):
            if os.path.relpath(root_dir, xml_path) != ".":
                parent_dir = os.path.dirname(root_dir)
                parent_node = tree_nodes.get(parent_dir, tree_nodes[output_dir])
                tree_nodes[root_dir] = QTreeWidgetItem(parent_node, [os.path.basename(root_dir)])

            for file_name in files:
                if file_name.endswith('.amd'):
                    fpath = os.path.join(root_dir, file_name)
                    try:
                        content = open(fpath, 'r', encoding='utf-8', errors='ignore').read()
                        # Lọc ra các file đúng chuẩn sơ đồ
                        if '<SimpleElement' in content or '<Connection' in content:
                            clean_name = file_name.replace('.specification.amd', '').replace('.dp.amd', '').replace('.amd', '')
                            node_name = f" 📊 {clean_name}"
                            QTreeWidgetItem(tree_nodes[root_dir], [node_name])
                            self.diagram_files[node_name] = fpath
                    except: pass
                    
        self.tree_widget.expandAll()

if __name__ == "__main__":
    app = QApplication.instance() or QApplication(sys.argv)
    window = AscetTreeApp()
    window.show()
    app.exec()