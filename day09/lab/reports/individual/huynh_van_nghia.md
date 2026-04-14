# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Huỳnh Văn Nghĩa  
**Vai trò trong nhóm:** Trace & Docs Owner  
**Ngày nộp:** 14/04/2026  
**Độ dài:** ~760 từ

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

Tôi phụ trách phần trace, đánh giá và tài liệu cuối sprint. File kỹ thuật chính tôi làm là `eval_trace.py`, tập trung vào các hàm `run_test_questions()`, `analyze_traces()`, `compare_single_vs_multi()` và phần export trong `run_grading_questions()`. Tôi cũng hoàn thiện `docs/system_architecture.md`, `docs/routing_decisions.md`, `docs/single_vs_multi_comparison.md`, và đồng bộ số liệu vào `reports/group_report.md`.

Công việc của tôi kết nối trực tiếp với Supervisor Owner, Worker Owner và MCP Owner vì tôi dùng trace để xác nhận route đúng intent, worker sequence đúng thiết kế, và MCP path có ổn định hay không. Bằng chứng rõ nhất là batch 15 trace mới nhất: `run_20260414_172337` (HITL), `run_20260414_172348` (retrieval route), `run_20260414_172359` và `run_20260414_172410` (policy route có gọi MCP đầy đủ).

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** Tôi tách rõ hai lớp metric MCP trong eval: “attempted usage” và “valid usage”, thay vì chỉ một chỉ số mcp_usage tổng quát.

Nếu chỉ nhìn `mcp_usage_rate = 3/15`, nhóm dễ hiểu rằng MCP đã hoạt động ở 3 câu. Tôi bổ sung thêm `mcp_valid_usage_rate` để kiểm tra dữ liệu tool có thật sự usable hay không, tránh hiểu sai chất lượng integration.

Trade-off là bảng metric dài hơn, nhưng đổi lại debug chính xác hơn: lỗi nằm ở integration/runtime của policy + MCP, không phải supervisor route.

**Bằng chứng từ code/trace:**

```python
mcp_tools = t.get("mcp_tools_used") or []
if mcp_tools:
    mcp_calls += 1

valid_tool_calls = [
    tool for tool in mcp_tools
    if isinstance(tool, dict) and tool.get("tool")
]
if valid_tool_calls:
    mcp_valid_calls += 1
```

Kết quả trong `artifacts/eval_report.json` của batch mới nhất: `mcp_usage_rate = 3/15 (20%)` và `mcp_valid_usage_rate = 3/15 (20%)`.

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** Dữ liệu null trong `mcp_tools_used` từng làm phần export grading/eval có nguy cơ truy cập `.get()` trên đối tượng không hợp lệ.

**Symptom (pipeline làm gì sai?):**
Ở các run cũ như `run_20260414_164243` (q13) và `run_20260414_164254` (q15), `policy_result` báo lỗi `'NoneType' object has no attribute 'get'` và `mcp_tools_used` chứa `null`. Nếu eval export giả định mọi phần tử là dict, summary dễ sai hoặc gãy ở bước trích tool name.

**Root cause:**
Trong `eval_trace.py`, logic cũ đọc `mcp_tools_used` chưa có lớp lọc kiểu dữ liệu trước khi lấy field.

**Cách sửa:**
Tôi thêm bước chuẩn hóa đầu vào: chỉ giữ phần tử kiểu dict và có khóa `tool` trước khi ghi vào record grading. Tôi cũng sửa cách tính confidence/latency sang kiểm tra `is not None` để không bỏ qua giá trị hợp lệ bằng 0.

**Bằng chứng trước/sau:**
- Trước: có các trace policy chứa null record ở `mcp_tools_used`, gây rủi ro runtime.
- Sau: batch mới (`run_20260414_172359`, `run_20260414_172410`) ghi đầy đủ `check_access_permission` + `get_ticket_info` với input/output rõ ràng; `mcp_valid_usage_rate` tăng lên `3/15`.

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

Điểm tôi làm tốt nhất là giữ được tính “evidence-first” cho toàn bộ tài liệu: mọi nhận định trong docs đều bám trace thật và số liệu thật, tránh viết theo cảm giác. Việc này giúp report nhóm thống nhất với code và artifacts, hạn chế rủi ro bị trừ điểm vì mâu thuẫn số liệu.

Điểm tôi làm chưa tốt là hiện chưa có bộ chấm raw tự động theo rubric nên vẫn chưa quy đổi được điểm tổng theo thang 96 từ grading_run. Ngoài ra, nhánh policy cho đơn đặt trước 01/02/2026 vẫn bị phụ thuộc vào việc thiếu tài liệu policy v3 trong KB.

Nhóm phụ thuộc vào tôi ở phần đóng gói kết quả cuối: nếu trace/eval/docs không khớp nhau thì khó nộp. Tôi phụ thuộc vào MCP Owner và Worker Owner ở phần ổn định payload tool để nâng chất lượng answer ở các câu policy + incident.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Tôi sẽ bổ sung tài liệu policy v3 vào KB và thêm rule tách riêng case đơn trước/sau 01/02/2026. Lý do là ở grading `gq02`, hệ thống route đúng nhưng vẫn phải trả lời thận trọng vì thiếu nguồn v3 để kết luận dứt điểm. Nếu bổ sung đúng nguồn, tôi kỳ vọng tăng quality ở nhóm câu temporal-policy mà không cần nới prompt theo hướng đoán.
