# Báo Cáo Nhóm — Lab Day 09: Multi-Agent Orchestration

**Tên nhóm:** Nhom69  
**Thành viên:**
| Tên | Vai trò | Email |
|-----|---------|-------|
| Khuất Văn Vương | Supervisor Owner | 26ai.vuongkv@vinuni.edu.vn |
| Lưu Lương Vi Nhân | Worker Owner | 26ai.nhanllv@vinuni.edu.vn |
| Nguyễn Đông Hưng | MCP Owner | 26ai.hungnd2@vinuni.edu.vn |
| Huỳnh Văn Nghĩa | Trace & Docs Owner | 26ai.nghiahv@vinuni.edu.vn |

**Ngày nộp:** 14/04/2026  
**Repo:** [Nhom69-lab8](https://github.com/HungBil/Nhom69-lab8)

---

## 1. Kiến trúc nhóm đã xây dựng (150–200 từ)

**Hệ thống tổng quan:**
Nhóm xây pipeline Supervisor-Worker bằng LangGraph, gồm 1 supervisor và 3 worker: retrieval, policy_tool, synthesis. Supervisor chỉ route, không trả lời domain trực tiếp. Luồng chạy: supervisor phân tích câu hỏi -> retrieval lấy evidence -> nếu là policy/access thì chạy policy_tool -> synthesis sinh câu trả lời có citation và confidence. Các trường route_reason, workers_called, retrieved_sources, confidence, hitl_triggered được lưu vào trace JSON để debug. Hệ thống chạy ổn định 15/15 câu test không crash.

**Routing logic cốt lõi:**
Supervisor dùng rule-based keyword matching: nhóm policy/access route sang policy_tool_worker, nhóm SLA/ticket route sang retrieval_worker, mã lỗi ERR-xxx mơ hồ route qua human_review. Route reason luôn ghi cụ thể trong trace để debug.

**MCP tools đã tích hợp:**
- search_kb
- get_ticket_info
- check_access_permission

Ví dụ trace có MCP path: run_20260414_172359.json (q13) có history ghi gọi `check_access_permission` và `get_ticket_info`.

---

## 2. Quyết định kỹ thuật quan trọng nhất (200–250 từ)

**Quyết định:** Bắt buộc retrieval trước policy_tool cho policy route (retrieval-first policy flow).

**Bối cảnh vấn đề:**
Ban đầu nhóm thử route thẳng vào policy_tool cho câu hoàn tiền/cấp quyền để giảm bước. Nhưng khi test, policy_tool thiếu context ổn định và synthesis khó bám nguồn, nhất là câu có nhiều điều kiện.

**Các phương án đã cân nhắc:**

| Phương án | Ưu điểm | Nhược điểm |
|-----------|---------|-----------|
| Route thẳng policy_tool | Ít bước hơn, latency có thể thấp hơn | Dễ thiếu evidence chuẩn hóa, khó trace chain reasoning |
| Retrieval trước rồi policy_tool | Có evidence chung cho mọi nhánh, trace rõ | Tốn thêm 1 bước, latency tăng |

**Phương án đã chọn và lý do:**
Nhóm chọn retrieval-first để chuẩn hóa context đầu vào cho policy_tool và synthesis. Cách này giữ evidence nhất quán và giúp trace đọc dễ hơn vì workers_called có thứ tự ổn định: retrieval -> policy_tool -> synthesis.

**Bằng chứng từ trace/code:**
- Code: trong graph, route policy được map qua retrieval trước khi vào policy_tool.
- Trace: run_20260414_172353.json (q12) có workers_called = retrieval_worker -> policy_tool_worker -> synthesis_worker.

---

## 3. Kết quả grading questions (150–200 từ)

**Tổng điểm raw ước tính:** N/A / 96 (đã chạy đủ 10/10 grading questions nhưng chưa có script/rubric quy đổi raw tự động)

**Tình trạng chạy grading:**
- Đã tạo `artifacts/grading_run.jsonl` với 10 records.
- Phân phối route: retrieval 5/10, policy_tool 5/10.
- Avg confidence: 0.627; avg latency: 6546 ms.

**Câu pipeline xử lý tốt nhất:**
- ID: gq03 — route policy_tool_worker, workers_called đủ 3 bước, gọi được 2 MCP tools (`check_access_permission`, `get_ticket_info`), confidence 0.84.

**Câu pipeline fail hoặc partial:**
- ID: gq02 — route đúng policy_tool nhưng câu trả lời phải giữ mức thận trọng vì đơn đặt trước 01/02/2026 cần policy v3, trong KB hiện chỉ có policy v4.

**Câu gq07 (abstain):** Nhóm xử lý thế nào?
Hệ thống trả lời “không có thông tin mức phạt tài chính cụ thể trong tài liệu hiện có” và khuyến nghị kiểm tra thêm tài liệu hợp đồng/SLA commercial. Đây là abstain có kiểm soát, tránh bịa dữ liệu.

**Câu gq09 (multi-hop khó nhất):** Trace ghi được 2 workers không? Kết quả thế nào?
Có. Trace ghi đủ chuỗi retrieval -> policy_tool -> synthesis và gọi 2 MCP tools; câu trả lời bao phủ cả SLA notification lẫn điều kiện cấp Level 2 emergency access, confidence 0.82.

---

## 4. So sánh Day 08 vs Day 09 — Điều nhóm quan sát được (150–200 từ)

**Metric thay đổi rõ nhất (có số liệu):**
Theo batch 15 trace, Day 09 có avg_confidence = 0.619, avg_latency = 6247 ms, routing retrieval 8/15 và policy_tool 7/15, mcp_usage 3/15, mcp_valid_usage 3/15, hitl 1/15. Proxy Day 08 có avg_confidence xấp xỉ 0.96 và không có routing trace. Chất lượng vẫn thấp hơn baseline proxy nhưng đã cải thiện so với run trước.

**Trường hợp multi-agent KHÔNG giúp ích hoặc làm chậm hệ thống:**
Với câu đơn giản chỉ cần một fact, multi-agent thêm bước điều phối nên latency cao hơn single-agent.

---

## 5. Phân công và đánh giá nhóm (100–150 từ)

**Phân công thực tế:**

| Thành viên | Phần đã làm | Sprint |
|------------|-------------|--------|
| Khuất Văn Vương | Supervisor routing + graph flow | 1 |
| Lưu Lương Vi Nhân | retrieval/policy/synthesis workers | 2 |
| Nguyễn Đông Hưng | MCP server tools + dispatch | 3 |
| Huỳnh Văn Nghĩa | eval_trace + docs + checklist/report | 4 |

**Điều nhóm làm tốt:**
Nhóm phối hợp tốt giữa code và tài liệu: thay đổi routing đều có trace evidence, docs bám output thật, pipeline chạy ổn định 15/15 câu test.

**Điều nhóm làm chưa tốt hoặc gặp vấn đề về phối hợp:**
Policy cho đơn đặt trước 01/02/2026 còn thiếu tài liệu v3 trong KB, nên một số câu phải trả lời thận trọng thay vì kết luận dứt điểm; metadata thành viên/email cũng chưa đủ.

---

## 6. Nếu có thêm 1 ngày, nhóm sẽ làm gì? (50–100 từ)

Nhóm sẽ ưu tiên 2 việc: (1) bổ sung tài liệu policy v3 vào KB và cập nhật rule cho case đơn trước 01/02/2026 để giảm câu trả lời “không thể kết luận chắc”; (2) bổ sung bộ đánh giá đúng-sai tự động theo expected answer/rubric cho grading_run thay vì chỉ dựa confidence proxy.
