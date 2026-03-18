import xml.etree.ElementTree as ET
import os

def extract_connections(xml_file_path, output_txt_path):
    print(f"Đang phân tích file: {xml_file_path}...")
    if not os.path.exists(xml_file_path):
        print(f"❌ Không tìm thấy file {xml_file_path}!")
        return

    try:
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
    except Exception as e:
        print(f"❌ Lỗi đọc file XML: {e}")
        return

    # 1. Xóa các namespace để dễ parse
    for el in root.iter():
        if '}' in el.tag:
            el.tag = el.tag.split('}', 1)[1]

    oid_map = {}

    # ==============================================================
    # BƯỚC 1: CÀN QUÉT KHU VỰC <Layout> (BẮT CÁC CỔNG NGOẠI VI)
    # ==============================================================
    layout_elem = root.find('./Layout')
    if layout_elem is not None:
        # Càn quét toàn bộ mọi ngóc ngách trong Layout, không chừa một thẻ nào
        for node in layout_elem.iter():
            oid = node.attrib.get('graphicOID')
            if oid and oid != "-1":
                # Tìm tên của thẻ đó (ưu tiên name -> elementName -> methodName -> tên Tag)
                name = node.attrib.get('name', node.attrib.get('elementName', node.attrib.get('methodName', node.tag)))
                oid_map[oid] = {
                    "block_name": "[CỔNG_NGOÀI_CÙNG_SƠ_ĐỒ]", 
                    "port_name": name
                }

    # ==============================================================
    # BƯỚC 2: CÀN QUÉT KHU VỰC SƠ ĐỒ <Specification name="Main">
    # ==============================================================
    main_spec = root.find('.//Specification[@name="Main"]')
    if main_spec is None:
        main_spec = root.find('.//Specification')

    if main_spec is None:
        print("❌ Không tìm thấy sơ đồ nào trong file!")
        return

    # Duyệt qua tất cả các <DiagramElement> (đây là cái hộp chứa mọi Khối)
    for diagram_element in main_spec.findall('.//DiagramElement'):
        for block in diagram_element:
            # Bỏ qua Dây nối và Chú thích
            if block.tag in ['Connection', 'Comment', 'Note']:
                continue
                
            # Xác định TÊN ĐẠI DIỆN của Khối này
            b_type = block.tag
            if b_type == 'Literal': 
                b_name = block.attrib.get('value', 'Hằng_Số')
            elif b_type == 'Operator': 
                b_name = block.attrib.get('operator', block.attrib.get('kind', block.attrib.get('type', 'Toán_Tử')))
            elif b_type in ['Junction', 'Connector', 'ConnectionPoint']: 
                b_name = f"Điểm_Nối_{block.attrib.get('graphicOID', 'N/A')}"
            else: 
                b_name = block.attrib.get('elementName', block.attrib.get('name', block.attrib.get('methodName', block.tag)))
            
            # CÀN QUÉT MỌI THẺ CON/CHÁU/CHẮT BÊN TRONG KHỐI NÀY
            for node in block.iter():
                oid = node.attrib.get('graphicOID')
                # Hễ cứ có OID hợp lệ là tóm gọn
                if oid and oid != "-1":
                    p_name = node.attrib.get('elementName', node.attrib.get('name', node.attrib.get('methodName', node.tag)))
                    
                    if node == block:
                        # Nếu chính là cái vỏ ngoài cùng
                        oid_map[oid] = {"block_name": b_name, "port_name": "Bản thân khối"}
                    else:
                        # Nếu là một cổng, hàm, biến... nằm bên trong bụng Khối
                        oid_map[oid] = {"block_name": b_name, "port_name": p_name}

    # ==============================================================
    # BƯỚC 3: QUÉT DÂY NỐI (CONNECTIONS) - KÈM KHỬ TRÙNG LẶP
    # ==============================================================
    parsed_conns = set()
    connections = []
    for conn in main_spec.findall('.//Connection'):
        start_elem = conn.find('.//Start')
        end_elem = conn.find('.//End')
        if start_elem is not None and end_elem is not None:
            src_oid = start_elem.attrib.get('graphicOID')
            tgt_oid = end_elem.attrib.get('graphicOID')
            if not src_oid or not tgt_oid: 
                continue
            
            bends = tuple((float(b.attrib.get('x',0)), float(b.attrib.get('y',0))) for b in conn.findall('.//BendPoint'))
            c_key = (src_oid, tgt_oid, bends)
            
            if c_key not in parsed_conns:
                parsed_conns.add(c_key)
                connections.append({"source_oid": src_oid, "target_oid": tgt_oid})

    # ==============================================================
    # BƯỚC 4: XUẤT RA FILE TEXT
    # ==============================================================
    with open(output_txt_path, 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write(f" 📑 DANH SÁCH LIÊN KẾT TÍN HIỆU (NETLIST TỐI THƯỢNG)\n")
        f.write(f" Nguồn: {xml_file_path}\n")
        f.write("="*80 + "\n\n")
            
        for i, c in enumerate(connections, 1):
            src_oid = c['source_oid']
            tgt_oid = c['target_oid']
            
            src_info = oid_map.get(src_oid, {"block_name": f"Lỗi/Ẩn (OID {src_oid})", "port_name": "?"})
            tgt_info = oid_map.get(tgt_oid, {"block_name": f"Lỗi/Ẩn (OID {tgt_oid})", "port_name": "?"})
            
            src_str = f"[{src_info['block_name']}]" + (f" (Cổng: {src_info['port_name']})" if "Bản thân khối" not in src_info['port_name'] else "")
            tgt_str = f"[{tgt_info['block_name']}]" + (f" (Cổng: {tgt_info['port_name']})" if "Bản thân khối" not in tgt_info['port_name'] else "")
            
            f.write(f"🔗 Dây {i:02d}: {src_str:<50} ---> {tgt_str}\n")
            
    print(f"✅ HOÀN TẤT! Đã tìm thấy {len(connections)} đường dây. Xóa sổ hoàn toàn Lỗi/Ẩn OID!")

if __name__ == '__main__':
    INPUT_XML = "HAZ_Core.specification.amd" 
    INPUT_XML = r"C:\My code\Copilot\DiagramAPI\ASCET_Auto_Exports\PlatformLibrary_MasterDatabase.xml\PlatformLibrary\Package\HAZ_HazardWarning\Public\HAZ_HazardWarning20ms.specification.amd" 

    OUTPUT_TXT = "Ket_Qua_HAZ_Core_3.txt"
    extract_connections(INPUT_XML, OUTPUT_TXT)

# if __name__ == '__main__':
#     # Tên file gốc của cậu
#     INPUT_XML = r"C:\My code\Copilot\DiagramAPI\ASCET_Auto_Exports\PlatformLibrary_MasterDatabase.xml\PlatformLibrary\Package\HAZ_HazardWarning\Private\HAZ_Core.specification.amd" 
#     OUTPUT_TXT = "Ket_Qua_HAZ_core.txt"
#     extract_connections(INPUT_XML, OUTPUT_TXT)