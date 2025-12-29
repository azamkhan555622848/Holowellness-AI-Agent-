from __future__ import annotations

import os
import logging
from typing import Any, Dict, List, Optional

import requests


logger = logging.getLogger(__name__)


class OpenRouterClient:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, base_url: str = "https://openrouter.ai/api/v1"):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY", "")
        self.model = model or os.getenv("OPENROUTER_MODEL", "google/gemma-2b-it")
        self.base_url = base_url
        self.timeout_s = int(os.getenv("OPENROUTER_TIMEOUT", "45"))
        self.max_tokens = int(os.getenv("OPENROUTER_MAX_TOKENS", "256"))
        self.temperature = float(os.getenv("OPENROUTER_TEMPERATURE", "0.3"))

    def chat(self, messages: List[Dict[str, str]], *, model: Optional[str] = None, max_tokens: Optional[int] = None, temperature: Optional[float] = None) -> Dict[str, Any]:
        payload = {
            "model": model or self.model,
            "messages": messages,
            "max_tokens": max_tokens if max_tokens is not None else self.max_tokens,
            "temperature": temperature if temperature is not None else self.temperature,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": os.getenv("APP_PUBLIC_URL", "http://localhost"),
            "X-Title": os.getenv("APP_TITLE", "Gemma RAG Service"),
        }

        url = f"{self.base_url}/chat/completions"
        logger.info("Calling OpenRouter model=%s", payload["model"])
        r = requests.post(url, headers=headers, json=payload, timeout=self.timeout_s)
        if r.status_code != 200:
            logger.error("OpenRouter error %s: %s", r.status_code, r.text[:500])
            raise RuntimeError(f"OpenRouter HTTP {r.status_code}")

        data = r.json()
        content = data["choices"][0]["message"]["content"].strip()
        return {"message": {"content": content}, "model": payload["model"], "done": True}


