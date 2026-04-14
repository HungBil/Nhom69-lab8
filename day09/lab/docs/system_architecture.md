# System Architecture — Lab Day 09

**Nhóm:** Nhom69  
**Ngày:** 14/04/2026  
**Version:** 1.0

---

## 1. Tổng quan kiến trúc

> Mô tả ngắn hệ thống của nhóm: chọn pattern gì, gồm những thành phần nào.

**Pattern đã chọn:** Supervisor-Worker  
**Lý do chọn pattern này (thay vì single agent):**
Tách rõ trách nhiệm theo module giúp trace dễ đọc và debug nhanh: supervisor chỉ route, retrieval chỉ lấy evidence, policy worker xử lý exception + MCP, synthesis chỉ tổng hợp grounded answer. So với single-agent Day 08, cách này giảm coupling và dễ thay thế từng thành phần độc lập.

---

## 2. Sơ đồ Pipeline

> Vẽ sơ đồ pipeline dưới dạng text, Mermaid diagram, hoặc ASCII art.
> Yêu cầu tối thiểu: thể hiện rõ luồng từ input → supervisor → workers → output.

**Ví dụ (ASCII art):**
```
User Request
     │
     ▼
┌──────────────┐
│  Supervisor  │  ← route_reason, risk_high, needs_tool
└──────┬───────┘
       │
   [route_decision]
       │
  ┌────┴────────────────────┐
  │                         │
  ▼                         ▼
Retrieval Worker     Policy Tool Worker
  (evidence)           (policy check + MCP)
  │                         │
  └─────────┬───────────────┘
            │
            ▼
      Synthesis Worker
        (answer + cite)
            │
            ▼
         Output
```

**Sơ đồ thực tế của nhóm:**

```
User Task
  |
  v
Supervisor (graph.py)
  - set: supervisor_route, route_reason, needs_tool, risk_high
  |
  +--> human_review (nếu ERR-* không có context)
  |       |
  |       +--> retrieval_worker
  |
  +--> retrieval_worker (default / SLA / ticket)
  |
  +--> retrieval_worker -> policy_tool_worker (policy/access/emergency)
                     |
                     +--> MCP tools (search_kb / check_access_permission / get_ticket_info)
  |
  v
synthesis_worker
  |
  v
final_answer + sources + confidence + trace
```

---

## 3. Vai trò từng thành phần

### Supervisor (`graph.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **Nhiệm vụ** | Phân tích tín hiệu từ câu hỏi và quyết định route + mức rủi ro |
| **Input** | task (text câu hỏi user) |
| **Output** | supervisor_route, route_reason, risk_high, needs_tool |
| **Routing logic** | Policy/access/refund -> `policy_tool_worker`; SLA/P1/ticket -> `retrieval_worker`; mã lỗi `ERR-*` thiếu context -> `human_review` |
| **HITL condition** | `unknown error code without policy/SLA context` |

### Retrieval Worker (`workers/retrieval.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **Nhiệm vụ** | Lấy evidence chunks từ KB nội bộ |
| **Embedding model** | `all-MiniLM-L6-v2` hoặc OpenAI embeddings (nếu có key) |
| **Top-k** | Mặc định 3 |
| **Stateless?** | Yes |

### Policy Tool Worker (`workers/policy_tool.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **Nhiệm vụ** | Kiểm tra policy applicability, detect exception, gọi tool bên ngoài khi cần |
| **MCP tools gọi** | `search_kb`, `check_access_permission`, `get_ticket_info` |
| **Exception cases xử lý** | Flash Sale, digital product/license/subscription, activated product, temporal note trước 01/02/2026 |

### Synthesis Worker (`workers/synthesis.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **LLM model** | `gpt-4o-mini` (fallback rule-based nếu không có API key) |
| **Temperature** | 0.1 |
| **Grounding strategy** | Prompt chỉ dùng chunks/policy trong state; fallback rule-based có citation |
| **Abstain condition** | Không có chunks hoặc gặp mã lỗi không có trong docs |

### MCP Server (`mcp_server.py`)

| Tool | Input | Output |
|------|-------|--------|
| search_kb | query, top_k | chunks, sources |
| get_ticket_info | ticket_id | ticket details |
| check_access_permission | access_level, requester_role | can_grant, approvers |
| create_ticket | priority, title, description | mock ticket_id, url, created_at |

---

## 4. Shared State Schema

> Liệt kê các fields trong AgentState và ý nghĩa của từng field.

| Field | Type | Mô tả | Ai đọc/ghi |
|-------|------|-------|-----------|
| task | str | Câu hỏi đầu vào | supervisor đọc |
| supervisor_route | str | Worker được chọn | supervisor ghi |
| route_reason | str | Lý do route | supervisor ghi |
| retrieved_chunks | list | Evidence từ retrieval | retrieval ghi, synthesis đọc |
| policy_result | dict | Kết quả kiểm tra policy | policy_tool ghi, synthesis đọc |
| mcp_tools_used | list | Tool calls đã thực hiện | policy_tool ghi |
| final_answer | str | Câu trả lời cuối | synthesis ghi |
| confidence | float | Mức tin cậy | synthesis ghi |
| workers_called | list | Dấu vết chuỗi worker đã chạy | mọi node ghi |
| hitl_triggered | bool | Có trigger human review hay không | human_review ghi |
| latency_ms | int | Tổng thời gian run | graph ghi |

---

## 5. Lý do chọn Supervisor-Worker so với Single Agent (Day 08)

| Tiêu chí | Single Agent (Day 08) | Supervisor-Worker (Day 09) |
|----------|----------------------|--------------------------|
| Debug khi sai | Khó — không rõ lỗi ở đâu | Dễ hơn — test từng worker độc lập |
| Thêm capability mới | Phải sửa toàn prompt | Thêm worker/MCP tool riêng |
| Routing visibility | Không có | Có route_reason trong trace |
| Khả năng quan sát tool call | Không tách bạch | Có `mcp_tools_used` theo từng câu; batch mới ghi nhận payload hợp lệ ở các case policy khó |

**Nhóm điền thêm quan sát từ thực tế lab:**
Trace thực tế batch mới nhất cho thấy phân phối route: retrieval `8/15 (53%)`, policy `7/15 (46%)`; HITL trigger `1/15 (6%)` ở case `ERR-403-AUTH`; avg_confidence `0.619` và avg_latency `6247ms`. Việc có route_reason giúp xác định nguyên nhân nhanh hơn thay vì phải đọc toàn pipeline.

---

## 6. Giới hạn và điểm cần cải tiến

> Nhóm mô tả những điểm hạn chế của kiến trúc hiện tại.

1. Retrieval đang fallback lexical khi môi trường thiếu `chromadb`, nên độ chính xác chưa ổn định như vector DB chuẩn.
2. Rule-based routing/policy vẫn có false positive nếu câu hỏi phủ định phức tạp.
3. Chưa có Day 08 latency baseline nên chưa định lượng được trade-off tốc độ.
4. Policy hoàn tiền cho đơn đặt trước 01/02/2026 vẫn thiếu tài liệu v3 trong KB, nên một số câu phải trả lời theo hướng thận trọng thay vì kết luận dứt điểm.
