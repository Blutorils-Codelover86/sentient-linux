"""
OpenAI cloud inference provider for Sentient Linux.
Disabled by default; requires explicit API key and external data-sharing consent.
"""

from __future__ import annotations
import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from sentient_linux.security.emergency_stop import EmergencyStop
from sentient_linux.security.privacy import ConsentManager, PrivacyError

logger = logging.getLogger("sentient.inference.openai")


class OpenAIProvider:
    """
    OpenAI API client adapter.
    Enforces privacy consent checks before any network transmission.
    """

    DESTINATION = "api.openai.com"

    def __init__(
        self,
        api_key: Optional[str] = None,
        consent_manager: Optional[ConsentManager] = None,
        base_url: str = "https://api.openai.com/v1",
        timeout: float = 45.0,
    ) -> None:
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.consent_manager = consent_manager or ConsentManager()
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.emergency_stop = EmergencyStop()

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def generate(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        has_screenshot: bool = False,
    ) -> str:
        self.emergency_stop.check()

        if not self.api_key:
            raise RuntimeError("OpenAI API key not configured. Set OPENAI_API_KEY to enable.")

        # Enforce explicit cloud consent
        payload_desc = "desktop context with screenshot" if has_screenshot else "desktop context and prompt"
        self.consent_manager.enforce_consent(
            provider="OpenAI",
            destination=self.DESTINATION,
            payload_type=payload_desc,
        )

        payload = {
            "model": model,
            "messages": messages,
        }
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                choices = data.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", "")
                return ""
        except urllib.error.HTTPError as err:
            self.emergency_stop.check()
            err_msg = err.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenAI API error ({err.code}): {err_msg[:200]}")
        except Exception as err:
            self.emergency_stop.check()
            raise RuntimeError(f"OpenAI connection error: {err}")
