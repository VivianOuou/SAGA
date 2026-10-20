# 小规模真实 A/B 结果（试点）

- **性质**：真实 LLM（planner/analyzer/judge/scorer 匹配均为 `gpt-5-mini-2025-08-07`，拒答检测 `gpt-4.1-nano`）+ **合成数值任务**。不是真实科研任务。
- **代码版本**：c93f2a3（运行于 2026-10-20，Gautschi 登录节点 tmux）；配置 `exps/meta_controller/ab_config.yaml`（运行前固定）。
- **设计**：3 任务 × 2 种子，每个 task-seed 都跑 A（Controller 关闭）与 B（Controller + 普通 LLM Judge）。两组共享任务、初始种群与目标、模块与模型、种子、预算上限、试验额度、超时。
- 修复前的 3 格试跑见 `prefix_pilot/`（不计入）。逐格数据：`real_llm__*.json`；Judge 决策：`real_llm__*__B.decisions.jsonl`；汇总表：`ab_summary.md`。
- **样本极小，不做显著性检验，不推断泛化。**

## 1. 结果

| 任务 | 种子 | A 测试指标 | B 测试指标 | B−A | A 成功 | B 成功 |
|---|---|---|---|---|---|---|
| robust_design（阈值 0.454） | 0 | 0.442 | 0.451 | +0.009 | 否 | 否 |
| robust_design | 1 | 0.431 | 0.450 | +0.019 | 否 | 否 |
| constrained_yield（阈值 0.592） | 0 | 0.647 | 0.650 | +0.003 | 是 | 是 |
| constrained_yield | 1 | 0.603 | 0.648 | +0.045 | 是 | 是 |
| spectral_signal（阈值 0.853） | 0 | 0.824 | 0.816 | −0.008 | 否 | 否 |
| spectral_signal | 1 | 0.801 | 0.847 | +0.046 | 否 | 否 |

- 成功数：A 2/6，B 2/6，相同。
- 固定外部指标（test split）：B−A 的配对平均差为 +0.019，6 对中 5 对 B ≥ A。这是一个弱的、方向偏正的信号。但差值与同组种子间的差异（0.01–0.04）处在同一量级。
- 所有 12 格都正常完成 6 轮（`max_iterations`），没有失败，也没有因预算提前终止主循环。

## 2. 成本（B 的 Judge、试验、验证均已计入）

| | LLM 调用 | tokens | 费用（LiteLLM 估算） | oracle 评估 |
|---|---|---|---|---|
| A 合计（6 格） | 113 | 519,597 | $0.327 | 10,952 |
| B 合计（6 格） | 136 | 589,546 | $0.415 | 40,184 |

- B 多出的部分：Judge 共 26 次调用、11.2 万 tokens；试验与验证共约 2.9 万次评估（候选试验 13,592 次，基线试验加验证器 15,576 次）。没有 token 统计缺失的调用（`calls_missing_usage = 0`）。
- **两组都远未用到预算上限的调用、token 和时间部分**（上限为 50 次调用、60 万 tokens、8000 次评估）。B 的评估数接近上限，有 4 次干预因"预算不足以支付干预加一轮主循环"而在 Judge 之前被跳过。A 在第 6 轮停止，没有用掉同样的剩余预算。因此这次比较**不是算力对等**的：B 用了更多资源。若要做算力对等的比较，需要让 A 也用满同样的预算（例如提高 `max_iterations`、以预算作为唯一停止条件），这次没有做。

## 3. Controller 行为

- **Judge 选择的目标**：objective 22 次，implementation 3 次。planning、optimization_workflow、no_change 一次都没有被选到。
- **failure_location 与 intervention_target 不同的有 3 次**，都是 spectral_signal 中 "implementation → objective"：Judge 判断 `smoothness` 的实现有问题（数值远大于 1），但选择在 objective 层删除或降权它。
- **结果统计**：经过验证的候选 22 个，accepted 7 个、rejected 15 个，接受率 32%。此外 invalid_decision 4 次，包括：提议加入已存在的目标（2 次）、把目标重新绑定到它当前已绑定的 scorer（1 次）、schema 不合法（1 次）。这些都被拦下，没有替换成其他干预。
- **被接受的 delta**（验证集）：0.013、0.018、0.050、0.050、0.085、0.106、0.596。基线在两个种子之间的差异中位数为 0.005、均值为 0.017，所以 **0.013 和 0.018 这两次接受处在试验噪声水平**。`min_improvement = 0.01` 这个门槛偏低。
- **被拒绝的提议中**，有 2 次是大幅退化（−0.42、−0.20，都出现在 constrained_yield，大幅改动权重并加入 `yield_per_unit_cost`）。验证器拦下了这类有害修改。

### 值得注意的问题（如实记录）

1. **原生 Planner 已经处理了大部分植入的问题。** 由于 Planner 的上下文里列出了全部 scorer 及其描述，所有 A 组运行在第 1 轮就自行加入了正确的目标：`smoothness_v2`、`robust_performance_mc`、`within_cost_budget`。合成任务留给 Controller 的改进空间因此远小于设计时的预期。这限制了本次 A/B 能说明的问题。
2. **组合提议的验证不能归因到单个操作。** spectral_signal s0 B 在第 2 轮接受了一个"提高 smoothness_v2 权重 + 重新加入有 bug 的 smoothness"的组合，delta 为 +0.106。验证只说明整个组合更好，不说明其中每一步都有益。该格最终比 A 低 0.008。
3. **包装器使"已绑定"检查失效。** spectral_signal s1 B 在第 1 轮接受了 `sanitize_outputs(smoothness)`（delta +0.596）；第 2 轮的 `rebind_scorer(smoothness → smoothness)` 没有被判为无操作，实际效果是撤销了清洗、恢复原 scorer。它以 +0.018（噪声水平）被接受。
4. 每格只有 2 个验证种子；试验 GA 有随机性，LLM 规划也不确定。

## 4. 结论边界

- 能说明的：在真实 LLM 下，整条链路（提议 → 隔离执行 → 独立验证 → accept/reject → 回滚 → 成本记账）可以稳定运行；Judge 的诊断能区分问题位置与干预目标；验证门槛挡住了多数退化或无效的修改。
- 不能说明的：Controller 显著提升了 SAGA；在算力对等条件下 B 更好；"选择干预目标"优于"修改错误发生的位置"（需要故障位置驱动、随机选择等对照组）；任何关于递归自我改进的结论。

## 5. 建议的下一步（未执行）

1. **算力对等**：A 与 B 都以预算作为停止条件（例如提高 `max_iterations`），或者给 A 等量的额外迭代。
2. **提高接受门槛或验证种子数**：例如 `min_improvement` 取验证噪声的 2–3 倍，或使用 4 个以上种子。
3. **限制组合提议**：一次只允许一个 objective 操作，或者对组合内的操作做消融，以便归因。
4. **修正"已绑定"检查**：识别 sanitize 包装器下的原始 scorer，并把"移除补丁"作为显式动作。
5. **任务设计**：去掉 Planner 上下文中的 scorer 描述提示，或使用 SAGA 真实任务（需要 Claude Code + Docker），以保留 Controller 可以发挥的空间。
6. **增加对照组**：故障位置驱动策略、随机目标策略。
7. **重复次数**：增加种子和任务数后，再考虑统计检验。
