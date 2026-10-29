"""
Privacy and PII protection for Sentient Linux.
Ported from upstream PIIScan.swift with added Linux-specific consent enforcement.
"""

from __future__ import annotations
import re
from typing import Optional, Set


class PrivacyError(RuntimeError):
    """Raised when external data transmission lacks required consent."""
    pass


class PIIScanner:
    """
    Deterministic PII filter adapted from upstream PIIScan.swift.
    Fails closed on high-risk credentials, financial identifiers, and government IDs.
    """

    # US SSN regex (excluding known invalid ranges 000, 666, 900-999)
    SSN_PATTERN = re.compile(
        r"\b(?!000|666|9\d{2})\d{3}[- ](?!00)\d{2}[- ](?!0000)\d{4}\b"
    )

    # 13 to 19 digit sequences potentially representing credit card PANs
    CARD_CANDIDATE_PATTERN = re.compile(r"\b(?:\d[ -]*?){13,19}\b")

    # Passport mention followed by 6-9 alphanumeric characters
    PASSPORT_PATTERN = re.compile(
        r"\b(?:passport|passport\s+no|passport\s+#)[:\s]+([a-zA-Z0-9]{6,9})\b",
        re.IGNORECASE,
    )

    # Common API key patterns
    API_KEY_PATTERN = re.compile(
        r"\b(?:sk-[a-zA-Z0-9]{20,}|ghp_[a-zA-Z0-9]{20,}|bearer\s+[a-zA-Z0-9_\-\.]{20,})\b",
        re.IGNORECASE,
    )

    @staticmethod
    def _is_luhn_valid(number_str: str) -> bool:
        """Standard Luhn checksum test for credit card numbers."""
        digits = [int(c) for c in number_str if c.isdigit()]
        if len(digits) < 13 or len(digits) > 19:
            return False
        checksum = 0
        reverse_digits = digits[::-1]
        for i, digit in enumerate(reverse_digits):
            if i % 2 == 1:
                doubled = digit * 2
                checksum += doubled - 9 if doubled > 9 else doubled
            else:
                checksum += digit
        return checksum % 10 == 0

    @classmethod
    def contains_high_risk_pii(cls, text: str) -> bool:
        """Returns True if the text contains verified high-risk PII."""
        if not text:
            return False

        # 1. SSN check
        if cls.SSN_PATTERN.search(text):
            return True

        # 2. Passport check
        if cls.PASSPORT_PATTERN.search(text):
            return True

        # 3. Credit card Luhn check
        for match in cls.CARD_CANDIDATE_PATTERN.finditer(text):
            candidate = re.sub(r"[\s-]", "", match.group(0))
            if cls._is_luhn_valid(candidate):
                return True

        return False

    @classmethod
    def sanitize_for_logging(cls, text: str) -> str:
        """Strip sensitive keys, tokens, and PII from log messages."""
        if not text:
            return ""
        # Redact API keys
        sanitized = cls.API_KEY_PATTERN.sub("[REDACTED_API_KEY]", text)
        # Redact SSNs
        sanitized = cls.SSN_PATTERN.sub("[REDACTED_SSN]", sanitized)
        # Redact Passports
        sanitized = cls.PASSPORT_PATTERN.sub("passport: [REDACTED_PASSPORT]", sanitized)
        return sanitized


class ConsentManager:
    """
    Manages explicit user authorization for sending data to external cloud providers.
    Cloud access is disabled by default.
    """

    def __init__(self) -> None:
        self._authorized_cloud_destinations: Set[str] = set()

    def is_cloud_authorized(self, destination: str) -> bool:
        """Return True only if user explicitly authorized the given destination."""
        return destination.lower() in self._authorized_cloud_destinations

    def authorize_cloud_destination(self, destination: str) -> None:
        self._authorized_cloud_destinations.add(destination.lower())

    def revoke_cloud_destination(self, destination: str) -> None:
        self._authorized_cloud_destinations.discard(destination.lower())

    def enforce_consent(self, provider: str, destination: str, payload_type: str) -> None:
        """Enforce default-deny rule on external transmission."""
        if not self.is_cloud_authorized(destination):
            raise PrivacyError(
                f"Cloud transmission blocked: No user consent granted to send {payload_type} "
                f"to {destination} via {provider}. Keep inference local or grant explicit consent."
            )
