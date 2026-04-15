# Báo Cáo Nhóm — Lab Day 10: Data Pipeline & Data Observability

**Tên nhóm:** Nhom69-E403  
**Thành viên:**
| Tên | Vai trò (Day 10) | Email |
|-----|------------------|-------|
| Khuất Văn Vương | Ingestion / Raw Owner | 26ai.vuongkv@vinuni.edu.vn |
| Lưu Lương Vi Nhân | Cleaning & Quality Owner | 26ai.nhanllv@vinuni.edu.vn |
| Nguyễn Đông Hưng | Embed & Idempotency Owner | 26ai.hungnd2@vinuni.edu.vn |
| Huỳnh Văn Nghĩa | Monitoring / Docs Owner | 26ai.nghiahv@vinuni.edu.vn |

**Ngày nộp:** 15/04/2026  
**Repo:** [Nhom69-lab8](https://github.com/HungBil/Nhom69-lab8)  
**Độ dài khuyến nghị:** 600–1000 từ

---

> **Nộp tại:** `reports/group_report.md`  
> **Deadline commit:** xem `SCORING.md` (code/trace sớm; report có thể muộn hơn nếu được phép).  
> Phải có **run_id**, **đường dẫn artifact**, và **bằng chứng before/after** (CSV eval hoặc screenshot).

---

## 1. Pipeline tổng quan (150–200 từ)

> Nguồn raw là gì (CSV mẫu / export thật)? Chuỗi lệnh chạy end-to-end? `run_id` lấy ở đâu trong log?

**Tóm tắt luồng:**

Nhóm sử dụng nguồn raw dạng CSV tại `data/raw/policy_export_dirty.csv` (10 records), mô phỏng dữ liệu export từ các hệ CS/IT/HR với lỗi thực tế: duplicate, thiếu ngày hiệu lực, doc_id ngoài allowlist và xung đột version policy. Pipeline chạy theo chuỗi ingest -> clean -> validate -> embed -> publish manifest. Ở bước clean, hệ thống chuẩn hoá `effective_date`, loại bản HR stale, loại trùng nội dung và sửa stale refund window 14 -> 7 ngày cho `policy_refund_v4`. Sau đó expectation suite quyết định halt/warn, rồi embed theo cơ chế upsert `chunk_id` vào collection `day10_kb` và prune id cũ để giữ publish boundary.

Trong vòng test cuối, nhóm dùng ba run chính để chứng minh before/after: `final-clean`, `final-inject-bad`, `final-clean-after-fix`. Các chỉ số `raw_records`, `cleaned_records`, `quarantine_records`, cờ `no_refund_fix/skipped_validate`, và `latest_exported_at` được ghi trong manifest tương ứng tại `artifacts/manifests/manifest_final-*.json` để truy vết toàn bộ lineage của lần publish.

**Lệnh chạy một dòng (copy từ README thực tế của nhóm):**

`python etl_pipeline.py run --run-id final-clean && python eval_retrieval.py --out artifacts/eval/final_clean.csv`

---

## 2. Cleaning & expectation (150–200 từ)

> Baseline đã có nhiều rule (allowlist, ngày ISO, HR stale, refund, dedupe…). Nhóm thêm **≥3 rule mới** + **≥2 expectation mới**. Khai báo expectation nào **halt**.

### 2a. Bảng metric_impact (bắt buộc — chống trivial)

| Rule / Expectation mới (tên ngắn) | Trước (số liệu) | Sau / khi inject (số liệu) | Chứng cứ (log / CSV / commit) |
|-----------------------------------|------------------|-----------------------------|-------------------------------|
| refund_fix + `refund_no_stale_14d_window` (halt) | `final_clean`: `q_refund_window hits_forbidden=no` | `final_inject_bad`: `hits_forbidden=yes`; sau fix (`final-clean-after-fix`): quay lại `no` | `artifacts/eval/final_clean.csv`, `artifacts/eval/final_inject_bad.csv`, `artifacts/eval/final_after_fix.csv` |
| quarantine stale HR + `hr_leave_no_stale_10d_annual` (halt) | `quarantine_records=4`, có 1 dòng `stale_hr_policy_effective_date` | Inject refund không làm lệch HR: `q_leave_version top1_doc_expected=yes` giữ ổn định | `artifacts/quarantine/quarantine_sprint1.csv`, `artifacts/eval/final_inject_bad.csv` |
| allowlist `doc_id` + dedupe text | Có 2 lỗi cố định trong mẫu: `unknown_doc_id=1`, `duplicate_chunk_text=1` | Sau inject vẫn giữ cùng ngưỡng quarantine, không để rò vào cleaned | `artifacts/quarantine/quarantine_sprint1.csv`, `artifacts/manifests/manifest_final-clean.json` |

**Rule chính (baseline + mở rộng):**

- Baseline: allowlist `doc_id`, chuẩn hoá ngày `effective_date`, quarantine HR cũ (`< 2026-01-01`), loại chunk thiếu text/ngày, dedupe chunk trùng, fix refund 14 -> 7.
- Mở rộng của nhóm: normalize whitespace trước khi hash chunk, quarantine marker `DRAFT/INTERNAL ONLY`, và validate định dạng `exported_at` để tránh timestamp bẩn đi vào publish.
- Expectation mở rộng: `no_placeholders` (halt) và `chunk_max_length_1000` (warn), bổ sung cho các expectation cốt lõi về refund stale, định dạng ngày ISO và version HR.

**Ví dụ 1 lần expectation fail (nếu có) và cách xử lý:**

Trong run `final-inject-bad`, nhóm chủ đích dùng cờ `--no-refund-fix --skip-validate` để giữ lại chunk refund stale. Theo logic expectation, rule `refund_no_stale_14d_window` thuộc mức halt nên đây là trạng thái fail có kiểm soát phục vụ Sprint 3. Hệ quả thể hiện trực tiếp ở eval: `q_refund_window` đổi từ `hits_forbidden=no` sang `yes`. Cách xử lý là chạy lại pipeline chuẩn (`final-clean-after-fix`) để bật lại refund fix và xuất bản snapshot sạch; kết quả `hits_forbidden` trở về `no`.

---

## 3. Before / after ảnh hưởng retrieval hoặc agent (200–250 từ)

> Bắt buộc: inject corruption (Sprint 3) — mô tả + dẫn `artifacts/eval/…` hoặc log.

**Kịch bản inject:**

Kịch bản inject được thực hiện bằng lệnh:

`python etl_pipeline.py run --run-id final-inject-bad --no-refund-fix --skip-validate`

Mục tiêu của inject không phải làm hỏng toàn bộ pipeline mà tạo một trường hợp sai lệch có chủ đích ở policy refund để quan sát độ nhạy của retrieval observability. Cờ `--no-refund-fix` giữ nguyên câu stale chứa cửa sổ 14 ngày làm việc; cờ `--skip-validate` cho phép pipeline vẫn embed để tạo trạng thái xấu trong index phục vụ so sánh before/after.

**Kết quả định lượng (từ CSV / bảng):**

So sánh trên 4 câu hỏi retrieval (`top_k_used=3`) cho ba run:

| Scenario | contains_expected | hits_forbidden | Nhận xét |
|----------|-------------------|----------------|----------|
| `final-clean` | 4/4 = yes | 0/4 = no | Baseline sạch, không dính context stale |
| `final-inject-bad` | 4/4 = yes | 1/4 = yes vi phạm (ở `q_refund_window`) | Câu trả lời vẫn có thể đúng bề mặt nhưng top-k đã nhiễm chunk stale |
| `final-clean-after-fix` | 4/4 = yes | 0/4 = no | Chạy lại clean pipeline khôi phục trạng thái tốt |

Điểm quan trọng của observability là không chỉ nhìn `contains_expected`, mà phải nhìn thêm `hits_forbidden` trên toàn bộ top-k. Trong inject run, `q_refund_window` vẫn có `contains_expected=yes` và `top1_doc_id=policy_refund_v4`, nhưng `hits_forbidden=yes` cho thấy index chứa ngữ cảnh cấm (14 ngày) ở các chunk còn lại. Sau fix, cùng câu này quay về `hits_forbidden=no`, chứng minh clean + publish boundary hoạt động đúng.

Với câu `q_leave_version`, cả ba run đều giữ `top1_doc_expected=yes`, xác nhận phần versioning HR không bị ảnh hưởng khi inject chỉ nhắm vào refund window.

---

## 4. Freshness & monitoring (100–150 từ)

> SLA bạn chọn, ý nghĩa PASS/WARN/FAIL trên manifest mẫu.

Nhóm giữ SLA freshness theo contract ở mức 24 giờ, đo tại boundary publish. Trên cả ba manifest final (`final-clean`, `final-inject-bad`, `final-clean-after-fix`), trường `latest_exported_at` đều là `2026-04-10T08:00:00`, trong khi thời điểm chạy ngày 15/04/2026 nên age xấp xỉ 120 giờ. Vì age > SLA, trạng thái freshness là FAIL và đây là kết quả hợp lý với bộ dữ liệu lab dạng snapshot cũ.

Theo thiết kế monitor trong pipeline: PASS khi age <= SLA, WARN khi thiếu timestamp hợp lệ trong manifest, và FAIL khi vượt SLA. Với bối cảnh lab, FAIL này là tín hiệu nghiệp vụ (nguồn cũ), không phải lỗi runtime. Trong vận hành thật, đội monitor sẽ phản ứng bằng cách yêu cầu refresh export upstream hoặc tạm gắn cờ “data stale” trước khi publish cho agent.

---

## 5. Liên hệ Day 09 (50–100 từ)

> Dữ liệu sau embed có phục vụ lại multi-agent Day 09 không? Nếu có, mô tả tích hợp; nếu không, giải thích vì sao tách collection.

Pipeline Day 10 giữ cùng domain tài liệu CS + IT Helpdesk như Day 09, nhưng xuất bản vào collection `day10_kb` để tách môi trường thử nghiệm observability khỏi index production-like trước đó. Sau khi xác nhận run sạch (`final-clean-after-fix`), nhóm có thể trỏ retrieval worker Day 09 sang collection này hoặc đồng bộ lại dữ liệu sạch vào luồng Day 09 để tránh agent đọc nhầm chunk stale.

---

## 6. Rủi ro còn lại & việc chưa làm

- Chưa chạy `grading_run.py` vì hiện chưa có file `data/grading_questions.json` trong repo local để tạo `artifacts/eval/grading_run.jsonl`.
- `artifacts/logs/` chưa được commit kèm report; hiện bằng chứng chính tập trung ở manifest + eval CSV.
- Chưa triển khai freshness 2 boundary (`ingest` và `publish`), nên chưa đạt phần bonus/Distinction liên quan monitoring nâng cao.
- Cần hoàn thiện đồng bộ các file docs còn placeholder (đặc biệt `docs/runbook.md` và `docs/pipeline_architecture.md`) để khớp hoàn toàn với nội dung report nhóm.
