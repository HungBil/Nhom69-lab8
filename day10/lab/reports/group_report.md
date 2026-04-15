# Báo Cáo Nhóm — Lab Day 10: Data Pipeline & Data Observability

**Tên nhóm:** ___________  
**Thành viên:**
| Tên | Vai trò (Day 10) | Email |
|-----|------------------|-------|
| ___ | Ingestion / Raw Owner | ___ |
| ___ | Cleaning & Quality Owner | ___ |
| ___ | Embed & Idempotency Owner | ___ |
| ___ | Monitoring / Docs Owner | ___ |

**Ngày nộp:** ___________  
**Repo:** ___________  
**Độ dài khuyến nghị:** 600–1000 từ

---

> **Nộp tại:** `reports/group_report.md`  
> **Deadline commit:** xem `SCORING.md` (code/trace sớm; report có thể muộn hơn nếu được phép).  
> Phải có **run_id**, **đường dẫn artifact**, và **bằng chứng before/after** (CSV eval hoặc screenshot).

---

## 1. Pipeline tổng quan (150–200 từ)

> Nguồn raw là gì (CSV mẫu / export thật)? Chuỗi lệnh chạy end-to-end? `run_id` lấy ở đâu trong log?

**Tóm tắt luồng:**

_________________

**Lệnh chạy một dòng (copy từ README thực tế của nhóm):**

_________________

---

## 2. Cleaning & expectation (150–200 từ)

Sprint 2 bám theo `contracts/data_contract.yaml`: baseline đã có 6 rule (R1–R6),
nhóm bổ sung **4 rule mới (R7–R10)** ở [transform/cleaning_rules.py](transform/cleaning_rules.py)
và **3 expectation mới (E7–E9)** ở [quality/expectations.py](quality/expectations.py).
`ALLOWED_DOC_IDS` và `HR_MIN_EFFECTIVE_DATE` giờ đọc trực tiếp từ contract (không hard-code),
vì contract là source of truth — khi ops đổi `policy_versioning.hr_leave_min_effective_date`
pipeline nhận ngay mà không cần sửa code.

**Chống trivial — mọi rule/expectation mới đều có delta đo được** trên cùng file
`data/raw/policy_export_dirty.csv` (14 rows post-augment). So sánh với sprint1
(10 rows, trước khi mở rộng):

- Sprint 1: `raw=10, cleaned=6, quarantine=4` — artifact [manifest_sprint1.json](artifacts/manifests/manifest_sprint1.json)
- Sprint 2: `raw=14, cleaned=6, quarantine=8` — artifact [manifest_sprint2.json](artifacts/manifests/manifest_sprint2.json)

### 2a. Bảng metric_impact (bắt buộc — chống trivial)

| Rule / Expectation mới | Loại | Severity | Trước (sprint1) | Sau (sprint2) | Delta đo được | Chứng cứ |
|------------------------|------|----------|-----------------|---------------|----------------|----------|
| R7 `contains_placeholder` | cleaning | halt (via quar.) | 0 row quarantined cho lý do này | 1 row (`chunk_id=11`, marker `[TODO]`) | `quarantine_records +1` | [quarantine_sprint2.csv](artifacts/quarantine/quarantine_sprint2.csv) dòng 6 |
| R8 `chunk_too_long` (>1000) | cleaning | warn (via quar.) | 0 | 1 row (`chunk_id=12`, length=1126) | `quarantine_records +1` | [quarantine_sprint2.csv](artifacts/quarantine/quarantine_sprint2.csv) dòng 7 |
| R9 `exported_at_iso_required` | cleaning | halt (via quar.) | 0 | 1 row (`chunk_id=13`, empty exported_at) | `quarantine_records +1` | [quarantine_sprint2.csv](artifacts/quarantine/quarantine_sprint2.csv) dòng 8 |
| R10 `strip_invisible` (BOM/ZWSP) | cleaning | warn | — | `chunk_id=14` (BOM+ZWSP duplicate) bị R10 chuẩn hoá → R5 dedupe bắt được | Không có R10: row 14 thoát dedupe → cleaned +1 lạc hậu | [quarantine_sprint2.csv](artifacts/quarantine/quarantine_sprint2.csv) dòng 9 |
| E7 `no_placeholder_markers` | expectation | **halt** | (không chạy, rule chưa tồn tại) | PASS trên cleaned 6 rows sau khi R7 đã quarantine row 11 | Nếu tắt R7 → E7 fail (halt) | [run_sprint2.log](artifacts/logs/run_sprint2.log) dòng `expectation[no_placeholder_markers]` |
| E8 `chunk_max_length_1000` | expectation | warn | — | PASS (long_chunks=0 sau R8) | Nếu tắt R8 → `long_chunks=1` (warn) | [run_sprint2.log](artifacts/logs/run_sprint2.log) dòng `expectation[chunk_max_length_1000]` |
| E9 `exported_at_iso_required` | expectation | **halt** | — | PASS (bad_exported_at=0 sau R9) | Nếu tắt R9 → halt (row 13 empty) | [run_sprint2.log](artifacts/logs/run_sprint2.log) dòng `expectation[exported_at_iso_required]` |

**Rule chính (baseline + mở rộng, đồng bộ contract):**

- **R1–R6 (baseline):** allowlist `doc_id`, normalize `effective_date`, HR stale quarantine, dedupe, refund 14→7 fix.
- **R7 `no_placeholders`:** đồng bộ contract `quality_rules[no_placeholders]` — bắt `[TODO]/[TBD]/[PLACEHOLDER]` trước khi vào index.
- **R8 `no_long_chunks`:** contract `quality_rules[no_long_chunks]` — ngưỡng `MAX_CHUNK_LEN` parse từ description (fallback 1000).
- **R9 `exported_at_iso_required`:** đồng bộ `schema_cleaned.exported_at.required` — trước Sprint 2 pipeline chấp nhận `exported_at` rỗng, vi phạm contract.
- **R10 `strip_invisible`:** BOM/ZWSP khiến dedupe "nhìn thấy" bản sao gần giống; không có R10, row 14 lọt qua và poison index.

**Expectation halt hay warn:** E7 và E9 là **halt** (data không hợp lệ với contract, không được publish). E8 là **warn** — chunk dài không làm agent trả lời sai nhưng tăng token cost, cần theo dõi.

**Ví dụ 1 lần expectation fail (tái hiện được):** xoá R7 trong `cleaning_rules.py` rồi chạy
`python etl_pipeline.py run --run-id demo-e7-fail` → expectation `no_placeholder_markers`
fail với `placeholder_rows=1`, pipeline exit 2 (`PIPELINE_HALT`). Cách xử lý:
bật lại R7 (hoặc fix trực tiếp row 11 ở upstream) và rerun.

---

## 3. Before / after ảnh hưởng retrieval hoặc agent (200–250 từ)

> Bắt buộc: inject corruption (Sprint 3) — mô tả + dẫn `artifacts/eval/…` hoặc log.

**Kịch bản inject:**

_________________

**Kết quả định lượng (từ CSV / bảng):**

_________________

---

## 4. Freshness & monitoring (100–150 từ)

> SLA bạn chọn, ý nghĩa PASS/WARN/FAIL trên manifest mẫu.

_________________

---

## 5. Liên hệ Day 09 (50–100 từ)

> Dữ liệu sau embed có phục vụ lại multi-agent Day 09 không? Nếu có, mô tả tích hợp; nếu không, giải thích vì sao tách collection.

_________________

---

## 6. Rủi ro còn lại & việc chưa làm

- …
