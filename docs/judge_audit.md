# Judge audit

Đánh giá offline bằng nhãn replay trong CSV public; không gọi API. Trong tất cả phép tính, **FAIL là lớp positive**: TP là lỗi được judge phát hiện, FN là lỗi judge bỏ sót.

Chạy từ `src` bằng Python trong môi trường bài lab:

```powershell
& $py -m pytest -q -m student -o addopts= tests/test_lab9_stats.py -k "not bootstrap"
& $py -m lab9.judge --csv data/eval/judge_tone_public.csv --audit 5
& $py -m lab9.judge --csv data/eval/judge_helpful_public.csv --audit 5
```

## Kết quả calibration

| Tiêu chí | n | κ | Precision | Recall | Đạt FLOORS (κ≥0.6, P≥0.8, R≥0.7)? | Quyết định |
|---|---|---|---|---|---|---|
| tone_ok | 100 | 0.757 | 0.857 | 0.800 | Có, đạt cả ba | Dùng cho tiêu chí giọng điệu trong phạm vi replay đã kiểm định |
| helpful | 100 | 0.375 | 1.000 | 0.300 | Không: κ và Recall dưới sàn | Loại khỏi release gate |

| Tiêu chí | TP | FP | FN | TN | Tỷ lệ lỗi judge quan sát | Tỷ lệ lỗi hiệu chỉnh Rogan–Gladen |
|---|---|---|---|---|---|---|
| tone_ok | 24 | 4 | 6 | 66 | 0.280 | 0.300 |
| helpful | 9 | 0 | 21 | 70 | 0.090 | 0.300 |

Đã chạy test phần M2: **4 passed, 2 deselected**. Hai test bootstrap thuộc M4 nên chưa được chọn. κ không xác định phải raise `ValueError`; judge không được vượt calibration nhờ trường hợp suy biến. Precision/Recall có mẫu số bằng 0 trả 0. Rogan–Gladen giới hạn kết quả về [0,1] và từ chối đầu vào không hợp lệ hoặc mẫu số bằng 0.

## Audit các bất đồng

Các nhận định dưới đây đối chiếu toàn bộ `reply` và trường `note`/`human_failure` trong CSV. Với helpful, số tiền ledger là thông tin tham chiếu ghi trong CSV replay, không phải một lượt chạy ledger mới. Các đề xuất là thay đổi rubric cần thử nghiệm lại; nhãn và verdict replay gốc được giữ nguyên.

| # | Case | Judge nói | Người nói | Ai đúng? | Bằng chứng và hành động sửa rubric |
|---|---|---|---|---|---|
| 1 | tone H-008 | PASS | FAIL | Người, theo quy chuẩn CS trong note | Câu dùng “nha”, “anh check giúp em”, giọng quá suồng sã. Rubric cần nêu mẫu thân mật không phù hợp và cặp ví dụ cách viết được phép; không mặc định thân thiện là chuyên nghiệp. |
| 2 | tone H-017 | PASS | FAIL | Người, theo ngữ cảnh trong note | Câu gọi “bạn ơi” và kết thúc “rồi nha”; note cho biết khách lớn tuổi. Rubric phải xét ngữ cảnh xưng hô, dùng “anh/chị” khi chưa rõ, không chỉ dựa vào từ “Dạ”. |
| 3 | tone H-029 | PASS | FAIL | Người | “Không cần nhắn thêm” mang tính ra lệnh dù có “Dạ, vui lòng”. Rubric cần đánh giá toàn câu và đánh dấu các mệnh lệnh gây cảm giác bị gạt đi; sửa thành thông báo thời gian chờ và bước tiếp theo. |
| 4 | tone H-042 | FAIL | PASS | Người | Reply có xưng hô lịch sự, thông tin hoàn tiền và thời gian nhận. Theo note, ngắn nhưng đủ ý; judge phạt vì thiếu xin lỗi. Rubric không bắt buộc xin lỗi ở mọi câu trả lời và không đồng nhất độ dài với giọng điệu. |
| 5 | tone H-051 | FAIL | PASS | Người, theo thuật ngữ được phép trong note | “Refund” là thuật ngữ CS LogiX cho phép. Rubric cần danh sách thuật ngữ chấp nhận, không tự động FAIL chỉ vì có từ tiếng Anh. |
| 6 | helpful HL-015 | PASS | FAIL | Người, theo ledger tham chiếu trong note | Reply nói 55.000đ, note ledger 40.000đ. Rubric phải ưu tiên đúng kết quả; thêm grader code đối chiếu số tiền reply với ledger, không dùng độ lịch sự để bù cho sai tiền. |
| 7 | helpful HL-016 | PASS | FAIL | Người, theo ledger tham chiếu trong note | Reply nói 55.000đ, note ledger 35.000đ, dù có nhiều câu xin lỗi. Rubric phải tách đúng sự thật khỏi phong cách; lời xin lỗi không làm một kết quả sai thành đúng. |
| 8 | helpful HL-020 | PASS | FAIL | Người, theo ledger tham chiếu trong note | Reply nói 90.000đ, note ledger 120.000đ. Grader tiền phải kiểm tra khớp chính xác, bắt cả trường hợp báo thiếu lẫn báo thừa. |
| 9 | helpful HL-028 | PASS | FAIL | Người, theo ledger tham chiếu trong note | Reply nói 50.000đ, note ledger 35.000đ. Rubric không thưởng lặp lời cảm ơn/xin lỗi; cung cấp kết quả chuẩn cho grader đối chiếu. |
| 10 | helpful HL-035 | PASS | FAIL | Người, theo ledger tham chiếu trong note | Reply nói 50.000đ, note ledger 35.000đ. Thêm ví dụ âm là câu lịch sự nhưng sai tiền; quyết định đúng tiền phải do code kiểm tra. |

## Kết luận

- Tone đạt FLOORS: TP=24, FP=4, FN=6, TN=66. Có thể dùng cho tiêu chí giọng điệu đã kiểm định, nhưng vẫn có 6 lỗi bị bỏ sót và 4 báo nhầm trên tập này; không dùng nó để xác nhận tiền hoặc approval.
- Helpful không được dùng làm gate: Precision=1.0 chỉ cho thấy 9 lỗi bị đánh dấu đều đúng. Judge bỏ sót 21/30 lỗi thật, Recall=0.3 và κ=0.375; tỷ lệ PASS cao không phải bằng chứng agent hữu ích hơn.
- Rogan–Gladen đưa tỷ lệ lỗi helpful từ 0.09 về 0.30 trong dữ liệu replay. Hiệu chỉnh tỷ lệ tổng thể không sửa các verdict sai ở từng case, nên không thay đổi quyết định loại judge này.
- Tiền và approval luôn kiểm tra bằng code; FM-08 cần grader so sánh reply với ledger ở M3. Chỉ số giọng điệu không thay thế kiểm tra đúng dữ liệu.
- Rủi ro còn lại: cả hai judge chỉ được kiểm trên CSV replay đã công khai, mỗi tập 100 dòng. Audit dựa trên nhãn và note được cung cấp, chưa có đánh giá người độc lập mới hoặc dữ liệu người dùng thật. Sau khi sửa rubric cần chạy judge mới và calibration trên tập held-out có nhãn người; kết quả replay hiện tại không chứng minh rubric đã cải thiện.
