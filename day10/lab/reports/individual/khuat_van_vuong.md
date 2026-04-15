# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Khuất Văn Vương
**Vai trò:** Ingestion Owner  
**Ngày nộp:** 2026-04-15
**Độ dài:** **400–650 từ**

---

## 1. Phụ trách

Tôi phụ trách vai trò Ingestion Owner, tập trung vào luồng đọc dữ liệu raw, chuẩn hóa điểm vào pipeline và ghi vết observability theo run. Tôi làm việc chủ yếu trong `etl_pipeline.py`, ở các bước: nhận `--run-id`, đọc `data/raw/policy_export_dirty.csv`, đếm `raw_records`, tạo artifact theo run, và ghi log key-value để nhóm dễ đối soát. Kết quả run đầu tiên là `run_id=sprint1`, `raw_records=10`, `cleaned_records=6`, `quarantine_records=4` (trong `artifacts/logs/run_sprint1.log`). Tôi cũng xuất manifest cho monitoring và freshness; `artifacts/manifests/manifest_sprint1.json` chứa `raw_path`, `latest_exported_at`, `no_refund_fix`, `skipped_validate`, `chroma_collection`.

Về phối hợp, tôi bàn giao dữ liệu đã ingest cho bạn Cleaning và Quality Owner xử lý rule và expectation; sau đó truyền `cleaned_csv` + `run_id` cho bạn Embed để đảm bảo upsert idempotent; cuối cùng gửi manifest cho bạn Monitoring Owner viết runbook freshness.

---

## 2. Quyết định kỹ thuật

Quyết định kỹ thuật quan trọng nhất của tôi là chọn cơ chế định danh run theo `run_id` và chuẩn hóa đường dẫn artifact theo run, thay vì ghi đè một file log duy nhất. Cụ thể, trong `cmd_run()` của `etl_pipeline.py`, khi người dùng không truyền `--run-id` thì hệ thống tự sinh timestamp UTC (`%Y-%m-%dT%H-%MZ`), còn khi truyền thủ công (ví dụ `sprint1`, `inject-bad`, `clean-good`) thì pipeline giữ nguyên để hỗ trợ so sánh scenario. Cách này giúp truy xuất lineage rõ ràng: một run tương ứng một cặp log/manifest/quarantine/cleaned.

Lý do tôi chọn thiết kế này là để giảm tranh cãi khi debug: mọi metric đều truy ngược được về đúng lần chạy, đúng input và đúng cờ cấu hình. Ví dụ `manifest_clean-good.json` thể hiện `no_refund_fix=false`, còn `manifest_inject-bad.json` thể hiện `no_refund_fix=true` và `skipped_validate=true`. Đây là nền tảng để các bạn còn lại chứng minh before/after trong báo cáo chất lượng mà không phải dựa vào mô tả miệng.

---

## 3. Sự cố / anomaly

Anomaly tôi xử lý trong sprint này là tình huống “expectation đã FAIL nhưng pipeline vẫn cần chạy để demo inject corruption có chủ đích”. Ở run `inject-bad`, log ghi rõ `expectation[refund_no_stale_14d_window] FAIL (halt) :: violations=1`. Nếu chạy mặc định, pipeline sẽ dừng và không tạo được bằng chứng cho bài so sánh trước/sau.

Cách xử lý của tôi là dùng đúng cơ chế điều khiển đã có trong entrypoint: `--skip-validate` kết hợp `--no-refund-fix`. Khi chạy `python etl_pipeline.py run --run-id inject-bad --no-refund-fix --skip-validate`, log ghi `WARN: expectation failed but --skip-validate → tiếp tục embed`, sau đó vẫn tạo được `manifest_inject-bad.json` và cập nhật index. Nhờ vậy nhóm có dữ liệu thực để chứng minh tác động của dữ liệu xấu, thay vì chỉ mô phỏng trên lý thuyết.

---

## 4. Before/after

- Trước khi fix (inject): `artifacts/eval/after_inject_bad.csv` có dòng `q_refund_window` với `contains_expected=yes` nhưng `hits_forbidden=yes`.
- Sau khi fix (clean): `artifacts/eval/before_after_eval.csv` cùng câu `q_refund_window` có `contains_expected=yes` và `hits_forbidden=no`.

Hai dòng này cho thấy dù top-1 vẫn trả lời đúng “7 ngày”, ở kịch bản inject thì top-k còn lẫn context cấm (stale window 14 ngày). Sau khi quay lại luồng chuẩn `clean-good`, tín hiệu forbidden biến mất. Các câu `q_p1_sla`, `q_lockout`, `q_leave_version` vẫn giữ trạng thái tốt (`yes/no`, và `top1_doc_expected=yes` ở `q_leave_version`), nên thay đổi tập trung đúng vào policy refund.

---

## 5. Cải tiến thêm 2 giờ

Nếu có thêm 2 giờ, tôi sẽ thêm một lớp “ingestion guardrail” kiểm tra schema và kiểu dữ liệu ngay sau bước đọc CSV (ví dụ bắt buộc các cột `doc_id`, `chunk_id`, `effective_date`, `exported_at` tồn tại), rồi ghi riêng metric `schema_error_count` vào log/manifest. Việc này giúp phát hiện sớm lỗi input trước khi tốn thời gian chạy cleaning và embed.
