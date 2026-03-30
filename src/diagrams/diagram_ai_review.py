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

from src.ai_core.model_config import create_model_config
from src.ai_core.response_handler import create_response_handler
from src.ai_core.ai_error_arbitrator import extract_ai_errors


from urllib.parse import urlparse

def get_proxies_for_url(url: str):
    host = urlparse(url).hostname or ""
    
    # Internal network (10.x.x.x)
    if host.startswith("10."):
        return {"http": None, "https": None}
    
    # Otherwise, use system proxy (if any)
    return None

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
                        "block_name": "[External Port]" if node.tag == 'ExternalPort' else "[Global Port]",
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
                    b_name = block.attrib.get('value', 'constant')
                elif b_type == 'Operator':
                    b_name = block.attrib.get('operator', block.attrib.get('kind', block.attrib.get('type', 'operator')))
                elif b_type in ['Junction', 'Connector', 'ConnectionPoint']:
                    b_name = f"Connection_Point_{block.attrib.get('graphicOID', 'N/A')}"
                else:
                    b_name = block.attrib.get('elementName', block.attrib.get('name', block.attrib.get('methodName', block.tag)))

                for node in block.iter():
                    oid = node.attrib.get('graphicOID')
                    if oid and oid != "-1":
                        p_name = node.attrib.get('elementName', node.attrib.get('name', node.attrib.get('methodName', node.tag)))
                        if node == block:
                            oid_map[oid] = {"block_name": b_name, "port_name": "Self"}
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
        lines.append(" 📑 CONNECTION LIST (NETLIST)")
        lines.append(f" Source: {xml_file_path}")
        lines.append("=" * 80)
        lines.append("")

        for i, conn in enumerate(connections, 1):
            src_oid = conn['source_oid']
            tgt_oid = conn['target_oid']

            src_info = oid_map.get(src_oid, {"block_name": f"Error/Hidden (OID {src_oid})", "port_name": "?"})
            tgt_info = oid_map.get(tgt_oid, {"block_name": f"Error/Hidden (OID {tgt_oid})", "port_name": "?"})

            src_str = f"[{src_info['block_name']}]"
            if "Self" not in src_info['port_name']:
                src_str += f" (Port: {src_info['port_name']})"

            tgt_str = f"[{tgt_info['block_name']}]"
            if "Self" not in tgt_info['port_name']:
                tgt_str += f" (Port: {tgt_info['port_name']})"

            lines.append(f"🔗 Wire {i:02d}: {src_str:<50} ---> {tgt_str}")

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

    from typing import List, Dict

    def _build_prompt(self, netlist_text: str) -> List[Dict[str, str]]:
        system_prompt = (
            "You are an expert Automotive Software and ASCET Diagram Reviewer. "
            "Your task is to review netlist-style connections and detect signal mapping or semantic naming mistakes. "
            "You must strictly distinguish between harmless naming variations and actual logic/wiring defects."
        )
        user_prompt = f"""Please perform a rigorous, line-by-line review of the following ASCET diagram netlist:

{netlist_text}

### 🔍 Review Guidelines:

1. **Acceptable Variations (Do NOT report as defect):**
   - Ignoring standard module prefixes (e.g., `CM_HAZ_ABSActive` mapped to `ABSActive` is CORRECT).
   - Case and underscore variations (e.g., `a_Veh_x_Target` mapped to `a_veh_x_Target` is CORRECT).
   - Expected signal routing conventions.

2. **CRITICAL DEFECTS TO CATCH (Must report as Defect):**
   - **Positional/Spatial Swaps:** Mixing up directional identifiers. Connecting a Right-side signal to a Left-side port is a severe error. (e.g., `FR` connected to `FL`, or `RR` to `RL`).
   - **Functional/Logic Swaps:** Confusing the nature of the signal. Wiring a "Request" signal to a "Switch" port, or vice versa, is a severe error. (e.g., `Brake_Request` mapped to `BrakeLightSwitch`, or `Brake_Light_switch` mapped to `Brake_request`).
   - **Crossed Wires:** Pay close attention to pairs of signals that appear to have their destination ports swapped with one another.

### 📝 Output Format:
Return your final analysis in the following JSON format ONLY (Ensure the output is exactly 1 valid JSON block).

```json
{{
  "错误类型": ["List the categories of errors here, e.g., Positional Mismatch, Functional Swap. Leave empty if no defect"],
  "状态": "Defect", // Strictly choose either "Defect" or "No Defect"
  "理由": "If Defect, explicitly list EVERY incorrect Wire number and precisely explain why the source and destination do not semantically match. If No Defect, write 'No obvious mismatch'."
}}""".strip()

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

       # response = requests.post(self.api_url, headers=headers, data=json.dumps(payload), timeout=180)
        proxies = get_proxies_for_url(self.api_url)

        response = requests.post(
            self.api_url,
            headers=headers,
            data=json.dumps(payload),
            timeout=180,
            proxies=proxies
        )
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
            print(f"[DiagramAIReviewFlow] Diagram review flow failed: {str(e)}")
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