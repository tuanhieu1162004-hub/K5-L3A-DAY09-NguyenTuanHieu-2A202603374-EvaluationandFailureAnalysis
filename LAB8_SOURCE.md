# Nguồn mã Lab 8 và bản nộp Lab 9

- Repo nộp cá nhân: https://github.com/tuanhieu1162004-hub/K5-L3A-DAY09-NguyenTuanHieu-2A202603374-EvaluationandFailureAnalysis
- Mã Lab 8 lấy từ repo nhóm: https://github.com/hoanganhchimxanh/K5-L3A-DAY08-4ThangSinhVien-FromWorkflowsToAgents
- Mốc main Lab 8: `b20206c5a38f4c06d1091788529b81b7921c2927`.
- Bản M0–M7 đã được kiểm tra trước khi đồng bộ: `92803873c94bdeb9caa2038fbeb95a8082a1f665`; PR nguồn: https://github.com/hoanganhchimxanh/K5-L3A-DAY08-4ThangSinhVien-FromWorkflowsToAgents/pull/1
- `src/lab8/` được chép nguyên nội dung Git, không chỉnh sửa để làm Lab 9. Mã đánh giá và cải tiến chỉ ở `src/lab9/`, tests, config, docs và workflow.
- Bản sao dùng tệp đã commit, không chép môi trường ảo, .git, .env hay instructor pack. Nhãn và report đã sinh bằng script được giữ nguyên.
- Vai trò lead tổng hợp của Nguyễn Tuấn Hiếu tham chiếu [TEAM.md của repo nguồn](https://github.com/hoanganhchimxanh/K5-L3A-DAY08-4ThangSinhVien-FromWorkflowsToAgents/blob/b20206c5a38f4c06d1091788529b81b7921c2927/TEAM.md).

## Chạy kiểm tra

Từ `src`, cài requirements.txt và requirements-lab9.txt rồi chạy:

```powershell
python -m lab9.smoke
python -m pytest -q -o addopts=
python -m lab9.evalset --v2 --check
python -m lab9.mutation --spec config/metric_spec_v2.yaml --baseline reports/baseline_v2.json
```

Đề yêu cầu starter/d09 → main; bài hoàn chỉnh nằm trong PR của nhánh đó. Các liên kết CI của repo nguồn trong eval card là bằng chứng lịch sử, không thay thế CI tại repo cá nhân sau khi push.
