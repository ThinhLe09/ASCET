import sys
import os
import shutil
import tempfile
import traceback
import win32com.client
import xml.etree.ElementTree as ET
import math
import json
import datetime

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QPushButton, QTreeWidget, QTreeWidgetItem, QComboBox, QTextEdit, 
                               QProgressBar, QSplitter, QGraphicsView, QGraphicsScene, QFileDialog)
from PySide6.QtGui import QPen, QBrush, QColor, QPainter, QPainterPath, QPolygonF, QFont, QImage
from PySide6.QtCore import Qt, QPointF, QRectF

# =====================================================================
# 1. CORE DATA & PARSING (Xử lý API, XML, File System)
# =====================================================================
class AscetDataCore:
    def __init__(self, logger_func):
        self.log = logger_func

    def _get_ascet_instance(self):
        """Ép kết nối vào app ASCET đang mở trên màn hình, thay vì tạo app ngầm"""
        try:
            return win32com.client.GetActiveObject("Ascet.Ascet.6.1.5")
        except:
            return win32com.client.Dispatch("Ascet.Ascet.6.1.5")

    def get_ascet_folders(self):
        self.log("Đang kết nối COM API...")
        original_cwd = os.getcwd()
        try:
            # ÉP PYTHON VỀ Ổ C ĐỂ KHÔNG BỊ NHIỄU NGỮ CẢNH (WORKING DIRECTORY)
            os.chdir(os.environ.get("SystemDrive", "C:") + "\\")
            
            ascet = self._get_ascet_instance()
            db = ascet.GetCurrentDataBase()
            self.log("Database Connect: THÀNH CÔNG (Đã khóa ngữ cảnh)!")
            
            try: folders = db.GetAllFolders()
            except: folders = db.GetAllAscetFolders()

            found_names = [f.GetName() if hasattr(f, 'GetName') else str(f) for f in folders]
            return sorted(found_names)
        except Exception as e:
            self.log(f"LỖI API QUÉT TỰ ĐỘNG:\n{str(e)}")
            return []
        finally:
            os.chdir(original_cwd)

    def export_folder_xml(self, folder_name, output_dir):
        original_cwd = os.getcwd()
        try:
            os.chdir(os.environ.get("SystemDrive", "C:") + "\\")
            ascet = self._get_ascet_instance()
            db = ascet.GetCurrentDataBase()
            
            try: ascet_obj = db.GetFolder(folder_name)
            except: ascet_obj = db.GetItemInFolder(folder_name, "\\")

            if not ascet_obj: raise ValueError(f"Không bắt được đối tượng '{folder_name}'.")

            # Cắt ngắn tên nếu nó quá dài để tránh lỗi 260 ký tự của Windows
            safe_name = ascet_obj.GetName()[:30] 
            xml_path = os.path.join(output_dir, f"{safe_name}_MasterDatabase.xml")
            xml_path = os.path.normpath(xml_path)
            
            ascet_obj.ExportXMLToFile(xml_path, True)
            return xml_path, ascet_obj.GetName()
        except Exception as e:
            self.log(f"LỖI KHI EXPORT:\n{str(e)}")
            return None, None
        finally:
            os.chdir(original_cwd)

    @staticmethod
    def get_diagram_version(specification_file_path):
        """Hàm tự động tra chéo sang file .main.amd và .scm.amd để lấy Version"""
        # Cắt đuôi chuẩn xác để tạo base path
        if specification_file_path.endswith('.specification.amd'):
            base_path = specification_file_path[:-18]
        elif specification_file_path.endswith('.dp.amd'):
            base_path = specification_file_path[:-7]
        elif specification_file_path.endswith('.main.amd'):
            base_path = specification_file_path[:-9]
        elif specification_file_path.endswith('.amd'):
            base_path = specification_file_path[:-4]
        else:
            return ""

        main_file_path = base_path + '.main.amd'
        scm_file_path = base_path + '.scm.amd'

        v_id = ""
        c_id = ""

        if os.path.exists(main_file_path):
            try:
                tree = ET.parse(main_file_path)
                root = tree.getroot()
                for el in root.iter():
                    if '}' in el.tag: el.tag = el.tag.split('}', 1)[1]
                config_mgmt = root.find('.//ConfigurationManagement')
                if config_mgmt is not None:
                    v_id = config_mgmt.attrib.get('versionID', '')
                    c_id = config_mgmt.attrib.get('configurationID', '')
            except: pass

        if not v_id and os.path.exists(scm_file_path):
            try:
                tree = ET.parse(scm_file_path)
                root = tree.getroot()
                for el in root.iter():
                    if '}' in el.tag: el.tag = el.tag.split('}', 1)[1]
                version_data = root.find('.//CurrentVersionData')
                if version_data is not None:
                    v_id = version_data.attrib.get('versionID', '')
            except: pass

        if v_id and c_id:
            return f" ({v_id}-{c_id})"
        elif v_id:
            prefix = "" if v_id.upper().startswith("V") else "V"
            return f" ({prefix}{v_id})"
        elif c_id:
            return f" ({c_id})"
        
        return ""
    def parse_diagram_xml(self, xml_file, diag_name):
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            for el in root.iter():
                if '}' in el.tag: el.tag = el.tag.split('}', 1)[1]
                
            data = {"diagram_name": diag_name.replace("📊 ", "").strip(), "source_xml_file": xml_file, "blocks": [], "connections": []}
            TARGET_TAGS = ['ComplexElement', 'SimpleElement', 'Literal', 'Operator', 'Junction', 'Connector', 'ConnectionPoint']
            
            main_spec = root.find('.//Specification[@name="Main"]')
            if main_spec is None:
                main_spec = root.find('.//Specification')
                
            if main_spec is None:
                return data 

            parsed_blocks = {}
            for elem in main_spec.iter():
                if elem.tag not in TARGET_TAGS: continue
                    
                b_oid = elem.attrib.get('graphicOID', '')
                pos = elem.find('./Position')
                size = elem.find('./Size') 
                
                if b_oid and pos is not None and b_oid != "-1":
                    bx, by = float(pos.attrib.get('x', 0)), float(pos.attrib.get('y', 0))
                    sw = float(size.attrib.get('x', 0)) if size is not None else None
                    sh = float(size.attrib.get('y', 0)) if size is not None else None
                    
                    b_type = elem.tag
                    if b_type == 'Literal': b_name = elem.attrib.get('value', '???')
                    elif b_type == 'Operator': b_name = elem.attrib.get('operator', elem.attrib.get('kind', elem.attrib.get('type', 'Op')))
                    elif b_type in ['Junction', 'Connector', 'ConnectionPoint']: b_name = ''
                    else: b_name = elem.attrib.get('elementName', elem.tag)
                    
                    block_data = {"id": b_oid, "name": b_name, "type": b_type, "position": {"x": bx, "y": by}, "size": {"w": sw, "h": sh}, "ports": []}
                    
                    interfaces = elem.find('.//Interfaces')
                    if interfaces is not None:
                        for port in interfaces.iter():
                            p_oid = port.attrib.get('graphicOID')
                            if not p_oid or p_oid == "-1": continue
                            
                            is_visible = port.attrib.get('visibility', 'true').lower() == 'true'
                            
                            p_pos = port.find('./Position')
                            px, py = (float(p_pos.attrib.get('x', 0)), float(p_pos.attrib.get('y', 0))) if p_pos is not None else (bx, by)
                            p_name = port.attrib.get('elementName', port.attrib.get('name', port.tag))
                            block_data["ports"].append({
                                "id": p_oid, "name": p_name, "tag": port.tag, 
                                "position": {"x": px, "y": py}, "is_visible": is_visible
                            })
                    
                    if b_oid not in parsed_blocks or len(block_data["ports"]) > len(parsed_blocks.get(b_oid, {}).get("ports", [])):
                        parsed_blocks[b_oid] = block_data
                            
            data["blocks"] = list(parsed_blocks.values())

            parsed_conns = set()
            for conn in main_spec.findall('.//Connection'):
                start_elem = conn.find('.//Start')
                end_elem = conn.find('.//End')
                if start_elem is not None and end_elem is not None:
                    src_oid = start_elem.attrib.get('graphicOID')
                    tgt_oid = end_elem.attrib.get('graphicOID')
                    if not src_oid or not tgt_oid: continue
                    bends = tuple((float(b.attrib.get('x',0)), float(b.attrib.get('y',0))) for b in conn.findall('.//BendPoint'))
                    c_key = (src_oid, tgt_oid, bends)
                    if c_key not in parsed_conns:
                        parsed_conns.add(c_key)
                        data["connections"].append({"source_oid": src_oid, "target_oid": tgt_oid, "bend_points": [{"x": pt[0], "y": pt[1]} for pt in bends]})
            return data
        except Exception as e:
            self.log(f"LỖI PARSE XML:\n{str(e)}")
            return None

# =====================================================================
# 2. RENDERER (Đại tu thuật toán Hình học & Z-Index)
# =====================================================================
class DiagramRenderer:
    def __init__(self, scene):
        self.scene = scene
        self.render_log = {}
        self.port_coords = {}
        
        self.pen_box = QPen(Qt.black, 1.5)
        self.pen_line = QPen(Qt.black, 1.5)
        self.pen_none = QPen(Qt.NoPen)
        self.brush_complex = QBrush(QColor('#f8f9fa'))
        self.brush_simple = QBrush(Qt.white)
        self.brush_literal = QBrush(QColor('#fffcdc')) 
        self.brush_operator = QBrush(QColor('#e8f4f8')) 
        self.brush_red = QBrush(QColor('#cc3333'))
        self.brush_black = QBrush(Qt.black)
        
        self.font_bold = QFont("Consolas", 9, QFont.Bold)
        self.font_normal = QFont("Consolas", 7) 
        self.font_op = QFont("Consolas", 12, QFont.Bold)

    def render(self, data):
        self.scene.clear()
        self.port_coords.clear()

        source_oids, target_oids = set(), set()
        for conn in data['connections']:
            source_oids.add(conn['source_oid'])
            target_oids.add(conn['target_oid'])

        self.render_log = {
            "diagram_name": data.get("diagram_name", "Unknown"),
            "blocks_drawn": [], "connections_drawn": [], "port_coordinates": {}
        }

        # BƯỚC 1: VẼ CÁC KHỐI & CHỐT TỌA ĐỘ PORT
        for block in data['blocks']:
            b_type, b_name, bx, by = block['type'], block['name'], block['position']['x'], block['position']['y']
            
            if b_type == 'Literal':
                t_item = self.scene.addText(str(b_name), self.font_normal)
                tw, th = t_item.boundingRect().width(), t_item.boundingRect().height()
                box = self.scene.addRect(bx - tw - 6, by - th/2, tw + 6, th, self.pen_line, self.brush_literal)
                t_item.setPos(bx - tw - 3, by - th/2)
                box.setZValue(0); t_item.setZValue(2)
                self.port_coords[block['id']] = (bx, by)

            elif b_type == 'Operator':
                r = 12
                ellipse = self.scene.addEllipse(bx - r, by - r, r*2, r*2, self.pen_box, self.brush_operator)
                t_item = self.scene.addText(b_name, self.font_op)
                t_item.setPos(bx - t_item.boundingRect().width()/2, by - t_item.boundingRect().height()/2 - 1)
                ellipse.setZValue(0); t_item.setZValue(2)
                self.port_coords[block['id']] = (bx, by)
                
            elif b_type in ['Junction', 'Connector', 'ConnectionPoint']:
                dot = self.scene.addEllipse(bx - 3, by - 3, 6, 6, self.pen_none, self.brush_black)
                dot.setZValue(3) 
                self.port_coords[block['id']] = (bx, by)

            elif b_type == 'ComplexElement':
                v_px = [p['position']['x'] for p in block['ports'] if p.get('is_visible', True)]
                v_py = [p['position']['y'] for p in block['ports'] if p.get('is_visible', True)]
                
                if v_px and v_py:
                    min_x, max_x = min(v_px), max(v_px)
                    min_y, max_y = min(v_py), max(v_py)
                    
                    if min_x == max_x:
                        min_x -= 30; max_x += 30 
                    
                    w, h = max_x - min_x, max_y - min_y + 40
                    rect_y = min_y - 20
                else:
                    min_x, rect_y, w, h = bx, by, 100, 60

                rect = self.scene.addRect(min_x, rect_y, w, h, self.pen_box, self.brush_complex)
                rect.setZValue(-2) 
                
                t_item = self.scene.addText(b_name, self.font_bold)
                t_item.setPos(min_x + w/2 - t_item.boundingRect().width()/2, rect_y + 2)
                t_item.setZValue(2)

                for p in block['ports']:
                    if not p.get('is_visible', True): continue 
                    pid, px, py, pname = p['id'], p['position']['x'], p['position']['y'], p['name']
                    self.port_coords[pid] = (px, py)
                    
                    p_box = self.scene.addRect(px - 3, py - 3, 6, 6, self.pen_box, self.brush_red)
                    p_item = self.scene.addText(pname, self.font_normal)
                    p_box.setZValue(1); p_item.setZValue(2)
                    
                    if px <= min_x + w/2: 
                        p_item.setPos(px + 4, py - p_item.boundingRect().height()/2)
                    else: 
                        p_item.setPos(px - p_item.boundingRect().width() - 4, py - p_item.boundingRect().height()/2)

            elif b_type == 'SimpleElement':
                t_item = self.scene.addText(b_name, self.font_normal)
                tw, th = t_item.boundingRect().width(), t_item.boundingRect().height()
                
                has_input_connection = any(p['id'] in target_oids for p in block.get('ports', []))
                has_output_connection = any(p['id'] in source_oids for p in block.get('ports', []))
                
                is_target = has_input_connection and not has_output_connection
                
                if is_target:
                    box = self.scene.addRect(bx, by - th/2, tw + 6, th, self.pen_line, self.brush_simple)
                    t_item.setPos(bx + 3, by - th/2)
                else:
                    box = self.scene.addRect(bx - tw - 6, by - th/2, tw + 6, th, self.pen_line, self.brush_simple)
                    t_item.setPos(bx - tw - 3, by - th/2)
                
                box.setZValue(0); t_item.setZValue(2)
                
                if not block['ports']: self.port_coords[block['id']] = (bx, by)
                else:
                    for p in block['ports']: self.port_coords[p['id']] = (bx, by)

        # BƯỚC 2: VẼ DÂY
        for idx, conn in enumerate(data['connections']):
            src, tgt = conn['source_oid'], conn['target_oid']
            if src not in self.port_coords or tgt not in self.port_coords: continue
            
            sx, sy = self.port_coords[src]
            ex, ey = self.port_coords[tgt]
            
            path_points = [(sx, sy)]
            for bend in conn.get('bend_points', []):
                path_points.append((bend['x'], bend['y']))
            path_points.append((ex, ey))

            path = QPainterPath()
            path.moveTo(path_points[0][0], path_points[0][1])
            for pt in path_points[1:]: 
                path.lineTo(pt[0], pt[1])
            
            path_item = self.scene.addPath(path, self.pen_line)
            path_item.setZValue(-1) 
            
            if len(path_points) >= 2:
                for i in range(len(path_points)-1, 0, -1):
                    px1, py1 = path_points[i-1]
                    px2, py2 = path_points[i]
                    dist = math.hypot(px2 - px1, py2 - py1)
                    if dist > 1e-3: 
                        dx, dy = (px2 - px1) / dist, (py2 - py1) / dist
                        nx, ny = -dy, dx
                        p1 = QPointF(px2, py2)
                        p2 = QPointF(px2 - 8*dx + 4*nx, py2 - 8*dy + 4*ny)
                        p3 = QPointF(px2 - 8*dx - 4*nx, py2 - 8*dy - 4*ny)
                        arrow = self.scene.addPolygon(QPolygonF([p1, p2, p3]), self.pen_none, self.brush_black)
                        arrow.setZValue(2)
                        break
                        
        self.scene.setSceneRect(self.scene.itemsBoundingRect().adjusted(-50, -50, 50, 50))
        return self.render_log

# =====================================================================
# 3. EXPORTER (Xuất Ảnh, JSON, và Báo cáo XML)
# =====================================================================
class DiagramExporter:
    @staticmethod
    def export(parent_widget, scene, diagram_data, render_log):
        default_name = f"{diagram_data['diagram_name']}"
        file_path, _ = QFileDialog.getSaveFileName(parent_widget, "Lưu Ảnh, JSON và Báo cáo Diagram", default_name, "PNG Images (*.png)")
        
        if not file_path: return False, "Đã hủy lưu file."
            
        try:
            base_path = file_path.rsplit('.', 1)[0]
            
            # 1. Lưu Ảnh
            rect = scene.itemsBoundingRect().adjusted(-50, -50, 50, 50)
            image = QImage(rect.size().toSize(), QImage.Format_ARGB32)
            image.fill(Qt.white)
            painter = QPainter(image)
            painter.setRenderHint(QPainter.Antialiasing)
            scene.render(painter, target=QRectF(image.rect()), source=rect)
            painter.end()
            image.save(file_path)
            
            # 2. Lưu JSON
            with open(f"{base_path}_attributes.json", 'w', encoding='utf-8') as f:
                json.dump(diagram_data, f, indent=4, ensure_ascii=False)
                
            # 3. Lưu Txt
            txt_report = DiagramExporter.generate_step_by_step_txt(diagram_data)
            txt_path = f"{base_path}_step_by_step_report.txt"
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(txt_report)
                
            return True, f"✅ Thành công!\n🖼️ Ảnh: {file_path}\n📝 Báo cáo Dễ Hiểu: {txt_path}"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def generate_step_by_step_txt(data):
        lines = []
        lines.append("=========================================================================================")
        lines.append(f" 📑 BÁO CÁO GIẢI MÃ LIÊN KẾT: {data['diagram_name']}")
        lines.append("=========================================================================================\n")
        
        lines.append("💡 BÍ MẬT CỦA ASCET XML (ĐỌC ĐỂ HIỂU TẠI SAO BẠN TÌM KHÔNG RA):")
        lines.append("   Dây nối <Connection> KHÔNG BAO GIỜ nối trực tiếp 2 Khối (Block) với nhau.")
        lines.append("   Dây nối chỉ nối 2 cái CỔNG (Port). Các cổng này nằm giấu bên trong Khối.")
        lines.append("-" * 89 + "\n")

        oid_map = {}
        for b in data['blocks']:
            b_name, b_type, b_oid = b['name'], b['type'], b['id']
            oid_map[b_oid] = {"bname": b_name, "btype": b_type, "pname": "Bản thân Khối", "ptag": b_type, "parent_oid": b_oid}
            for p in b.get('ports', []):
                oid_map[p['id']] = {"bname": b_name, "btype": b_type, "pname": p['name'], "ptag": p['tag'], "parent_oid": b_oid}

        block_inputs = {b['name']: [] for b in data['blocks']}

        for conn in data['connections']:
            src_oid, tgt_oid = conn['source_oid'], conn['target_oid']
            src_info, tgt_info = oid_map.get(src_oid), oid_map.get(tgt_oid)
            
            if src_info and tgt_info:
                block_inputs[tgt_info['bname']].append({
                    "from_block": src_info['bname'], "from_block_oid": src_info['parent_oid'],
                    "from_port": src_info['pname'], "src_oid": src_oid, "src_tag": src_info['ptag'],
                    "to_port": tgt_info['pname'], "tgt_oid": tgt_oid, "tgt_tag": tgt_info['ptag'],
                })

        lines.append("--- PHÂN TÍCH LUỒNG DỮ LIỆU ĐI VÀO TỪNG KHỐI ---\n")
        
        for b in data['blocks']:
            bname, btype, b_oid = b['name'], b['type'], b['id']
            ins = block_inputs.get(bname, [])
            
            if not ins: continue 
                
            lines.append(f"📦 KHỐI NHẬN: [{btype}] {bname}")
            lines.append(f"   (Để tìm khối này trong XML, gõ tìm: graphicOID=\"{b_oid}\")")
            lines.append("   Các dữ liệu truyền vào khối này:")
            
            for i, inp in enumerate(ins):
                lines.append(f"      {i+1}. Từ khối [{inp['from_block']}]  ------>  Vào cổng [{inp['to_port']}]")
                lines.append(f"         📝 Cách tra cứu đoạn nối này trong file XML:")
                lines.append(f"            Bước 1: Tìm đoạn dây nối bằng cách search: <Start graphicOID=\"{inp['src_oid']}\"/> và <End graphicOID=\"{inp['tgt_oid']}\"/>")
                lines.append(f"            Bước 2: Search OID Đích (graphicOID=\"{inp['tgt_oid']}\"). Thẻ <{inp['tgt_tag']}> nằm lọt thỏm bên trong Khối {bname} (mã {b_oid}).")
                lines.append(f"            Bước 3: Search OID Nguồn (graphicOID=\"{inp['src_oid']}\"). Thẻ <{inp['src_tag']}> nằm lọt thỏm bên trong Khối {inp['from_block']} (mã {inp['from_block_oid']}).\n")
            lines.append("-" * 89)

        lines.append("\n================================ KẾT THÚC BÁO CÁO ================================")
        return "\n".join(lines)

# =====================================================================
# 4. UI COMPONENTS & MAIN WINDOW (Bộ điều phối)
# =====================================================================
class DiagramView(QGraphicsView):
    def __init__(self, scene=None):
        super().__init__(scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setStyleSheet("border: none; background-color: white;")
        
    def wheelEvent(self, event):
        zoom_factor = 1.15
        if event.angleDelta().y() > 0: self.scale(zoom_factor, zoom_factor)
        else: self.scale(1 / zoom_factor, 1 / zoom_factor)

class AscetDiagramApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ASCET Diagram - V6 Ultimate (Final Version)")
        self.resize(1400, 900)
        
        self.diagram_files = {} 
        self.current_diagram_data = None 
        self.current_render_log = None
        
        self.data_core = AscetDataCore(logger_func=self.log)
        self.setup_ui()
        self.renderer = DiagramRenderer(self.scene)

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.btn_auto_detect = QPushButton(" BƯỚC 1: Quét Thư mục")
        self.btn_auto_detect.setStyleSheet("background-color: #8e44ad; color: white; font-weight: bold; padding: 12px;")
        self.btn_auto_detect.clicked.connect(self.step1_auto_detect_folders)
        left_layout.addWidget(self.btn_auto_detect)

        self.path_combo = QComboBox()
        self.path_combo.setStyleSheet("padding: 5px; font-weight: bold;")
        left_layout.addWidget(self.path_combo)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0) 
        self.progress_bar.setVisible(False) 
        left_layout.addWidget(self.progress_bar)

        self.btn_step2 = QPushButton(" BƯỚC 2: Kéo Data & Dựng Cây")
        self.btn_step2.setStyleSheet("background-color: #2b5797; color: white; font-weight: bold; padding: 12px;")
        self.btn_step2.setEnabled(False) 
        self.btn_step2.clicked.connect(self.step2_extract_data)
        left_layout.addWidget(self.btn_step2)

        self.btn_export = QPushButton(" BƯỚC 3: Xuất Ảnh & JSON")
        self.btn_export.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; padding: 12px;")
        self.btn_export.setEnabled(False)
        self.btn_export.clicked.connect(self.step3_export_diagram)
        left_layout.addWidget(self.btn_export)

        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setStyleSheet("background-color: #0d1117; color: #00ff00; font-family: Consolas; font-size: 12px;")
        left_layout.addWidget(self.log_console, stretch=2)

        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabel("Sơ đồ khả dụng")
        self.tree_widget.itemDoubleClicked.connect(self.on_diagram_selected)
        left_layout.addWidget(self.tree_widget, stretch=3)

        self.scene = QGraphicsScene()
        self.view = DiagramView(self.scene)
        
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(self.view)
        splitter.setSizes([400, 1000]) 
        main_layout.addWidget(splitter)

    def log(self, text):
        self.log_console.append(text)
        scrollbar = self.log_console.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        QApplication.processEvents()

    def set_loading(self, is_loading):
        self.progress_bar.setVisible(is_loading)
        QApplication.processEvents()

    def step1_auto_detect_folders(self):
        self.set_loading(True)
        self.path_combo.clear()
        folders = self.data_core.get_ascet_folders()
        if folders:
            self.path_combo.addItems(folders)
            for i, name in enumerate(folders):
                if "cn_library" in name.lower():
                    self.path_combo.setCurrentIndex(i)
                    break
            self.btn_step2.setEnabled(True)
        self.set_loading(False)

    def step2_extract_data(self):
        selected_folder = self.path_combo.currentText()
        if not selected_folder: return

        self.set_loading(True)
        self.btn_auto_detect.setEnabled(False)
        self.btn_step2.setEnabled(False)
        
        # --- SỬ DỤNG THƯ MỤC TEMP ĐỂ NÉ HOÀN TOÀN GIỚI HẠN KÝ TỰ ---
        temp_base = tempfile.gettempdir()
        output_dir = os.path.join(temp_base, "ASCET_Auto_Exports")
        
        # TỰ ĐỘNG DỌN RÁC Cache cũ
        if os.path.exists(output_dir):
            try: shutil.rmtree(output_dir)
            except Exception as e: self.log(f"⚠️ Lỗi khi dọn dẹp cache cũ: {str(e)}")
                
        os.makedirs(output_dir, exist_ok=True)

        self.log(f"\n[BƯỚC 2] Bắt đầu kéo data: {selected_folder}...")
        self.log(f"📍 Nơi lưu file tạm xử lý ngầm: {output_dir}")
        
        xml_path, folder_real_name = self.data_core.export_folder_xml(selected_folder, output_dir)
        
        if xml_path:
            self.log("✅ Export XML thành công. Bắt đầu dựng cây thư mục...")
            self.build_tree(xml_path, output_dir, folder_real_name)
        else:
            self.log("❌ Lỗi: Quá trình Export từ ASCET thất bại. Hãy kiểm tra lại phần mềm ASCET.")
            
        self.set_loading(False)
        self.btn_auto_detect.setEnabled(True)
        self.btn_step2.setEnabled(True)
    def build_tree(self, xml_path, output_dir, root_name):
        self.diagram_files.clear()
        self.tree_widget.clear()
        
        tree_nodes = {os.path.abspath(output_dir): QTreeWidgetItem(self.tree_widget, [root_name])}

        for root_dir, dirs, files in os.walk(xml_path):
            root_dir_abs = os.path.abspath(root_dir)
            
            if root_dir_abs not in tree_nodes:
                parent_dir = os.path.abspath(os.path.dirname(root_dir_abs))
                parent_node = tree_nodes.get(parent_dir, tree_nodes[os.path.abspath(output_dir)])
                dir_item = QTreeWidgetItem([os.path.basename(root_dir_abs)])
                parent_node.addChild(dir_item)
                tree_nodes[root_dir_abs] = dir_item
                
            current_node = tree_nodes[root_dir_abs]

            # Dùng set để KHỬ TRÙNG LẶP (Vì 1 component sinh ra rất nhiều file .amd)
            processed_components = set()

            for file_name in files:
                if not file_name.endswith('.amd'):
                    continue
                    
                # Chỉ xử lý khi gặp các file "chính" đại diện cho Component
                if file_name.endswith('.specification.amd') or file_name.endswith('.main.amd') or file_name.endswith('.dp.amd'):
                    
                    # Bỏ qua các file cấu hình phụ (.data, .implementation, .project...) để tránh rác cây
                    if '.project.' in file_name or '.data.' in file_name or '.implementation.' in file_name or '.scm.' in file_name:
                        continue
                        
                    clean_name = file_name.replace('.specification.amd', '').replace('.main.amd', '').replace('.dp.amd', '')
                    
                    # Nếu Component này đã được đưa lên cây rồi thì bỏ qua
                    if clean_name in processed_components:
                        continue
                    processed_components.add(clean_name)
                    
                    # Xác định file nào chứa nội dung vẽ đồ họa
                    spec_file = os.path.join(root_dir_abs, f"{clean_name}.specification.amd")
                    dp_file = os.path.join(root_dir_abs, f"{clean_name}.dp.amd")
                    
                    has_diagram = False
                    fpath_to_parse = os.path.join(root_dir_abs, file_name) # File mặc định để parse
                    
                    # Kiểm tra xem ruột file có chứa sơ đồ không
                    if os.path.exists(spec_file):
                        content = open(spec_file, 'r', encoding='utf-8', errors='ignore').read()
                        if '<SimpleElement' in content or '<Connection' in content:
                            has_diagram = True
                        fpath_to_parse = spec_file
                    elif os.path.exists(dp_file):
                        content = open(dp_file, 'r', encoding='utf-8', errors='ignore').read()
                        if '<SimpleElement' in content or '<Connection' in content:
                            has_diagram = True
                        fpath_to_parse = dp_file

                    # Gọi hàm móc Version từ .main.amd
                    version_str = AscetDataCore.get_diagram_version(fpath_to_parse)
                    
                    # Phân loại Icon
                    if has_diagram:
                        display_name = f" 📊 {clean_name}{version_str}"
                    else:
                        display_name = f" 📦 {clean_name}{version_str}"
                        
                    diagram_item = QTreeWidgetItem([display_name])
                    current_node.addChild(diagram_item)
                    
                    # Lưu lại file để khi click đúp sẽ gọi hàm parse đồ họa
                    self.diagram_files[display_name] = fpath_to_parse
        
        self.tree_widget.expandAll()
        self.log("Dựng cây hoàn tất! Hãy Click đúp vào một sơ đồ để vẽ.")
    def on_diagram_selected(self, item, column):
        diag_name = item.text(column)
        if diag_name not in self.diagram_files: return
            
        self.log(f"\n[+] Đang xử lý vẽ: {diag_name}...")
        self.set_loading(True)
        
        xml_file = self.diagram_files[diag_name]
        data = self.data_core.parse_diagram_xml(xml_file, diag_name)
        
        if data:
            self.current_diagram_data = data
            self.current_render_log = self.renderer.render(data)
            self.view.resetTransform()
            self.log("Vẽ hoàn tất! Bạn có thể xuất kết quả.")
            self.btn_export.setEnabled(True)
        else:
            self.log("Lỗi: Không parse được dữ liệu để vẽ.")
            
        self.set_loading(False)

    def step3_export_diagram(self):
        if not self.current_diagram_data: return
        success, msg = DiagramExporter.export(self, self.scene, self.current_diagram_data, self.current_render_log)
        self.log(msg)

if __name__ == "__main__":
    app = QApplication.instance() or QApplication(sys.argv)
    window = AscetDiagramApp()
    window.show()
    app.exec()