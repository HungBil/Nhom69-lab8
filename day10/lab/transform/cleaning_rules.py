"""
Cleaning rules — raw export → cleaned rows + quarantine.

Baseline gồm các failure mode mở rộng (allowlist doc_id, parse ngày, HR stale version).
Sprint 2 bổ sung các rule mới bám theo `contracts/data_contract.yaml`:
  - no_placeholders          (R7)  — halt-effect qua quarantine
  - no_long_chunks (>1000)   (R8)  — warn-effect qua quarantine
  - exported_at_iso_required (R9)  — schema cleaned bắt buộc
  - invisible_char_stripper  (R10) — chuẩn hoá BOM/zero-width trước dedupe

Các rule mới đều có `metric_impact` đo được trên `policy_export_dirty.csv`
(xem `reports/group_report.md` bảng metric_impact).
"""

from __future__ import annotations

import csv
import hashlib
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    import yaml  # PyYAML có trong requirements.txt
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

_CONTRACT_PATH = Path(__file__).resolve().parent.parent / "contracts" / "data_contract.yaml"

# Fallback khi không đọc được contract (test môi trường không cài PyYAML).
_FALLBACK_ALLOWED_DOC_IDS = frozenset(
    {
        "policy_refund_v4",
        "sla_p1_2026",
        "it_helpdesk_faq",
        "hr_leave_policy",
    }
)
_FALLBACK_HR_MIN_EFFECTIVE_DATE = "2026-01-01"
_FALLBACK_MAX_CHUNK_LEN = 1000


def _load_contract() -> Dict[str, Any]:
    if yaml is None or not _CONTRACT_PATH.is_file():
        return {}
    try:
        return yaml.safe_load(_CONTRACT_PATH.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return {}


_CONTRACT = _load_contract()

ALLOWED_DOC_IDS = frozenset(
    _CONTRACT.get("allowed_doc_ids") or _FALLBACK_ALLOWED_DOC_IDS
)
HR_MIN_EFFECTIVE_DATE: str = (
    (_CONTRACT.get("policy_versioning") or {}).get("hr_leave_min_effective_date")
    or _FALLBACK_HR_MIN_EFFECTIVE_DATE
)


def _max_chunk_len_from_contract() -> int:
    for rule in _CONTRACT.get("quality_rules") or []:
        if rule.get("id") == "no_long_chunks":
            m = re.search(r"(\d{3,5})", rule.get("description") or "")
            if m:
                return int(m.group(1))
    return _FALLBACK_MAX_CHUNK_LEN


MAX_CHUNK_LEN: int = _max_chunk_len_from_contract()

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DMY_SLASH = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")
_ISO_DATETIME = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?$"
)

_PLACEHOLDER_MARKERS: Tuple[str, ...] = ("[TODO]", "[TBD]", "[PLACEHOLDER]")

_INVISIBLE_CHARS = (
    "\ufeff"  # BOM
    "\u200b"  # zero-width space
    "\u200c"  # zero-width non-joiner
    "\u200d"  # zero-width joiner
    "\u2060"  # word joiner
)
_INVISIBLE_RE = re.compile(f"[{_INVISIBLE_CHARS}]")


def _norm_text(s: str) -> str:
    return " ".join((s or "").strip().split()).lower()


def _stable_chunk_id(doc_id: str, chunk_text: str, seq: int) -> str:
    h = hashlib.sha256(f"{doc_id}|{chunk_text}|{seq}".encode("utf-8")).hexdigest()[:16]
    return f"{doc_id}_{seq}_{h}"


def _normalize_effective_date(raw: str) -> Tuple[str, str]:
    """
    Trả về (iso_date, error_reason).
    iso_date rỗng nếu không parse được.
    """
    s = (raw or "").strip()
    if not s:
        return "", "empty_effective_date"
    if _ISO_DATE.match(s):
        return s, ""
    m = _DMY_SLASH.match(s)
    if m:
        dd, mm, yyyy = m.group(1), m.group(2), m.group(3)
        return f"{yyyy}-{mm}-{dd}", ""
    return "", "invalid_effective_date_format"


def _strip_invisible(s: str) -> str:
    return _INVISIBLE_RE.sub("", s or "")


def _detect_placeholder(s: str) -> str:
    upper = (s or "").upper()
    for marker in _PLACEHOLDER_MARKERS:
        if marker in upper:
            return marker
    return ""


def load_raw_csv(path: Path) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append({k: (v or "").strip() for k, v in r.items()})
    return rows


def clean_rows(
    rows: List[Dict[str, str]],
    *,
    apply_refund_window_fix: bool = True,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Trả về (cleaned, quarantine).

    Baseline (narrative Day 10):
      R1) Quarantine: doc_id không thuộc allowlist contract.
      R2) Chuẩn hoá effective_date; quarantine khi không parse được.
      R3) Quarantine: hr_leave_policy effective_date < HR_MIN_EFFECTIVE_DATE (lấy từ contract).
      R4) Quarantine: chunk_text rỗng.
      R5) Loại trùng nội dung chunk_text (giữ bản đầu).
      R6) Fix stale refund: policy_refund_v4 chứa '14 ngày làm việc' → 7 ngày.

    Sprint 2 — rule mới (đo được trên `policy_export_dirty.csv`):
      R7)  Quarantine nếu chunk_text chứa marker placeholder ([TODO]/[TBD]/[PLACEHOLDER]).
      R8)  Quarantine nếu chunk_text dài vượt MAX_CHUNK_LEN (từ contract `no_long_chunks`).
      R9)  Quarantine nếu exported_at rỗng hoặc không đúng ISO datetime (schema required).
      R10) Chuẩn hoá BOM/zero-width trước dedupe (khiến dedupe R5 bắt được bản "vô hình"
           khác bản gốc — delta đo bằng quarantine_records tăng khi có row BOM).
    """
    quarantine: List[Dict[str, Any]] = []
    seen_text: set[str] = set()
    cleaned: List[Dict[str, Any]] = []
    seq = 0

    for raw in rows:
        doc_id = raw.get("doc_id", "")
        text = raw.get("chunk_text", "")
        eff_raw = raw.get("effective_date", "")
        exported_at = raw.get("exported_at", "")

        # R1
        if doc_id not in ALLOWED_DOC_IDS:
            quarantine.append({**raw, "reason": "unknown_doc_id"})
            continue

        # R2
        eff_norm, eff_err = _normalize_effective_date(eff_raw)
        if eff_err == "empty_effective_date":
            quarantine.append({**raw, "reason": "missing_effective_date"})
            continue
        if eff_err == "invalid_effective_date_format":
            quarantine.append({**raw, "reason": eff_err, "effective_date_raw": eff_raw})
            continue

        # R3
        if doc_id == "hr_leave_policy" and eff_norm < HR_MIN_EFFECTIVE_DATE:
            quarantine.append(
                {
                    **raw,
                    "reason": "stale_hr_policy_effective_date",
                    "effective_date_normalized": eff_norm,
                    "hr_min_effective_date": HR_MIN_EFFECTIVE_DATE,
                }
            )
            continue

        # R4
        if not text:
            quarantine.append({**raw, "reason": "missing_chunk_text"})
            continue

        # R9: exported_at must be ISO datetime (schema contract)
        if not exported_at or not _ISO_DATETIME.match(exported_at):
            quarantine.append(
                {
                    **raw,
                    "reason": "missing_or_invalid_exported_at",
                    "exported_at_raw": exported_at,
                }
            )
            continue

        # R10: strip BOM / zero-width characters trước khi dedupe & lưu
        text_clean = _strip_invisible(text)

        # R7: placeholder markers
        marker = _detect_placeholder(text_clean)
        if marker:
            quarantine.append(
                {
                    **raw,
                    "reason": "contains_placeholder",
                    "placeholder_marker": marker,
                }
            )
            continue

        # R8: chunk too long (contract `no_long_chunks`)
        if len(text_clean) > MAX_CHUNK_LEN:
            quarantine.append(
                {
                    **raw,
                    "reason": "chunk_too_long",
                    "chunk_length": len(text_clean),
                    "max_chunk_length": MAX_CHUNK_LEN,
                }
            )
            continue

        # R5: dedupe
        key = _norm_text(text_clean)
        if key in seen_text:
            quarantine.append({**raw, "reason": "duplicate_chunk_text"})
            continue
        seen_text.add(key)

        # R6: fix stale refund window
        fixed_text = text_clean
        if apply_refund_window_fix and doc_id == "policy_refund_v4":
            if "14 ngày làm việc" in fixed_text:
                fixed_text = fixed_text.replace(
                    "14 ngày làm việc",
                    "7 ngày làm việc",
                )
                fixed_text += " [cleaned: stale_refund_window]"

        seq += 1
        cleaned.append(
            {
                "chunk_id": _stable_chunk_id(doc_id, fixed_text, seq),
                "doc_id": doc_id,
                "chunk_text": fixed_text,
                "effective_date": eff_norm,
                "exported_at": exported_at,
            }
        )

    return cleaned, quarantine


def write_cleaned_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("chunk_id,doc_id,chunk_text,effective_date,exported_at\n", encoding="utf-8")
        return
    fieldnames = ["chunk_id", "doc_id", "chunk_text", "effective_date", "exported_at"]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})


def write_quarantine_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("chunk_id,doc_id,chunk_text,effective_date,exported_at,reason\n", encoding="utf-8")
        return
    keys: List[str] = []
    seen_k: set[str] = set()
    for r in rows:
        for k in r.keys():
            if k not in seen_k:
                seen_k.add(k)
                keys.append(k)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore", restval="")
        w.writeheader()
        for r in rows:
            w.writerow(r)
