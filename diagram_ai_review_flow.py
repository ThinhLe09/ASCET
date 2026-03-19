#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diagram AI Review Flow
======================

Dedicated review flow for diagram queue items (.amd).
- Parse diagram connections into netlist text
- Send netlist text to AI for review
- Return result in the same shape used by class review pipeline
"""

import os
import json
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

from model_config import create_model_config
from response_handler import create_response_handler
from ai_error_arbitrator import extract_ai_errors


def is_diagram_item(class_path: Optional[str]) -> bool:
    """Check whether queue item is a diagram path."""
    if not class_path:
        return False
    normalized = str(class_path).strip().lower()
    return normalized.endswith(".amd") or ".specification.amd" in normalized


class DiagramNetlistExtractor:
    """Extract connection netlist text from ASCET .amd XML."""

    @staticmethod
    def _strip_namespaces(root: ET.Element) -> None:
        for el in root.iter():
            if '}' in el.tag:
                el.tag = el.tag.split('}', 1)[1]

    @staticmethod
    def extract_connections(xml_file_path: str) -> Tuple[List[Dict[str, str]], Dict[str, Dict[str, str]]]:
        if not os.path.exists(xml_file_path):
            raise FileNotFoundError(f"Diagram file not found: {xml_file_path}")

        tree = ET.parse(xml_file_path)
        root = tree.getroot()
        DiagramNetlistExtractor._strip_namespaces(root)

        oid_map: Dict[str, Dict[str, str]] = {}

        # Step 1: scan Layout for global/external ports
        layout_elem = root.find('./Layout')
        if layout_elem is not None:
            for node in layout_elem.iter():
                oid = node.attrib.get('graphicOID')
                if oid and oid != "-1":
                    name = node.attrib.get('name', node.attrib.get('elementName', node.attrib.get('methodName', node.tag)))
                    oid_map[oid] = {
                        "block_name": "[CỔNG_NGOÀI_CÙNG_SƠ_ĐỒ]",
                        "port_name": name
                    }

        # Step 2: scan specification and build OID -> block/port mapping
        main_spec = root.find('.//Specification[@name="Main"]')
        if main_spec is None:
            main_spec = root.find('.//Specification')
        if main_spec is None:
            return [], oid_map

        for diagram_element in main_spec.findall('.//DiagramElement'):
            for block in diagram_element:
                if block.tag in ['Connection', 'Comment', 'Note']:
                    continue

                b_type = block.tag
                if b_type == 'Literal':
                    b_name = block.attrib.get('value', 'Hằng_Số')
                elif b_type == 'Operator':
                    b_name = block.attrib.get('operator', block.attrib.get('kind', block.attrib.get('type', 'Toán_Tử')))
                elif b_type in ['Junction', 'Connector', 'ConnectionPoint']:
                    b_name = f"Điểm_Nối_{block.attrib.get('graphicOID', 'N/A')}"
                else:
                    b_name = block.attrib.get('elementName', block.attrib.get('name', block.attrib.get('methodName', block.tag)))

                for node in block.iter():
                    oid = node.attrib.get('graphicOID')
                    if oid and oid != "-1":
                        p_name = node.attrib.get('elementName', node.attrib.get('name', node.attrib.get('methodName', node.tag)))
                        if node == block:
                            oid_map[oid] = {"block_name": b_name, "port_name": "Bản thân khối"}
                        else:
                            oid_map[oid] = {"block_name": b_name, "port_name": p_name}

        # Step 3: parse connections (dedupe by source/target/bendpoints)
        parsed_conns = set()
        connections: List[Dict[str, str]] = []
        for conn in main_spec.findall('.//Connection'):
            start_elem = conn.find('.//Start')
            end_elem = conn.find('.//End')
            if start_elem is None or end_elem is None:
                continue

            src_oid = start_elem.attrib.get('graphicOID')
            tgt_oid = end_elem.attrib.get('graphicOID')
            if not src_oid or not tgt_oid:
                continue

            bends = tuple((float(b.attrib.get('x', 0)), float(b.attrib.get('y', 0))) for b in conn.findall('.//BendPoint'))
            c_key = (src_oid, tgt_oid, bends)
            if c_key in parsed_conns:
                continue

            parsed_conns.add(c_key)
            connections.append({"source_oid": src_oid, "target_oid": tgt_oid})

        return connections, oid_map

    @staticmethod
    def to_netlist_text(xml_file_path: str) -> str:
        connections, oid_map = DiagramNetlistExtractor.extract_connections(xml_file_path)

        lines = []
        lines.append("=" * 80)
        lines.append(" 📑 DANH SÁCH LIÊN KẾT TÍN HIỆU (NETLIST TỐI THƯỢNG)")
        lines.append(f" Nguồn: {xml_file_path}")
        lines.append("=" * 80)
        lines.append("")

        for i, conn in enumerate(connections, 1):
            src_oid = conn['source_oid']
            tgt_oid = conn['target_oid']

            src_info = oid_map.get(src_oid, {"block_name": f"Lỗi/Ẩn (OID {src_oid})", "port_name": "?"})
            tgt_info = oid_map.get(tgt_oid, {"block_name": f"Lỗi/Ẩn (OID {tgt_oid})", "port_name": "?"})

            src_str = f"[{src_info['block_name']}]"
            if "Bản thân khối" not in src_info['port_name']:
                src_str += f" (Cổng: {src_info['port_name']})"

            tgt_str = f"[{tgt_info['block_name']}]"
            if "Bản thân khối" not in tgt_info['port_name']:
                tgt_str += f" (Cổng: {tgt_info['port_name']})"

            lines.append(f"🔗 Dây {i:02d}: {src_str:<50} ---> {tgt_str}")

        return "\n".join(lines)


class DiagramAIReviewFlow:
    """Dedicated AI review flow for diagram queue items."""

    def __init__(self, config: Dict[str, Any], mode: str):
        self.config = config
        self.mode = mode
        self.class_path = str(config.get("class_path", ""))
        self.model_type = config.get("model_type", "gpt5-mini")
        self.model_config = create_model_config(self.model_type)
        self.response_handler = create_response_handler(self.model_type)
        self.api_key = config.get("api_key", "")
        self.api_url = self._build_chat_url()

    def _build_chat_url(self) -> str:
        if self.config.get("deepseek_api_url"):
            return str(self.config.get("deepseek_api_url"))

        base_url = str(self.config.get("api_base_url", "http://10.161.112.104:3000/v1")).rstrip("/")
        if base_url.endswith("/chat/completions"):
            return base_url
        return f"{base_url}/chat/completions"

    def _build_prompt(self, netlist_text: str) -> List[Dict[str, str]]:
        system_prompt = (
            "You are an automotive ASCET diagram reviewer. "
            "Review netlist-style connection text and detect only real mapping/semantic naming mistakes. "
            "If names are very similar (underscore/case/abbreviation variants), treat them as correct and do NOT report as defect."
        )

        user_prompt = f"""
Hãy review diagram netlist sau:

{netlist_text}

Yêu cầu rất quan trọng:
1. Tên na ná nhau (ví dụ khác underscore, viết hoa/thường, viết tắt gần nghĩa) thì coi là đúng.
2. Chỉ báo lỗi khi mismatch thật sự rõ ràng về ngữ nghĩa/tín hiệu.
3. Nếu không có lỗi thật, trả về No Defect.

Trả kết quả ĐÚNG JSON format sau (chỉ 1 khối json):
```json
{{
  "错误类型": ["参数映射名称一致性错误"],
  "状态": ["No Defect", "Defect"],
  "理由": "Nếu Defect thì liệt kê cụ thể dây nào sai và vì sao; nếu No Defect thì để rỗng hoặc ghi No obvious mismatch"
}}
```
""".strip()

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def _call_ai(self, messages: List[Dict[str, str]]) -> str:
        if not self.api_key:
            raise ValueError("Missing api_key for diagram AI review")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        payload = self.model_config.get_request_params(messages)
        # Diagram flow needs a deterministic single response payload.
        payload["stream"] = False

        response = requests.post(self.api_url, headers=headers, data=json.dumps(payload), timeout=180)
        response.raise_for_status()
        response_data = response.json()

        processed = self.response_handler.process_complete_response(response_data)
        return processed.get("complete_content") or processed.get("main_content") or ""

    def run(self) -> Dict[str, Any]:
        start_time = datetime.now()
        diagram_name = Path(self.class_path).name if self.class_path else "UnknownDiagram"

        try:
            netlist_text = DiagramNetlistExtractor.to_netlist_text(self.class_path)
            ai_review = self._call_ai(self._build_prompt(netlist_text))

            ai_error_details = extract_ai_errors(ai_review)
            ai_errors = len(ai_error_details)
            error_statistics = {
                "rule_errors": 0,
                "ai_errors": ai_errors,
                "total_errors": ai_errors,
                "rule_error_details": [],
                "ai_error_details": ai_error_details,
                "rule_severity_stats": {
                    "high_severity": 0,
                    "medium_severity": 0,
                    "low_severity": 0,
                    "has_high_severity": False,
                },
            }

            execution_time = (datetime.now() - start_time).total_seconds()
            return {
                "status": "success",
                "mode": self.mode,
                "execution_time": execution_time,
                "basic_issues": [],
                "ai_review": ai_review,
                "final_report": None,
                "current_report_path": None,
                "ascet_extraction_info": {
                    "class_path": self.class_path,
                    "diagram_name": diagram_name,
                    "diagram_review_flow": True,
                },
                "data_collection_status": "diagram_reviewed",
                "data_extraction_time": 0.0,
                "json_data_size": len(netlist_text),
                "error_statistics": error_statistics,
                "error_statistics_json": {
                    "error_statistics": error_statistics,
                    "mode": self.mode,
                    "class_path": self.class_path,
                    "note": "Diagram queue item - reviewed by dedicated diagram AI flow",
                },
                "summary": f"Diagram reviewed by dedicated AI flow: {diagram_name}",
                "token_statistics": "Diagram AI review completed",
            }

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return {
                "status": "error",
                "mode": self.mode,
                "error_message": f"Diagram review flow failed: {str(e)}",
                "execution_time": execution_time,
                "error_statistics": {
                    "rule_errors": 0,
                    "ai_errors": 0,
                    "total_errors": 0,
                    "rule_error_details": [],
                    "ai_error_details": [],
                    "rule_severity_stats": {
                        "high_severity": 0,
                        "medium_severity": 0,
                        "low_severity": 0,
                        "has_high_severity": False,
                    },
                },
                "summary": f"Diagram review failed: {diagram_name}",
            }
