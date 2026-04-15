# Runbook — Lab Day 10 (incident tối giản)

---

## Symptom

Các triệu chứng chính nhóm gặp trong lab:

- Agent/retrieval trả lời liên quan refund có dấu hiệu stale (xuất hiện ngữ cảnh 14 ngày thay vì 7 ngày làm việc).
- CSV eval cho thấy `contains_expected=yes` nhưng `hits_forbidden=yes` ở `q_refund_window`.
- Freshness check trả về FAIL vì dữ liệu export đã quá SLA.
- Một số run inject có expectation halt fail do chủ đích tắt fix (`--no-refund-fix`).

---

## Detection

Nguồn phát hiện sự cố theo thứ tự ưu tiên:

1. Freshness monitor từ manifest:
	- PASS: dữ liệu trong SLA.
	- WARN: thiếu timestamp hợp lệ.
	- FAIL: vượt SLA (nguồn stale).
2. Expectation suite trong pipeline log:
	- Ví dụ: `expectation[refund_no_stale_14d_window] FAIL (halt)`.
3. Retrieval eval CSV:
	- Ưu tiên đọc `hits_forbidden` trên toàn top-k để phát hiện context sai nhưng câu trả lời vẫn trông đúng.

---

## Diagnosis

| Bước | Việc làm | Kết quả mong đợi |
|------|----------|------------------|
| 1 | Kiểm tra manifest mới nhất trong `artifacts/manifests/manifest_<run_id>.json` | Có `run_id`, `raw_records`, `cleaned_records`, `quarantine_records`, `latest_exported_at` |
| 2 | Xác nhận cờ vận hành trong manifest (`no_refund_fix`, `skipped_validate`) | Biết run đang ở mode clean hay inject |
| 3 | Mở `artifacts/quarantine/quarantine_<run_id>.csv` để đọc `reason` | Xác định lỗi nguồn (unknown_doc_id, stale_hr_policy, missing_effective_date, duplicate_chunk_text, ...) |
| 4 | Mở `artifacts/cleaned/cleaned_<run_id>.csv` | Xác nhận chunk refund đã được clean 14 -> 7 hay chưa |
| 5 | Chạy `python eval_retrieval.py --out artifacts/eval/<scenario>.csv` | Đối chiếu `contains_expected`, `hits_forbidden`, `top1_doc_expected` |
| 6 | Nếu cần, so sánh với baseline `final_clean.csv` | Khoanh vùng hồi quy do clean rule hay do source mới |

---

## Mitigation

Luồng xử lý nhanh theo từng loại sự cố:

1. Sự cố stale refund context (`hits_forbidden=yes`):

```bash
python etl_pipeline.py run --run-id recover-clean
python eval_retrieval.py --out artifacts/eval/recover_clean.csv
```

Kỳ vọng: `q_refund_window` quay lại `hits_forbidden=no`.

2. Sự cố freshness FAIL (nguồn quá cũ):

- Đánh dấu trạng thái dữ liệu stale trong báo cáo/monitor.
- Yêu cầu upstream xuất snapshot mới, sau đó rerun pipeline chuẩn.
- Không sửa số liệu để PASS giả nếu không có bản export mới.

3. Sự cố expectation halt chặn publish:

- Chỉ dùng `--skip-validate` trong inject demo có kiểm soát.
- Với run phục vụ nộp/chạy thật, bắt buộc rerun không cờ skip để đảm bảo quality gate.

4. Lỗi terminal encoding khi in ký tự Unicode:

```powershell
$env:PYTHONIOENCODING="utf-8"
python etl_pipeline.py run --run-id recover-clean
```

---

## Prevention

Biện pháp phòng ngừa cho các sprint sau:

- Giữ strict rule: không publish nếu có expectation halt fail (trừ inject demo có ghi chú).
- Đặt checklist trước publish: manifest hợp lệ, quarantine được review, eval không có `hits_forbidden=yes` cho câu trọng yếu.
- Mở rộng freshness thành 2 boundary (`ingest` và `publish`) để phát hiện drift sớm hơn.
- Commit đầy đủ artifact tối thiểu cho mỗi run chính: manifest, eval CSV, log, quarantine.
- Gán ownership rõ: Monitoring/Docs Owner chịu trách nhiệm trạng thái freshness + runbook; Cleaning Owner chịu trách nhiệm expectation/rule hồi quy.
