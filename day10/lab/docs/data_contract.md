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
> Các lý do quarantine bao gồm: Unknown Doc ID, Missing Text, Invalid Date, Stale HR Policy, và prohibited content (Draft/Internal).
> Ingestion Owner phải review file quarantine.

---

## 4. Phiên bản & canonical

> Source of truth cho policy refund là `policy_refund_v4` (Window = 7 ngày). Các bản v3 (14 ngày) sẽ bị auto-clean hoặc halt pipeline nếu phát hiện.
