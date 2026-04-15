# Quality report — Lab Day 10 (nhóm)

**run_id:** final-clean / final-inject-bad / final-clean-after-fix  
**Ngày:** 15/04/2026

---

## 1. Tóm tắt số liệu

| Chỉ số | Trước (final-clean) | Sau inject (final-inject-bad) | Ghi chú |
|--------|----------------------|-------------------------------|---------|
| raw_records | 10 | 10 | Cùng một file raw export |
| cleaned_records | 6 | 6 | Inject giữ nguyên số record đã clean |
| quarantine_records | 4 | 4 | Các lỗi quarantine không đổi trên bộ mẫu |
| Expectation halt? | Không | Có | `refund_no_stale_14d_window` fail khi bỏ refund fix |

Artifact chính:
- `artifacts/manifests/manifest_final-clean.json`
- `artifacts/manifests/manifest_final-inject-bad.json`
- `artifacts/manifests/manifest_final-clean-after-fix.json`
- `artifacts/eval/final_clean.csv`
- `artifacts/eval/final_inject_bad.csv`
- `artifacts/eval/final_after_fix.csv`

---

## 2. Before / after retrieval (bắt buộc)

> Dẫn chiếu tới `artifacts/eval/final_clean.csv`, `artifacts/eval/final_inject_bad.csv`, và `artifacts/eval/final_after_fix.csv`.

**Câu hỏi then chốt:** refund window (`q_refund_window`)

**Trước - final_clean.csv**  
`contains_expected=yes`, `hits_forbidden=no`, `top1_doc_id=policy_refund_v4`

**Sau inject - final_inject_bad.csv**  
`contains_expected=yes`, `hits_forbidden=yes`, `top1_doc_id=policy_refund_v4`

**Sau fix - final_after_fix.csv**  
`contains_expected=yes`, `hits_forbidden=no`, `top1_doc_id=policy_refund_v4`

Diễn giải:
- Bản clean trả về đúng context “7 ngày làm việc” và không chạm chunk stale trong toàn bộ top-k.
- Khi chạy `--no-refund-fix --skip-validate`, expectation refund fail nhưng pipeline vẫn embed để phục vụ demo corruption.
- Sau inject, `hits_forbidden=yes` chứng minh top-k retrieval đã dính chunk stale “14 ngày”.
- Sau khi rerun clean pipeline, `hits_forbidden` quay lại `no`, xác nhận clean rule đã khôi phục publish snapshot đúng.

**Merit (khuyến nghị):** versioning HR — `q_leave_version`

**Trước - final_clean.csv**  
`contains_expected=yes`, `hits_forbidden=no`, `top1_doc_expected=yes`

**Sau inject - final_inject_bad.csv**  
`contains_expected=yes`, `hits_forbidden=no`, `top1_doc_expected=yes`

**Sau fix - final_after_fix.csv**  
`contains_expected=yes`, `hits_forbidden=no`, `top1_doc_expected=yes`

Diễn giải:
- Kịch bản inject của Sprint 3 chỉ tác động lên refund window, nên câu HR giữ ổn định.
- Đây vẫn là một bằng chứng tốt cho thấy pipeline đang giữ đúng version HR 2026 và không kéo lại chunk cũ “10 ngày phép năm”.

---

## 3. Freshness & monitor

Kết quả `freshness_check` của cả ba run đều là `FAIL`.

Chi tiết:
- `latest_exported_at = 2026-04-10T08:00:00`
- `sla_hours = 24`
- Ở thời điểm chạy ngày 15/04/2026, dữ liệu mẫu đã vượt SLA khoảng 120 giờ

Giải thích:
- Đây là hành vi hợp lý với bộ dữ liệu lab, vì raw CSV được thiết kế như một snapshot cũ để buộc nhóm phải quan sát freshness thay vì chỉ nhìn output retrieval.
- Nhóm giữ nguyên SLA 24 giờ ở mức `publish`.
- Trong runbook cần nêu rõ rằng `FAIL` ở đây phản ánh dữ liệu nguồn cũ, không phải lỗi kỹ thuật của pipeline runtime.

---

## 4. Corruption inject (Sprint 3)

Kịch bản inject:
- Chạy `python etl_pipeline.py run --run-id final-inject-bad --no-refund-fix --skip-validate`
- Cờ `--no-refund-fix` giữ nguyên chunk stale “14 ngày làm việc”
- Cờ `--skip-validate` cho phép pipeline tiếp tục embed dù expectation halt đã fail

Cách phát hiện:
- Log có dòng `expectation[refund_no_stale_14d_window] FAIL (halt) :: violations=1`
- Eval retrieval đổi từ `hits_forbidden=no` sang `hits_forbidden=yes` ở `q_refund_window`
- Sau khi rerun clean pipeline, chỉ số này quay về `no`

Ghi chú vận hành:
- Khi chạy trên Windows console mặc định, phần log chứa ký tự `→` từng gây `UnicodeEncodeError`.
- Run Sprint 3 được ổn định bằng cách đặt `PYTHONIOENCODING=utf-8` trước khi chạy lệnh inject/fix.

---

## 5. Hạn chế & việc chưa làm

- Hiện đã có `grading_questions.json` và `grading_run.jsonl`; phần tiếp theo nên mở rộng grading beyond keyword-based hoặc thêm bộ slice lớn hơn để tăng độ tin cậy của eval.
- Chưa mở rộng eval beyond baseline; hiện mới dùng bộ retrieval keyword-based có sẵn.
- Chưa có đo freshness ở 2 boundary (`ingest` + `publish`), nên chưa chạm bonus đó.
- Cần cập nhật `reports/group_report.md` để copy các số liệu run_id, log excerpt, và before/after CSV vào báo cáo nộp cuối.
