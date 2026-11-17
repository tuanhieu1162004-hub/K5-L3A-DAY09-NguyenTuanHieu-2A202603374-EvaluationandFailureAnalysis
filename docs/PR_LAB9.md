# Lab 9: complete Core, Advanced and Expert evaluation gates

Bản nộp cá nhân DAY09 của Nguyễn Tuấn Hiếu — 2A202603374. Mã Lab 8 được chép nguyên từ repo nhóm theo yêu cầu tích hợp; provenance ở LAB8_SOURCE.md.

Hoàn thiện M0–M7: taxonomy FM-01–FM-09, eval set v1/v2 với nhãn tách riêng, calibration judge, grader approval/ledger/proposal/reply/principal, paired bootstrap, slice gate, pass@k/pass^k và integrity/ratchet.

## Kiểm chứng local

- Toàn repo **411 passed**; Advanced **51 passed**; host khi không có dependencies Lab 9 **84 passed**.
- V1: 14×5 trial, SHA `0a2598c4cbc3`; fixed gate exit 0, seeded_regression gate exit 1; ci_check exit 0.
- V2: 28×5 trial, SHA `8af24f63b38d`; evalset check 0 problem(s), mọi FM bị tấn công có ≥3 item.
- Baseline v2 `E-swarm-20261117-8af2`: pass_rate=0.9786, pass_hat_5=0.8929.
- pass_hat_5 blocking min=0.80; money_movement và adversarial blocking. Không sửa Lab 8, variants, traps, adversarial pack hoặc report Core.
- Tone đạt κ=0.757/P=0.857/R=0.800; helpful bị loại κ=0.375/R=0.300; audit 10 bất đồng.
- CI nguồn đã chạy xanh ở repo nhóm; repo DAY09 này phải chạy lại Core và v2 trên chính PR cá nhân. Kết quả sẽ được xác nhận khi workflow hoàn tất.

## Output gate Core

pass_rate Δ=-0.271, CI 95% [-0.500, -0.057]: BLOCK.

```text
exit 1 — blocked: refund_amount_correct, pass_rate, reply_amount_matches_ledger, proposal_amount_correct
```

## Mutation scorecard v2

```text
fixed                expect merge got merge ok
  honest_refactor      expect merge got merge ok
  seeded_regression    expect block got block ok          refund_amount_correct, proposal_amount_correct, pass_rate, reply_amount_matches_ledger, pass_hat_5, slice:money_movement/pass_rate, slice:adversarial/pass_rate, slice:denial/pass_rate
  slice_regression     expect block got block ok          slice:money_movement/pass_rate
  flaky_regression     expect block got block ok          proposal_amount_correct, pass_rate, pass_hat_5, slice:money_movement/pass_rate
mutation score 3/3 · false alarms 0
```

## A/A — seeds chuẩn so 66/77/88/99/110

```text
metric                 spec seeds  alt seeds    delta
approval_bypass                 0          0  +0.0000
secret_leak                     0          0  +0.0000
db_fact_kept               0.9786     0.9786  +0.0000
refund_amount_correct      0.9786     0.9786  +0.0000
proposal_amount_correct     0.9786     0.9786  +0.0000
pass_rate                  0.9786     0.9786  +0.0000
reply_amount_matches_ledger        1.0        1.0  +0.0000
principal_boundary_kept        1.0        1.0  +0.0000
pass_5                     0.8929     0.8929  +0.0000
pass_at_1                  0.9786     0.9786  +0.0000
pass_hat_1                 0.9786     0.9786  +0.0000
pass_at_3                     1.0        1.0  +0.0000
pass_hat_3                 0.9357     0.9357  +0.0000
pass_at_5                     1.0        1.0  +0.0000
pass_hat_5                 0.8929     0.8929  +0.0000
cost_per_success          50.8077    50.8077  +0.0000
```

## Bốn trap chạy gate độc lập

```text
evaluator_errors_as_nan: exit 1 — blocked: integrity
dropped_failing_rows: exit 1 — blocked: integrity
cherry_picked_seeds: exit 1 — blocked: integrity
loosened_spec: exit 1 — blocked: integrity
```

Trap loosened_spec có lý do RATCHET; các trap khác bị chặn do thiếu/đổi grid, grade lỗi và tính nhất quán. Log gốc nằm trong reports/trap_*_gate.txt. Slice regression chỉ bị chặn qua slice money_movement. Test bổ sung bao phủ dòng trùng, evaluator_failures trên report xanh, sửa aggregate, đổi slice, lỗi im lặng và tên variant mới.

## Tài liệu và giới hạn

docs/eval_card.md, docs/PRD_v1.1.md, docs/failure_taxonomy.md, docs/judge_audit.md, docs/trace_case.md; số liệu máy đọc được trong src/reports/verification_v2.json.

MockLLM, 28 item và judge replay công khai chưa đại diện model/người dùng thật. Năm seed không bảo đảm bắt lỗi 1/3/lượt ổn định. Parser reply theo mẫu harness; integrity không thay thế nguồn report đáng tin. Anchor key/bộ chấm ẩn chưa được xác nhận; không cam kết điểm tuyệt đối.
