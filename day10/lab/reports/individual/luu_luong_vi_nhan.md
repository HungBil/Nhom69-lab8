# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Lưu Lương Vi Nhân

**Vai trò:** Cleaning / Quality Owner — Sprint 2

**Ngày nộp:** 2026-04-15

**Độ dài yêu cầu:** **400–650 từ** 

---

## 1. Tôi phụ trách phần nào? (80–120 từ)

**File / module:**

- [transform/cleaning_rules.py](../../transform/cleaning_rules.py) — tôi thêm **3 rule mới** nằm ngay trong vòng lặp `clean_rows`: R7 chuẩn hoá whitespace (giữ case để không làm hỏng keyword matching downstream), R8 quarantine chunk chứa marker `DRAFT` / `INTERNAL ONLY` (`prohibited_content_marker`), và R9 validate `exported_at` bằng `datetime.fromisoformat` — row format sai đi vào quarantine với reason `invalid_exported_at_format`.
- [quality/expectations.py](../../quality/expectations.py) — tôi thêm **2 expectation**: **E7** `no_placeholders` (severity **halt**, chặn `[TODO]/[TBD]/PLACEHOLDER`) và **E8** `chunk_max_length_1000` (severity **warn**, đếm chunk > 1000 ký tự).

**Kết nối với thành viên khác:**

Ingestion Owner cấp `raw_records` và manifest; tôi đọc vào và trả lại `cleaned_records` + `quarantine_records` để Embed Owner upsert. Monitoring Owner dùng expectation halt/warn của tôi làm signal cho runbook.

**Bằng chứng (commit / comment trong code):**

[transform/cleaning_rules.py:119-133](../../transform/cleaning_rules.py#L119-L133) và [quality/expectations.py:115-141](../../quality/expectations.py#L115-L141).

---

## 2. Một quyết định kỹ thuật (100–150 từ)

**Chọn `halt` cho E7 nhưng chỉ `warn` cho E8.** Lý do: `[TODO]` / `[TBD]` trong cleaned chunk có nghĩa là tài liệu nguồn **chưa finalized** — nếu embed, agent sẽ trích dẫn draft như câu trả lời chính thức, gây incident lộ nội dung nội bộ (đúng tinh thần slide Day 10 "publish boundary"). Ngược lại, chunk > 1000 ký tự chỉ ảnh hưởng token cost và độ chính xác retrieval (lớp vector bị loãng), không phải lỗi **đúng/sai** → theo dõi được bằng metric, không cần chặn pipeline. Tôi cũng cân nhắc đặt R8 (prohibited content) ở severity halt nhưng cuối cùng chọn quarantine + continue, vì nếu ai đó lỡ đánh dấu `DRAFT` ở 1 row hợp lệ, cả pipeline không nên sập — chỉ cần loại row đó và log lại. Ranh giới "halt ở schema + policy, warn ở quality/perf" là trụ tôi bám khi thêm rule sau này.

---

## 3. Một lỗi hoặc anomaly đã xử lý (100–150 từ)

**Triệu chứng:** raw row 3 của `policy_refund_v4` còn chứa "14 ngày làm việc" — lệch với source of truth v4 (7 ngày). Nếu embed nguyên xi, agent refund sẽ trả về số sai cho customer service.

**Detection:** expectation E3 `refund_no_stale_14d_window` (halt) chạy **sau clean**; nếu R6 fix fail, E3 bật halt → `PIPELINE_HALT` exit code 2.

**Fix:** R6 trong `cleaning_rules.py` replace string "14 ngày làm việc" → "7 ngày làm việc" và append `[cleaned: stale_refund_window]` vào cuối chunk để audit trail còn thấy được row nào đã bị rewrite.

**Bằng chứng trong `run_id=2026-04-15T08-38Z`:** expectation log `expectation[refund_no_stale_14d_window] OK (halt) :: violations=0` — có nghĩa R6 đã bắt và clean thành công trước khi E3 kiểm tra.

---

## 4. Bằng chứng trước / sau (80–120 từ)

**`run_id=2026-04-15T08-38Z`** — artifact: [cleaned_2026-04-15T08-38Z.csv](../../artifacts/cleaned/cleaned_2026-04-15T08-38Z.csv).

**Trước** (raw row 3 trong [data/raw/policy_export_dirty.csv](../../data/raw/policy_export_dirty.csv)):

```
3,policy_refund_v4,"Yêu cầu hoàn tiền được chấp nhận trong vòng 14 ngày làm việc kể từ xác nhận đơn (ghi chú: bản sync cũ policy-v3 — lỗi migration).",2026-02-01,2026-04-10T08:00:00
```

**Sau** (cleaned row 2, cùng run):

```
policy_refund_v4_2_c96089a43e33aa9d,policy_refund_v4,Yêu cầu hoàn tiền được chấp nhận trong vòng 7 ngày làm việc kể từ xác nhận đơn (ghi chú: bản sync cũ policy-v3 — lỗi migration). [cleaned: stale_refund_window],2026-02-01,2026-04-10T08:00:00
```

Manifest cùng run: `raw_records=10, cleaned_records=6, quarantine_records=4` — [manifest_2026-04-15T08-38Z.json](../../artifacts/manifests/manifest_2026-04-15T08-38Z.json).

---

## 5. Cải tiến tiếp theo (40–80 từ)

Đọc `MAX_CHUNK_LEN` của E8 và danh sách placeholder của E7 **trực tiếp từ `contracts/data_contract.yaml`** (contract đã khai báo `no_long_chunks` và `no_placeholders` ở `quality_rules`) thay vì hard-code trong Python. Khi ops điều chỉnh ngưỡng, pipeline áp dụng ngay ở run kế mà không cần PR code — đây đúng là yêu cầu Distinction (d) trong [SCORING.md](../../SCORING.md).
