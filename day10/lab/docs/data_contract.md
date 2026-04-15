# Data contract — Lab Day 10

> Bắt đầu từ `contracts/data_contract.yaml` — mở rộng và đồng bộ file này.

---

## 1. Nguồn dữ liệu (source map)

| Nguồn            | Phương thức ingest | Failure mode chính                                                    | Metric / alert         |
| ---------------- | ------------------ | --------------------------------------------------------------------- | ---------------------- |
| Legal/Artifacts  | CSV Export         | Stale version. Chunk 1, 2: 7 ngày làm việc, chunk 3: 14 ngày làm việc | `hits_forbidden`       |
| IT Helpdesk Wiki | CSV Export         | Empty chunk, unknown ID. Chunk 3 rỗng, chunk 10 sai format date       | `quarantine_count`     |
| HR Portal        | CSV Export         | Version conflict. Policy conflict ngày                                | `hr_stale_expectation` |

---

## 2. Schema cleaned

| Cột            | Kiểu     | Bắt buộc | Ghi chú                                    |
| -------------- | -------- | -------- | ------------------------------------------ |
| chunk_id       | string   | Có       | Hash stable của doc_id + text + seq        |
| doc_id         | string   | Có       | Khớp ALLOWED_DOC_IDS                       |
| chunk_text     | string   | Có       | Text đã được normalize whitespace/mask PII |
| effective_date | date     | Có       | ISO YYYY-MM-DD                             |
| exported_at    | datetime | Có       | ISO format xác định freshness              |

---

## 3. Quy tắc quarantine vs drop

> Record bị flag sẽ được ghi vào `artifacts/quarantine/quarantine_<run_id>.csv`.
> Ingestion Owner phải review file quarantine mỗi run.

**Lý do quarantine hiện hành (map 1:1 với cleaning rules):**

| Reason | Rule | Severity | Contract ref |
|--------|------|----------|--------------|
| `unknown_doc_id` | R1 | drop | `allowed_doc_ids` |
| `missing_effective_date` / `invalid_effective_date_format` | R2 | drop | `schema_cleaned.effective_date` |
| `stale_hr_policy_effective_date` | R3 | drop | `policy_versioning.hr_leave_min_effective_date` |
| `missing_chunk_text` | R4 | drop | `schema_cleaned.chunk_text.required` |
| `duplicate_chunk_text` | R5 (+ R10 normalize) | warn | `quality_rules.no_duplicate_chunk_text` |
| `contains_placeholder` | R7 | **halt** | `quality_rules.no_placeholders` |
| `chunk_too_long` | R8 | warn | `quality_rules.no_long_chunks` |
| `missing_or_invalid_exported_at` | R9 | **halt** | `schema_cleaned.exported_at.required` |

**Expectation đồng bộ:** `no_placeholder_markers` (E7, halt), `chunk_max_length_1000` (E8, warn),
`exported_at_iso_required` (E9, halt) — xem [quality/expectations.py](../quality/expectations.py).

---

## 4. Phiên bản & canonical

Source of truth cho policy refund là `policy_refund_v4` (Window = **7 ngày**). Các bản v3
(14 ngày) bị auto-clean ở R6 hoặc halt ở E3 nếu phát hiện.

Ngưỡng versioning HR (`hr_leave_min_effective_date = 2026-01-01`) lấy trực tiếp từ
`contracts/data_contract.yaml` qua `_load_contract()` trong cleaning_rules — không hard-code.
Ops đổi ngày trong contract thì pipeline áp dụng ngay ở run kế.
