# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Khuất Văn Vương  
**Vai trò trong nhóm:** Supervisor Owner  
**Ngày nộp:** 14-04-2026
**Độ dài:** 500–800 từ

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

Trong Day 09, tôi phụ trách phần orchestration của hệ multi-agent ở file `graph.py`. Cụ thể, tôi thiết kế `AgentState`, viết `supervisor_node()` để phân tích task và route, cùng `route_decision()` + `post_retrieval_decision()` cho conditional edge. Tôi cũng triển khai `human_review_node()` để bật `hitl_triggered` cho câu rủi ro cao (đặc biệt task có mã `ERR-*`).

Tôi kết nối supervisor với các worker qua `retrieval_worker_node`, `policy_tool_worker_node`, `synthesis_worker_node`, và chuyển `build_graph()` sang `StateGraph` bằng LangGraph có fallback khi thiếu thư viện. Phần này là trục chính để các module worker và MCP chạy chung trong một pipeline thống nhất.

**Bằng chứng:** các function trong `day09/lab/graph.py` trong `supervisor_node`, `build_graph`, `post_retrieval_decision` và trace có `route_reason`/`workers_called` trong `artifacts/traces/*.json`.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** Tôi chọn routing rule-based theo tín hiệu từ câu hỏi keyword + risk flag ở supervisor. Khi kiểm thử grading, tôi đưa ra các phương án cải thiện ở điểm:

- Cải thiện retrieval khi thiếu vector db, thực hiện việc boost theo intent câu hỏi để ưu tiên đúng tài liệu, đa dạng, tự tăng top_k trong các câu multi-hop để retrive tốt hơn
- Cải thiện policy_tool và synthesis, xử lý negative cho các case và parse scope theo chuẩn ngày `dd/mm/yy để trả lời đúng trọng tâm.

Khi làm Sprint 1, tôi cân nhắc 2 cách là gọi LLM để classify route và luật routing rõ ràng bằng keyword. Tôi chọn cách rule routing vì yêu cầu `route_reason` phải khá cụ thể. Với rule-based, mỗi quyết định route đều giải thích được bằng tín hiệu kích hoạt như policy/access hoặc SLA/P1. Tôi cũng thêm flag `needs_tool` và `choose MCP=yes/no` để trace thể hiện rõ quyết định có đi qua tool layer.

**Bằng chứng từ trace/code:**

```text
run_20260414_142110_474286.json
route_reason: policy/access signal detected: access, level 2 -> route policy_tool_worker (prefer MCP) | risk_high signals: emergency, 2am | choose MCP=yes
workers_called: ['retrieval_worker', 'policy_tool_worker', 'synthesis_worker']
```

Đây là case multi-hop, supervisor route đúng vào policy path và worker sequence khớp thiết kế.

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** Pipeline không abstain đúng cho câu dạng mã lỗi lạ `ERR-403-AUTH`, dù đã route vào nhánh human review.

**Symptom:** Trước khi sửa, cùng route_reason nhưng final answer vẫn kéo nội dung không liên quan từ tài liệu access control. Điều này có rủi ro bị trừ điểm ở câu abstain.

**Root cause:** Sau `human_review -> retrieval`, synthesis fallback vẫn lấy chunk gần nhất và “trả lời đại diện” thay vì kiểm tra xem mã lỗi đó có thật sự xuất hiện trong evidence hay không. Nói cách khác, supervisor route đúng nhưng tầng synthesis chưa có guard anti-hallucination cho unknown error code.

**Cách sửa:** Tôi thêm guard trong `workers/synthesis.py` ở `_rule_based_answer()`: nếu task match regex `ERR-*` nhưng không xuất hiện trong chunks thì trả lời abstain rõ ràng: “Không đủ thông tin trong tài liệu nội bộ…”.

**Bằng chứng trước/sau:**

- Trước: `run_20260414_113020_051110.json` trả về đoạn access control không liên quan (confidence 0.4).
- Sau: `run_20260414_142110_460571.json` trả về abstain đúng chuẩn cho `ERR-403-AUTH` (confidence 0.3), `workers_called` vẫn là `['human_review', 'retrieval_worker', 'synthesis_worker']`.

Việc này giúp pipeline an toàn hơn ở câu gq07 dạng anti-hallucination.

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

Điểm tôi làm tốt nhất là giữ được kiến trúc rõ ràng giữa supervisor và workers: supervisor chỉ route và quyết định luồng, không ôm domain logic. Nhờ vậy khi có bug, nhóm debug theo cây quyết định rõ ràng (route sai hay worker sai), thay vì mò trong một hàm monolith.

Điểm tôi làm chưa tốt là routing rule vẫn phụ thuộc keyword nên còn nhạy với câu phủ định hoặc câu diễn đạt lạ. Ví dụ case “không phải Flash Sale” ban đầu bị false positive cho policy exception; sau đó nhóm đã sửa.

Nhóm phụ thuộc vào tôi ở phần ổn định flow end-to-end: nếu `graph.py` chưa chốt edge và state schema thì pipeline không thể nộp trace chuẩn. Ngược lại, tôi phụ thuộc vào Worker Owner để policy/synthesis đủ grounded và MCP Owner để tool call có dữ liệu thật.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Nếu có thêm 2 giờ, tôi sẽ thay keyword routing bằng một supervisor classifier nhẹ (ví dụ model nhỏ hoặc rule + score) nhưng vẫn bắt buộc xuất `route_reason` theo format chuẩn key-value. Lý do: trace hiện có cho thấy route đúng đa số, nhưng vài case ngôn ngữ tự nhiên dài vẫn làm confidence thấp (ví dụ multi-hop ở `run_20260414_142110_474286.json`, confidence 0.35). Tôi muốn giảm lỗi biên mà vẫn giữ khả năng debug minh bạch.
