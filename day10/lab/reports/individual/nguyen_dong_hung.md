# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Nguyễn Đông Hưng  
**MSSV:** 2A202600392  
**Vai trò:** Embed & Eval Owner / Sprint 3 Owner  
**Ngày nộp:** 15/04/2026  
**Độ dài:** khoảng 560 từ

---

## 1. Tôi phụ trách phần nào?

Trong Lab Day 10, tôi phụ trách phần Embed & Eval, đồng thời là người chính xử lý Sprint 3. Công việc của tôi tập trung vào việc đưa dữ liệu đã qua clean vào vector store, kiểm tra tính idempotent của publish boundary, rồi tạo bằng chứng before/after khi dữ liệu xấu được inject vào hệ thống. Các file tôi làm việc trực tiếp nhiều nhất là `etl_pipeline.py`, `eval_retrieval.py`, `docs/quality_report.md`, cùng nhóm artifact trong `artifacts/eval/` và `artifacts/manifests/`.

Ở phần embed, tôi theo dõi collection ChromaDB `day10_kb` và dùng các run như `final-clean`, `final-inject-bad`, `final-clean-after-fix` để chứng minh cùng một pipeline có thể đưa index từ trạng thái an toàn sang trạng thái rủi ro, rồi phục hồi lại. Ở phần eval, tôi sử dụng bộ câu hỏi retrieval có sẵn để kiểm tra không chỉ câu trả lời mong đợi mà cả tín hiệu stale context thông qua cột `hits_forbidden`. Đây là phần quan trọng nhất của Sprint 3 vì bài lab yêu cầu phải chứng minh được dữ liệu xấu làm retrieval tệ đi như thế nào.

**Bằng chứng:** `etl_pipeline.py`, `eval_retrieval.py`, `docs/quality_report.md`, `artifacts/eval/final_clean.csv`, `artifacts/eval/final_inject_bad.csv`, `artifacts/eval/final_after_fix.csv`.

---

## 2. Một quyết định kỹ thuật

Quyết định kỹ thuật quan trọng nhất của tôi là coi ChromaDB như “snapshot publish boundary”, chứ không chỉ là nơi tạm chứa embedding. Điều đó có nghĩa là evidence quality phải được đo trên collection thực đang serve retrieval, không được chỉ nhìn cleaned CSV rồi kết luận. Vì lý do đó, tôi bám sát cách pipeline đang làm trong `etl_pipeline.py`: upsert theo `chunk_id` và prune các id không còn trong cleaned output.

Cách tiếp cận này giúp tránh một lỗi rất phổ biến trong hệ thống AI: file CSV đã sạch nhưng vector store vẫn còn dữ liệu cũ. Nếu chỉ kiểm tra cleaned CSV thì nhóm có thể tưởng pipeline đã đúng, trong khi top-k retrieval vẫn bị nhiễm chunk stale từ các run trước. Việc gắn Sprint 3 vào ChromaDB khiến phần before/after có giá trị thật: khi dữ liệu xấu đi vào publish boundary thì eval mới nhìn thấy được `hits_forbidden=yes`, và khi dữ liệu sạch được publish lại thì chỉ số này mới về `no`.

Tôi ủng hộ prune vector id không còn trong batch để tránh top-k còn chunk “14 ngày” sau inject.

---

## 3. Một lỗi hoặc anomaly đã xử lý

Anomaly đáng chú ý nhất tôi gặp là ở run inject. Theo thiết kế bài lab, khi chạy:

`python etl_pipeline.py run --run-id final-inject-bad --no-refund-fix --skip-validate`

expectation `refund_no_stale_14d_window` phải fail, nhưng pipeline vẫn tiếp tục embed để phục vụ demo corruption có chủ đích. Tuy nhiên trên môi trường Windows console, dòng log chứa ký tự Unicode `→` trong cảnh báo `--skip-validate → tiếp tục embed` từng gây `UnicodeEncodeError`, làm run inject bị dừng giữa chừng.

Tôi xử lý bằng cách đặt `PYTHONIOENCODING=utf-8` trước khi chạy các lệnh inject và rerun clean. Sau khi sửa cách chạy, pipeline đã ghi đủ log:
- `expectation[refund_no_stale_14d_window] FAIL (halt) :: violations=1`
- `WARN: expectation failed but --skip-validate ...`
- `PIPELINE_OK`

Nhờ vậy, nhóm có thể giữ đúng kịch bản Sprint 3: cố ý để lỗi lọt qua validation, publish vào ChromaDB, rồi đo tác động thực trên retrieval thay vì dừng ở mức lý thuyết.

---

## 4. Bằng chứng trước / sau

Bằng chứng then chốt tôi dùng là câu `q_refund_window` trong các file eval:

- `artifacts/eval/final_clean.csv`  
  `contains_expected=yes`, `hits_forbidden=no`

- `artifacts/eval/final_inject_bad.csv`  
  `contains_expected=yes`, `hits_forbidden=yes`

- `artifacts/eval/final_after_fix.csv`  
  `contains_expected=yes`, `hits_forbidden=no`

Điều này cho thấy ở bản sạch, retrieval vừa đúng đáp án vừa không dính stale chunk. Sau khi inject lỗi bằng cách bỏ refund fix, top-k retrieval vẫn còn lấy trúng context cấm “14 ngày”, nên `hits_forbidden` chuyển sang `yes`. Sau khi rerun pipeline chuẩn, collection được khôi phục và chỉ số quay lại `no`.

Ngoài ra, tôi cũng dùng `q_leave_version` như một evidence bổ sung: ở cả `final_clean.csv`, `final_inject_bad.csv` và `final_after_fix.csv`, câu này đều giữ `contains_expected=yes`, `hits_forbidden=no`, `top1_doc_expected=yes`. Điều đó chứng minh kịch bản inject của Sprint 3 tập trung đúng vào refund policy chứ không làm hỏng toàn bộ hệ thống retrieval.

---

## 5. Cải tiến tiếp theo

Nếu có thêm 2 giờ, tôi sẽ mở rộng eval từ bộ retrieval keyword-based sang một bộ slice lớn hơn để tăng sức thuyết phục. Hiện đã có `grading_questions.json` và `grading_run.jsonl`; bước tiếp theo hợp lý là bổ sung publish alias hoặc cơ chế blue/green index để tách rõ giữa “candidate index” và “serving index”, giúp giảm rủi ro khi rerun hoặc backfill trên vector store.
