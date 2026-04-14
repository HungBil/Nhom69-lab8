# Routing Decisions Log — Lab Day 09

**Nhóm:** Nhom69  
**Ngày:** 14/04/2026

> **Hướng dẫn:** Ghi lại ít nhất **3 quyết định routing** thực tế từ trace của nhóm.
> Không ghi giả định — phải từ trace thật (`artifacts/traces/`).
> 
> Mỗi entry phải có: task đầu vào → worker được chọn → route_reason → kết quả thực tế.

---

## Routing Decision #1

**Trace ID:** `run_20260414_172410` (q15)

**Task đầu vào:**
> Ticket P1 lúc 2am. Cần cấp Level 2 access tạm thời cho contractor để thực hiện emergency fix. Đồng thời cần notify stakeholders theo SLA. Nêu đủ cả hai quy trình.

**Worker được chọn:** `policy_tool_worker`  
**Route reason (từ trace):** `policy/access signal detected: access, level 2 → route policy_tool_worker (prefer MCP) | risk_high signals: emergency, 2am | choose MCP=yes`  
**MCP tools được gọi:** `check_access_permission`, `get_ticket_info`  
**Workers called sequence:** `retrieval_worker -> policy_tool_worker -> synthesis_worker`

**Kết quả thực tế:**
- final_answer (ngắn): Trả lời đầy đủ 2 phần: SLA P1 notification (Slack/email/PagerDuty + escalation 10 phút) và điều kiện cấp Level 2 emergency access (Line Manager + IT Admin).
- confidence: `0.80`
- Correct routing? `Yes`

**Nhận xét:** _(Routing này đúng hay sai? Nếu sai, nguyên nhân là gì?)_

Routing đúng hướng cho câu multi-hop vì vừa cần policy/access vừa cần ngữ cảnh SLA. Ở batch mới, nhánh policy + MCP trả dữ liệu hợp lệ nên synthesis không còn bị partial.

---

## Routing Decision #2

**Trace ID:** `run_20260414_172348` (q11)

**Task đầu vào:**
> Ticket P1 được tạo lúc 22:47. Ai sẽ nhận thông báo đầu tiên và qua kênh nào?

**Worker được chọn:** `retrieval_worker`  
**Route reason (từ trace):** `SLA/ticket retrieval signal detected: p1, escalation, ticket → route retrieval_worker | choose MCP=no`  
**MCP tools được gọi:** `[]`  
**Workers called sequence:** `retrieval_worker -> synthesis_worker`

**Kết quả thực tế:**
- final_answer (ngắn): Trả lời dựa trên evidence SLA/P1, không cần policy tool.
- confidence: `0.64`
- Correct routing? `Yes`

**Nhận xét:**

Routing phù hợp cho câu retrieval đơn tài liệu. Không cần gọi MCP nên latency ổn định hơn nhánh policy và trace ngắn, dễ debug.

---

## Routing Decision #3

**Trace ID:** `run_20260414_172337` (q09)

**Task đầu vào:**
> ERR-403-AUTH là lỗi gì và cách xử lý?

**Worker được chọn:** `human_review` (sau đó auto-approve về `retrieval_worker`)  
**Route reason (từ trace):** `unknown error code without policy/SLA context → human review | choose MCP=no | human approved → retrieval`  
**MCP tools được gọi:** `[]`  
**Workers called sequence:** `human_review -> retrieval_worker -> synthesis_worker`

**Kết quả thực tế:**
- final_answer (ngắn): Hệ thống abstain do thiếu thông tin mã lỗi trong tài liệu nội bộ.
- confidence: `0.30`
- Correct routing? `Yes`

**Nhận xét:**

Đây là route quan trọng để chống hallucination cho unknown error code. HITL placeholder giúp thể hiện rõ quyết định “escalate to human” trong trace.

---

## Routing Decision #4 (tuỳ chọn — bonus)

**Trace ID:** `run_20260414_172359` (q13)

**Task đầu vào:**
> Contractor cần Admin Access (Level 3) để khắc phục sự cố P1 đang active. Quy trình cấp quyền tạm thời như thế nào?

**Worker được chọn:** `policy_tool_worker`  
**Route reason:** `policy/access signal detected: cấp quyền, access, level 3 → route policy_tool_worker (prefer MCP) | choose MCP=yes`

**Nhận xét: Đây là trường hợp routing khó nhất trong lab. Tại sao?**

Trường hợp này khó vì có cả access policy và incident context. Supervisor route đúng sang policy worker, và trong batch mới worker gọi thành công cả `check_access_permission` + `get_ticket_info`, giúp synthesis trả lời đầy đủ hơn.

---

## Tổng kết

### Routing Distribution

| Worker | Số câu được route | % tổng |
|--------|------------------|--------|
| retrieval_worker | 8 | 53% |
| policy_tool_worker | 7 | 46% |
| human_review | 1 lần trigger HITL (sau đó route retrieval) | 6% hitl_rate |

### Routing Accuracy

> Trong số X câu nhóm đã chạy, bao nhiêu câu supervisor route đúng?

- Câu route đúng: 15 / 15 traces (xét theo intent routing ở batch mới nhất)
- Câu route sai (đã sửa bằng cách nào?): 0 trong batch hiện tại. Vấn đề chính nằm ở quality của nhánh policy do lỗi MCP runtime, không phải supervisor route.
- Câu trigger HITL: 1

### Lesson Learned về Routing

> Quyết định kỹ thuật quan trọng nhất nhóm đưa ra về routing logic là gì?  
> (VD: dùng keyword matching vs LLM classifier, threshold confidence cho HITL, v.v.)

1. Ưu tiên keyword routing rule-based cho lab để kiểm soát được hành vi và dễ giải thích `route_reason`.
2. Dùng `route_reason` có signal + quyết định MCP (`choose MCP=yes/no`) để debug nhanh hơn.

### Route Reason Quality

> Nhìn lại các `route_reason` trong trace — chúng có đủ thông tin để debug không?  
> Nếu chưa, nhóm sẽ cải tiến format route_reason thế nào?

Hiện tại đủ để debug root cause nhanh. Cải tiến kế tiếp: chuẩn hóa format theo key-value ngắn gọn (vd. `signals=[p1,ticket]; route=retrieval; risk=false; mcp=false`) để dễ parse tự động.
