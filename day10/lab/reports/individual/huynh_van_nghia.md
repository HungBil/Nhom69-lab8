# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Huỳnh Văn Nghĩa  
**Vai trò:** Monitoring / Docs Owner  
**Ngày nộp:** 15/04/2026  
**Độ dài:** khoảng 520 từ

---

## 1. Phụ trách

Trong Lab Day 10, tôi phụ trách vai trò Monitoring / Docs Owner, tập trung vào hai nhóm việc: (1) xây dựng tài liệu vận hành để cả nhóm chạy pipeline nhất quán, và (2) theo dõi chất lượng publish thông qua manifest + eval artifact. Các file tôi phụ trách chính là `docs/runbook.md`, `docs/pipeline_architecture.md`, phối hợp cập nhật `reports/group_report.md` và đối chiếu `docs/quality_report.md` để số liệu khớp giữa tài liệu và artifact.

Tôi kết nối trực tiếp với bạn phụ trách Cleaning/Quality để xác nhận expectation nào là halt, đồng thời làm việc với bạn Embed Owner để kiểm tra kết quả before/after trên các file `artifacts/eval/final_clean.csv`, `artifacts/eval/final_inject_bad.csv`, `artifacts/eval/final_after_fix.csv`. Tôi cũng dùng các manifest `manifest_final-clean.json`, `manifest_final-inject-bad.json`, `manifest_final-clean-after-fix.json` để viết phần lineage và freshness trong report nhóm, đảm bảo có run_id và đường dẫn chứng cứ rõ ràng.

Bằng chứng đóng góp của tôi thể hiện qua việc điền đầy đủ nội dung vận hành trong `docs/runbook.md` và sơ đồ kiến trúc + ownership trong `docs/pipeline_architecture.md`, thay cho bản placeholder ban đầu.

---

## 2. Quyết định kỹ thuật

Quyết định kỹ thuật quan trọng nhất tôi đưa ra là coi freshness FAIL trong bộ dữ liệu lab là tín hiệu nghiệp vụ, không xem là lỗi runtime của pipeline. Lý do là trong các manifest final, `latest_exported_at` đều là `2026-04-10T08:00:00`, trong khi run diễn ra ngày 15/04/2026 với SLA 24 giờ. Nếu tôi đánh đồng freshness FAIL với lỗi hệ thống và “vá số liệu” để PASS giả thì sẽ làm sai mục tiêu observability của bài lab.

Vì vậy, trong runbook và group report, tôi đặt quy ước theo thứ tự debug: freshness/version trước, rồi mới đến expectation/eval. Tôi cũng thống nhất cách đọc quality evidence: không chỉ nhìn `contains_expected`, mà bắt buộc đọc thêm `hits_forbidden` trên toàn bộ top-k. Cách này giúp phát hiện trường hợp câu trả lời tưởng đúng nhưng context retrieval vẫn nhiễm chunk stale. Quyết định này giúp phần Monitoring có giá trị thực tế hơn và khớp yêu cầu SCORING về evidence before/after.

---

## 3. Sự cố / anomaly

Anomaly chính tôi xử lý là trường hợp retrieval bị nhiễm context stale sau inject. Triệu chứng là ở run `final-inject-bad`, câu `q_refund_window` vẫn có `contains_expected=yes` nhưng `hits_forbidden=yes`, tức là top-k đã chứa đoạn cấm liên quan “14 ngày làm việc”. Nếu chỉ nhìn top1 hoặc chỉ nhìn cột contains_expected thì rất dễ bỏ sót lỗi này.

Tôi phát hiện anomaly bằng cách so sánh ba scenario (`final-clean` -> `final-inject-bad` -> `final-clean-after-fix`) trên các file eval tương ứng. Sau đó, tôi yêu cầu rerun pipeline chuẩn (không dùng `--no-refund-fix`, không `--skip-validate`) để khôi phục snapshot sạch. Kết quả sau fix, `hits_forbidden` trở lại `no` cho câu refund, xác nhận clean rule đã hoạt động đúng ở publish boundary.

Ngoài ra, khi tổng hợp log vận hành, tôi ghi nhận thêm lỗi môi trường Windows có thể gặp `UnicodeEncodeError` khi in ký tự Unicode trong console, và đề xuất đặt `PYTHONIOENCODING=utf-8` trong runbook để tránh gián đoạn khi demo inject/fix.

---

## 4. Before/after

Hai dòng CSV then chốt tôi dùng làm evidence (cùng câu hỏi `q_refund_window`):

- Run `final-clean` từ `artifacts/eval/final_clean.csv`:
  `q_refund_window,...,contains_expected=yes,hits_forbidden=no,...`
- Run `final-inject-bad` từ `artifacts/eval/final_inject_bad.csv`:
  `q_refund_window,...,contains_expected=yes,hits_forbidden=yes,...`

Sau khi chạy lại run `final-clean-after-fix` (`artifacts/eval/final_after_fix.csv`), chỉ số quay về:
`q_refund_window,...,contains_expected=yes,hits_forbidden=no,...`

Chuỗi bằng chứng này cho thấy monitoring dựa trên `hits_forbidden` là hiệu quả để chứng minh dữ liệu tệ hơn khi inject và tốt hơn sau fix.

---

## 5. Cải tiến thêm 2 giờ

Nếu có thêm 2 giờ, tôi sẽ triển khai freshness theo 2 boundary (`ingest` và `publish`) thay vì chỉ một điểm đo từ manifest. Cụ thể, tôi sẽ thêm timestamp ingest riêng, ghi ra artifact log chuẩn hóa, và tạo bảng so sánh age theo từng boundary để tách rõ lỗi nguồn dữ liệu cũ với lỗi trễ xử lý pipeline. Việc này giúp cảnh báo sớm hơn và tăng cơ hội đạt bonus monitoring.
