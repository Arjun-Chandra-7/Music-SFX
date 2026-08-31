"""Conservative local policy checks for autonomous audio work."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass(frozen=True)
class PolicyDecision:
    authority: str
    allowed: bool
    reasons: tuple[str, ...]

    def as_dict(self) -> dict:
        result = asdict(self)
        result["reasons"] = list(self.reasons)
        return result


def evaluate(*, input_path: Path, output_path: Path, rights: str, overwrite: bool) -> PolicyDecision:
    reasons: list[str] = []
    if rights not in {"owned", "licensed", "public_domain", "unknown"}:
        return PolicyDecision("forbidden", False, ("rights must be owned, licensed, public_domain, or unknown",))
    if rights == "unknown":
        reasons.append("source rights are unknown; review before publishing")
    if input_path.resolve() == output_path.resolve():
        return PolicyDecision("forbidden", False, ("in-place source overwrite is not permitted",))
    if output_path.exists() and not overwrite:
        return PolicyDecision("forbidden", False, ("output exists; explicitly pass overwrite=true",))
    if not input_path.is_file():
        return PolicyDecision("forbidden", False, ("input file does not exist",))
    authority = "approval_required" if rights == "unknown" else "allowed"
    return PolicyDecision(authority, True, tuple(reasons or ["local deterministic audio processing"]))

