# Single Agent vs Multi-Agent Comparison — Lab Day 09

**Nhóm:** Nhom69  
**Ngày:** 14/04/2026

> **Hướng dẫn:** So sánh Day 08 (single-agent RAG) với Day 09 (supervisor-worker).
> Phải có **số liệu thực tế** từ trace — không ghi ước đoán.
> Chạy cùng test questions cho cả hai nếu có thể.

---

## 1. Metrics Comparison

> Điền vào bảng sau. Lấy số liệu từ:
> - Day 08: chạy `python eval.py` từ Day 08 lab
> - Day 09: chạy `python eval_trace.py` từ lab này

| Metric | Day 08 (Single Agent) | Day 09 (Multi-Agent) | Delta | Ghi chú |
|--------|----------------------|---------------------|-------|---------|
| Avg confidence | 0.96 (proxy từ Faithfulness scorecard) | 0.619 (trace avg_confidence) | -0.341 | Chỉ số khác bản chất, dùng tham chiếu tương đối |
| Avg latency (ms) | N/A | 6247 ms | N/A | Day 08 scorecard không log latency |
| Abstain/HITL rate (%) | N/A | 6% (1/15) | N/A | Day 09 có case abstain rõ cho ERR-403-AUTH |
| Multi-hop quality | N/A | Đã trả đủ ở q15/gq09; còn thận trọng ở case thiếu policy v3 | N/A | Cần thêm policy v3 để kết luận chắc cho đơn đặt trước 01/02/2026 |
| Routing visibility | ✗ Không có | ✓ Có route_reason | N/A | |
| Debug time (estimate) | 20-30 phút | 8-12 phút | giảm ~50-60% | Thời gian tìm root cause 1 bug routing/policy |
| MCP observability | Không tách biệt | Có field `mcp_tools_used`, valid usage = 3/15 | Tăng rõ | Đã thấy được tool/input/output ở các case policy khó |

> **Lưu ý:** Nếu không có Day 08 kết quả thực tế, ghi "N/A" và giải thích.

---

## 2. Phân tích theo loại câu hỏi

### 2.1 Câu hỏi đơn giản (single-document)

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Accuracy | Cao | Trung bình-khá |
| Latency | N/A | ~5.4-5.7s cho retrieval route trong batch mới |
| Observation | Trả lời ổn khi query thẳng | Route retrieval ổn định, nhưng confidence bảo thủ hơn |

**Kết luận:** Multi-agent không luôn tăng accuracy cho câu đơn giản, nhưng giúp quan sát được từng bước nên dễ sửa lỗi hơn.

### 2.2 Câu hỏi multi-hop (cross-document)

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Accuracy | N/A | Route đúng và answer đầy đủ hơn ở case policy+incident có MCP |
| Routing visible? | ✗ | ✓ |
| Observation | Không có trace worker-level | Có chuỗi `retrieval -> policy_tool -> synthesis`; MCP path đã có output hợp lệ ở q13, q15 |

**Kết luận:** Day 09 phù hợp hơn cho câu multi-hop vì biểu diễn được orchestration và nguồn lỗi theo từng worker; sau khi ổn định MCP local path, chất lượng ở case policy+incident đã cải thiện rõ.

### 2.3 Câu hỏi cần abstain

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Abstain rate | N/A | Có (ERR-403-AUTH sau bản vá) |
| Hallucination cases | Có rủi ro khi thiếu context | Đã giảm nhờ guard + HITL route |
| Observation | Không có node HITL chuyên biệt | Có `human_review` route và `hitl_triggered` trong trace |

**Kết luận:** Multi-agent hỗ trợ anti-hallucination tốt hơn khi thiết kế route + synthesis guard đúng cách.

---

## 3. Debuggability Analysis

> Khi pipeline trả lời sai, mất bao lâu để tìm ra nguyên nhân?

### Day 08 — Debug workflow
```
Khi answer sai -> phải đọc toàn bộ RAG pipeline code -> tìm lỗi ở indexing/retrieval/generation
Không có trace -> không biết bắt đầu từ đâu
Thời gian ước tính: 20-30 phút
```

### Day 09 — Debug workflow
```
Khi answer sai -> đọc trace -> xem supervisor_route + route_reason
  -> Nếu route sai -> sửa supervisor routing logic
  -> Nếu retrieval sai -> test retrieval_worker độc lập
  -> Nếu synthesis sai -> test synthesis_worker độc lập
Thời gian ước tính: 8-12 phút
```

**Câu cụ thể nhóm đã debug:**

Lỗi dữ liệu null ở `mcp_tools_used` trong nhánh policy. Sau khi vá phần chuẩn hóa output MCP, batch mới ghi nhận `mcp_valid_usage_rate = 3/15` và không còn lỗi runtime kiểu `NoneType` ở q13, q15.

---

## 4. Extensibility Analysis

> Dễ extend thêm capability không?

| Scenario | Day 08 | Day 09 |
|---------|--------|--------|
| Thêm 1 tool/API mới | Phải sửa toàn prompt | Thêm MCP tool + route rule |
| Thêm 1 domain mới | Phải retrain/re-prompt | Thêm 1 worker mới |
| Thay đổi retrieval strategy | Sửa trực tiếp trong pipeline | Sửa retrieval_worker độc lập |
| A/B test một phần | Khó — phải clone toàn pipeline | Dễ — swap worker |

**Nhận xét:** Day 09 rõ ràng dễ mở rộng hơn về mặt kiến trúc. Chi phí là nhiều moving parts hơn, cần quản lý contract và trace cẩn thận.

---

## 5. Cost & Latency Trade-off

> Multi-agent thường tốn nhiều LLM calls hơn. Nhóm đo được gì?

| Scenario | Day 08 calls | Day 09 calls |
|---------|-------------|-------------|
| Simple query | 1 LLM call | 1 synthesis call, thường không dùng MCP |
| Complex query | 1 LLM call | 1 synthesis + 0-2 MCP calls trong batch hiện tại |
| MCP tool call | N/A | 3/15 traces có gọi tool và đều có payload hợp lệ |

**Nhận xét về cost-benefit:** Day 09 tốn thêm orchestration/tool overhead, nhưng đổi lại có khả năng kiểm soát và debug tốt hơn nhiều cho case phức tạp.

---

## 6. Kết luận

> **Multi-agent tốt hơn single agent ở điểm nào?**

1. Debuggable hơn nhờ route_reason, workers_called, mcp_tools_used.
2. Dễ mở rộng capability qua MCP mà không phá pipeline lõi.

> **Multi-agent kém hơn hoặc không khác biệt ở điểm nào?**

1. Với câu đơn giản, đôi khi chưa cải thiện accuracy và có thể tăng độ phức tạp không cần thiết.

> **Khi nào KHÔNG nên dùng multi-agent?**

Khi domain hẹp, yêu cầu đơn giản, và team chưa cần trace sâu hoặc tích hợp tool ngoài.

> **Nếu tiếp tục phát triển hệ thống này, nhóm sẽ thêm gì?**

Thêm evaluation script cho grading questions với chấm đúng/sai tự động theo rubric và thêm semantic parser để route bằng classifier thay cho keyword rules.
