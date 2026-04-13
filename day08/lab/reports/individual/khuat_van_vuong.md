# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Khuất Văn Vương
**Vai trò trong nhóm:** Tech Lead  
**Ngày nộp:** 13/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

> Mô tả cụ thể phần bạn đóng góp vào pipeline:
>
> - Sprint nào bạn chủ yếu làm?
> - Cụ thể bạn implement hoặc quyết định điều gì?
> - Công việc của bạn kết nối với phần của người khác như thế nào?

---

Trong vai trò Tech Lead, tôi cần đảm bảo pipeline chạy ổn định và end to end. Cụ thể, trong sprint 1,2, đưa ra quyết định và implement xử lý index.py cho việc preprocess, chunk, embed và store vào vector db. Phần xử lý rag_answer.py, tôi xử lý và hỗ trợ Retrieve Onwer đảm bảo flow retrive, generate và trả về sources. Trong sprint 3, phối hợp với Retrieve Ownerr để thử variant hybrid + rerank, đặc biệt ở phần tuned để tăng độ chính xác cho strategy này, cụ thể ở các phần tuned rerank function, grounded prompt. Ở Sprint 4, tôi review scorecard, đối chiếu các case fail, đặc biệt case q10, rồi điều phối, tham gia xử lý các việc tuned các prompt, retrieval.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

> Chọn 1-2 concept từ bài học mà bạn thực sự hiểu rõ hơn sau khi làm lab.
> Ví dụ: chunking, hybrid retrieval, grounded prompt, evaluation loop.
> Giải thích bằng ngôn ngữ của bạn — không copy từ slide.

---

Sau lab này, tôi hiểu rõ hơn hai điểm:

- Thứ nhất là phần grounded answer không chỉ là thêm câu answer from context, mà là thiết kế rule ra quyết định rõ: khi nào trả lời trực tiếp, khi nào suy luận theo policy chung, khi nào mới được abstain. Nếu rule này mơ hồ, model dễ từ chối quá mức hoặc trả lời lan man dù retrieval đúng.
- Thứ hai là evaluation loop quan trọng hơn cảm giác chủ quan khi đọc vài câu trả lời. Trước đây tôi nghĩ hybrid + rerank gần như luôn tốt hơn dense, nhưng scorecard cho thấy variant có thể kém baseline nếu rerank làm lệch ngữ cảnh. Vì vậy, bài học lớn là phải giữ baseline mạnh, đo bằng cùng bộ test, và đọc per-question thay vì chỉ nhìn average tổng.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

> Điều gì xảy ra không đúng kỳ vọng?
> Lỗi nào mất nhiều thời gian debug nhất?
> Giả thuyết ban đầu của bạn là gì và thực tế ra sao?

---

Điều làm tôi bất ngờ nhất là Context Recall gần như luôn cao, nhưng chất lượng answer vẫn không ổn ở một số câu hard. Ban đầu tôi giả thuyết lỗi chính nằm ở retrieval không lấy đúng tài liệu, nhưng khi đối chiếu scorecard thì nhiều câu đã retrieve đúng source rồi mà answer vẫn thiếu trọng tâm hoặc abstain sai. Case mất thời gian nhất là q10: baseline còn trả lời được theo quy trình chuẩn, trong khi variant `hybrid + rerank` lại trả không đủ dữ liệu. Điều này cho thấy rerank không chỉ lọc noise mà còn có thể làm mất chunk quan trọng cho generation. Khó khăn là cân bằng giữa việc đẩy nhanh tuning và việc giữ thí nghiệm sạch để biết biến nào gây ra regression.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

> Chọn 1 câu hỏi trong test_questions.json mà nhóm bạn thấy thú vị.
> Phân tích:
>
> - Baseline trả lời đúng hay sai? Điểm như thế nào?
> - Lỗi nằm ở đâu: indexing / retrieval / generation?
> - Variant có cải thiện không? Tại sao có/không?

**Câu hỏi:** q10 — “Nếu cần hoàn tiền khẩn cấp cho khách hàng VIP, quy trình có khác không?”

**Phân tích:**

---

Đây là câu phản ánh rõ nhất ranh giới giữa thiếu dữ liệu thật và không có case riêng nhưng vẫn có policy chung. Với baseline dense, hệ thống trả lời theo hướng: tài liệu không nêu quy trình VIP riêng, nhưng có quy trình hoàn tiền chuẩn (ticket -> CS review -> Finance xử lý 3-5 ngày). Điểm baseline cho câu này ở mức trung bình (Faithfulness/Relevance chưa cao tuyệt đối) nhưng vẫn hữu ích cho người dùng. Ngược lại, variant `hybrid + rerank` trong lần chạy chính bị rơi về mức rất thấp vì trả lời không đủ dữ liệu, tức là bỏ qua policy chung đang có trong context.

Tôi đánh giá lỗi chính nằm ở tầng retrieval selection và generation policy, không phải indexing. Index vẫn chứa đúng nội dung refund policy, vấn đề ở chỗ là sau khi rerank, tín hiệu policy chuẩn không còn được model dùng hiệu quả, và prompt cũ cho phép abstain quá dễ. Vì vậy variant không cải thiện mà còn regression. Hướng xử lý phù hợp là làm rerank an toàn hơn bằng cách trộn điểm retrieval gốc, và siết rule generation để ưu tiên generation policy trước khi abstain.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

> 1-2 cải tiến cụ thể bạn muốn thử.
> Không phải "làm tốt hơn chung chung" mà phải là:
> "Tôi sẽ thử X vì kết quả eval cho thấy Y."

---

Tôi sẽ thử hai cải tiến cụ thể để kiểm thử thêm các case:

- Một là thay cross-encoder rerank hiện tại bằng model multilingual hoặc bật cơ chế fallback về thứ tự retrieval gốc khi rerank confidence thấp, vì kết quả eval cho thấy variant đang tụt ở câu tiếng Việt khó.
- Hai là thêm một lớp answer post-check đơn giản: nếu câu trả lời là abstain nhưng context có policy chung liên quan thì buộc regenerate theo policy đó. Mục tiêu là giảm false abstain như q10 mà không làm tăng hallucination.

---

_Lưu file này với tên: `reports/individual/[ten_ban].md`_
_Ví dụ: `reports/individual/nguyen_van_a.md`_
re