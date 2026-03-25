# request.py
"""
Simple API request module for model selection and prompt sending
"""

import requests
from src.ai_core.model_config import create_model_config


import os
import json

def _auto_get_api_key():
	# Ưu tiên các biến môi trường hoặc file cấu hình phổ biến
	# 1. Biến môi trường
	for env_key in ["DEEPSEEK_API_KEY", "OPENAI_API_KEY", "API_KEY", "api_key"]:
		v = os.environ.get(env_key)
		if v and v.strip():
			return v.strip()
	# 2. File config phổ biến
	for config_file in ["build_config.json", "config.json"]:
		if os.path.exists(config_file):
			try:
				with open(config_file, "r", encoding="utf-8") as f:
					cfg = json.load(f)
				for k in ["api_key", "deepseek_api_key", "openai_api_key"]:
					if k in cfg and cfg[k]:
						return cfg[k]
			except Exception:
				pass
	return None

def send_prompt(prompt: str, model_type: str = "gpt5-mini", api_key: str = None, api_url: str = None) -> str:
	"""
	Send a prompt to the selected model and return the response content.
	Tự động lấy API key nếu không truyền vào.
	"""
	model_config = create_model_config(model_type)
	messages = [
		{"role": "user", "content": prompt}
	]
	payload = model_config.get_request_params(messages)
	if api_key is None:
		api_key = _auto_get_api_key()
	if not api_key:
		raise RuntimeError("Không tìm thấy API key! Hãy đặt biến môi trường DEEPSEEK_API_KEY hoặc OPENAI_API_KEY hoặc điền vào build_config.json.")
	if api_url is None:
		api_url = "http://10.161.112.104:3000/v1/chat/completions"
	headers = {
		"Content-Type": "application/json",
		"Authorization": f"Bearer {api_key}",
	}
	response = requests.post(api_url, headers=headers, json=payload, timeout=60)
	response.raise_for_status()
	data = response.json()
	# Try to extract content from OpenAI-compatible response
	try:
		return data["choices"][0]["message"]["content"]
	except Exception:
		return str(data)

# Example usage
if __name__ == "__main__":
	prompt = "Say hello, model!"
	print(send_prompt(prompt, model_type="gpt5-mini"))
