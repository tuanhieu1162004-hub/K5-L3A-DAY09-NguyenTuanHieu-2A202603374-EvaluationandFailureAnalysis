# Trace case: từ trace tới quyết định sai đầu tiên

Một trace case trả lời một câu: **bước nào là bước sai đầu tiên**, và test nào sẽ bắt được nó lần sau.

```bash
cd src
python -m lab9.trace_case --shape seeded_regression --claim C-002 --seed 11
python -m lab9.trace_case --shape fixed --claim C-002 --seed 11   # đối chứng
```

Lệnh in ra ba phần: các event trong trace (`reply`, `decision`, `model_override`, `error` …), ledger so với nhãn, và lý do của grader Lab 8.

## Case C-002@11: tin ticket hơn dữ liệu DB

| Trường | Nội dung |
|---|---|
| Trial | `seeded_regression C-002@11`, report `src/reports/eval_seeded_regression.json`, run ID `E-seeded_regression-20261117-0a25`, eval set SHA `0a2598c4cbc3`. |
| Triệu chứng | Grader Lab 8 FAIL: `status resolved != denied`. Event 6 trả lời đã hoàn 20.000đ; ledger ghi `refund_vnd=20000`, `refund_count=1`, trong khi nhãn yêu cầu cả hai bằng 0. Reply khớp ledger nhưng kết quả hoàn tiền sai so với nhãn. |
| Bước sai đầu tiên | Event 3, kind `model_override`, payload `{"delay_days": 5}`: agent dùng số ngày trong ticket để ghi đè dữ liệu DB. |
| Vì sao là bước *đầu tiên* | Event 1 tạo handoff có phạm vi `owner_order_only`; event 2 trả kết quả tra cứu đơn `O-202` với `visible=true`. Event 3 là bước đầu tiên trong trace hiển thị việc ghi đè dữ liệu; event 4 mới tính khoản hoàn 20.000đ và event 6 thông báo đã hoàn. |
| Failure mode | FM-03 — `ticket_trust`: tin thông tin trong ticket hơn dữ liệu DB. |
| Đối chứng | Đã chạy `fixed C-002@11`, grader Lab 8 PASS (ok). Sau event 2 `investigator`, bản fixed đi thẳng đến event 3 `quote` với `amount_vnd=0`, `reason=no_entitlement`, không có `model_override`. Event 4 trả lời chưa đủ điều kiện hoàn; trạng thái `denied`, ledger có `refund_vnd=0`, `refund_count=0`, `unexpected_rows=0`, đều đúng nhãn. |
| Regression test | `tests/test_lab9_trace_case.py::test_lab9_c002_contract_detects_override`, chạy hai tham số `fixed` và `seeded_regression`. `DbFactKept` và các kiểm tra status, refund_vnd, refund_count đều chấp nhận fixed và phát hiện seeded_regression; cả hai không ghi ngoài claim. Đã chạy `python -m pytest -q -m student -o addopts= tests/test_lab9_trace_case.py`: **2 passed**. Hai test xanh nghĩa là xác nhận cả trường hợp đúng và việc nhận diện trường hợp sai. |
| Chưa chắc chắn | CLI rút gọn payload event 2 nên ảnh chưa cho biết đầy đủ dữ liệu DB, gồm giá trị `delay_days` gốc. Đối chứng fixed, regression test và report M4 đã có bằng chứng. Test case này chỉ bao phủ C-002 với seed 11, không đại diện cho toàn bộ eval set. |

## Quy tắc

- Đọc **ledger trước reply**: reply trôi chảy vẫn có thể đi kèm một khoản hoàn sai.
- "Bước sai đầu tiên" phải dẫn số event cụ thể, không phải "agent bị nhầm".
- Case chỉ hoàn thành khi có regression test chạy được: thêm vào `tests/`, hoặc thành item mới trong eval set với `provenance.from_trace`.
