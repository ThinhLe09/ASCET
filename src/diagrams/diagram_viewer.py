"""
Diagram Viewer Dialog - Display diagram visualization and connection logic
Shows diagram with 2 tabs: Visual diagram + Text-based connection logic
"""

import os
import xml.etree.ElementTree as ET
import math
from typing import Dict, List

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QGraphicsView, 
                               QGraphicsScene, QTextEdit, QPushButton, QLabel)
from PySide6.QtGui import QPen, QBrush, QColor, QPainter, QPainterPath, QPolygonF, QFont, QImage
from PySide6.QtCore import Qt, QPointF, QRectF


# =====================================================================
# DIAGRAM RENDERER (Vẽ sơ đồ)
# =====================================================================
class DiagramRenderer:
    def __init__(self, scene):
        self.scene = scene
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
        """Render diagram blocks and connections"""
        self.scene.clear()
        self.port_coords.clear()

        source_oids, target_oids = set(), set()
        for conn in data.get('connections', []):
            source_oids.add(conn['source_oid'])
            target_oids.add(conn['target_oid'])

        # STEP 1: Draw blocks and record port coordinates
        for block in data.get('blocks', []):
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
                v_px = [p['position']['x'] for p in block.get('ports', []) if p.get('is_visible', True)]
                v_py = [p['position']['y'] for p in block.get('ports', []) if p.get('is_visible', True)]
                
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

                for p in block.get('ports', []):
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
                
                if not block.get('ports'): 
                    self.port_coords[block['id']] = (bx, by)
                else:
                    for p in block.get('ports'): 
                        self.port_coords[p['id']] = (bx, by)

        # STEP 2: Draw connections
        for conn in data.get('connections', []):
            src, tgt = conn['source_oid'], conn['target_oid']
            if src not in self.port_coords or tgt not in self.port_coords: 
                continue
            
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
            
            # Draw arrow head
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


# =====================================================================
# CONNECTION LOGIC EXTRACTOR (Trích xuất logic dây nối)
# =====================================================================
class ConnectionLogicExtractor:
    @staticmethod
    def extract(diagram_data: Dict) -> str:
        """Extract and generate netlist-style connection logic"""
        lines = []
        lines.append("=" * 80)
        lines.append(f" 📑 CONNECTION LIST (NETLIST)")
        lines.append(f" Diagram: {diagram_data.get('diagram_name', 'Unknown')}")
        lines.append("=" * 80)
        lines.append("")

        # Build OID map: map from OID to {block_name, port_name}
        oid_map = {}
        for b in diagram_data.get('blocks', []):
            b_name, b_oid = b['name'], b['id']
            
            # Block itself as OID
            oid_map[b_oid] = {
                "block_name": b_name, 
                "port_name": "Self"
            }
            
            # Ports
            for p in b.get('ports', []):
                p_oid = p['id']
                p_name = p['name']
                oid_map[p_oid] = {
                    "block_name": b_name, 
                    "port_name": p_name
                }

        # Generate netlist
        connections = diagram_data.get('connections', [])
        
        for i, conn in enumerate(connections, 1):
            src_oid = conn['source_oid']
            tgt_oid = conn['target_oid']
            
            src_info = oid_map.get(src_oid)
            tgt_info = oid_map.get(tgt_oid)
            
            if not src_info or not tgt_info:
                continue
            
            src_block = src_info['block_name']
            src_port = src_info['port_name']
            
            tgt_block = tgt_info['block_name']
            tgt_port = tgt_info['port_name']
            
            # Format: 🔗 Wire 01: [Block1] (Port: Port1) ---> [Block2] (Port: Port2)
            if src_port == "Self":
                src_str = f"[{src_block}]"
            else:
                src_str = f"[{src_block}] (Port: {src_port})"
            
            if tgt_port == "Self":
                tgt_str = f"[{tgt_block}]"
            else:
                tgt_str = f"[{tgt_block}] (Port: {tgt_port})"
            
            line = f"🔗 Wire {i:02d}: {src_str:<50} ---> {tgt_str}"
            lines.append(line)
        
        lines.append("")
        lines.append("=" * 80)
        
        return "\n".join(lines)


# =====================================================================
# GRAPHICS VIEW (Zoom & Pan support)
# =====================================================================
class DiagramGraphicsView(QGraphicsView):
    def __init__(self, scene=None):
        super().__init__(scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setStyleSheet("border: 1px solid #ccc; background-color: white;")
        
    def wheelEvent(self, event):
        """Zoom with mouse wheel"""
        zoom_factor = 1.15
        if event.angleDelta().y() > 0:
            self.scale(zoom_factor, zoom_factor)
        else:
            self.scale(1 / zoom_factor, 1 / zoom_factor)


# =====================================================================
# MAIN DIALOG: DIAGRAM VIEWER
# =====================================================================
class DiagramViewerDialog(QDialog):
    """Dialog to display diagram with 2 tabs: Visual + Logic"""
    
    def __init__(self, diagram_data: Dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"📊 Diagram View: {diagram_data.get('diagram_name', 'Unknown')}")
        self.resize(1200, 800)
        
        self.diagram_data = diagram_data
        self.setup_ui()
        
    def setup_ui(self):
        """Setup UI with 2 tabs"""
        layout = QVBoxLayout(self)
        
        # Top label
        title_label = QLabel(f"📊 Diagram: {self.diagram_data.get('diagram_name', 'Unknown')}")
        title_label.setStyleSheet("font-weight: bold; font-size: 12px; padding: 5px;")
        layout.addWidget(title_label)
        
        # Create tabs
        self.tab_widget = QTabWidget()
        
        # TAB 1: Visual Diagram
        self.scene = QGraphicsScene()
        self.view = DiagramGraphicsView(self.scene)
        
        renderer = DiagramRenderer(self.scene)
        renderer.render(self.diagram_data)
        
        self.tab_widget.addTab(self.view, "📊 Visual Diagram")
        
        # TAB 2: Connection Logic
        self.logic_text = QTextEdit()
        self.logic_text.setReadOnly(True)
        self.logic_text.setFont(QFont("Consolas", 9))
        self.logic_text.setStyleSheet("background-color: #f5f5f5; color: #000;")
        
        logic_content = ConnectionLogicExtractor.extract(self.diagram_data)
        self.logic_text.setText(logic_content)
        
        self.tab_widget.addTab(self.logic_text, "📝 Connection Logic")
        
        layout.addWidget(self.tab_widget)
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
