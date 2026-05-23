from dataclasses import dataclass
import re


@dataclass
class PolicyDecision:
    allow: bool
    needs_confirmation: bool
    reason: str


class SafetyPolicy:
    """Simple command safety layer for local system actions."""

    BLOCK_PATTERNS = [
        r"\brm\s+-rf\s+/\b",
        r"\bmkfs\b",
        r"\bdd\b.*\bof=/dev/",
        r"\bshutdown\b",
        r"\breboot\b",
        r"\binit\s+0\b",
    ]

    HIGH_RISK_PATTERNS = [
        r"\brm\b",
        r"\bmv\b",
        r"\bchmod\b",
        r"\bchown\b",
        r"\bapt\b|\byum\b|\bdnf\b|\bbrew\b|\bpip\b",
        r">|>>",
        r"\bkill\b",
    ]

    def __init__(self, approval_mode: str = "ask") -> None:
        self.approval_mode = approval_mode

    def evaluate_shell(self, command: str) -> PolicyDecision:
        normalized = command.strip()

        for pat in self.BLOCK_PATTERNS:
            if re.search(pat, normalized):
                return PolicyDecision(False, False, f"blocked by policy pattern: {pat}")

        for pat in self.HIGH_RISK_PATTERNS:
            if re.search(pat, normalized):
                if self.approval_mode == "auto":
                    return PolicyDecision(True, False, f"high risk, auto mode: {pat}")
                if self.approval_mode == "block":
                    return PolicyDecision(False, False, f"high risk denied in block mode: {pat}")
                return PolicyDecision(True, True, f"high risk command requires confirmation: {pat}")

        return PolicyDecision(True, False, "safe")
