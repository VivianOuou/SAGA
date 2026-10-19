# 合成数值任务（SYNTHETIC）

供 Meta-Controller 离线测试和小规模 A/B 使用。这些是纯 numpy 任务，不代表真实科研任务。候选是 [0,1]^D 中的向量。

| 任务 | D | 目标（给 Planner/Analyzer 的自然语言） | 已注册的代理 scorer | 初始目标 | 独立验证器（真值） |
|---|---|---|---|---|---|
| robust_design | 8 | 在制造公差（每维 std 0.08）下最大化期望性能；越过失效边界 x0+x1>1 时性能为 0 | nominal_performance（无公差，会把解推向边界）、robust_performance_mc（16 次 MC，与真值方向一致但有噪声）、cliff_margin、center_distance | nominal_performance↑ | 公差扰动下的期望性能 |
| constrained_yield | 6 | 在市场情景不确定下最大化期望产量，成本 ≤ 0.15 为硬约束 | yield_estimate、production_cost、within_cost_budget（filter）、cost_budget_slack、yield_per_unit_cost | yield_estimate↑, production_cost↓ | 各情景下的平均产量 × 是否满足预算 |
| spectral_signal | 12 | 低频幅度谱匹配目标，同时信号要平滑 | spectrum_match、**smoothness（故意植入的实现 bug：指数符号写反，值 >1 且随粗糙度增大）**、smoothness_v2（正确实现）、signal_mean_level | spectrum_match↑, smoothness↑ | 谱匹配 × 平滑度，含执行噪声和测量噪声 |

- `smoothness` 的 bug 是**有意设计**的，用来模拟 coding agent 生成了错误 scorer 的情况，检验 implementation 层面的失败与干预。描述中没有提示这个 bug，只能从数值证据（声称在 [0,1]，实际出现远大于 1 的值）发现。
- 验证器与 scorer 是分开实现的（`validators.py`），scorer 里的 bug 不会传到验证器。指标是系统排名前 5 个候选的平均真实质量。validation、test、calibration 三个 split 的随机抽样相互独立。
- 成功阈值 = 0.9 × q*。其中 q* 由直接优化 calibration split 的 oracle GA 得到（`exps/meta_controller/calibrate_tasks.py`，结果在 `task_thresholds.json`），**在任何 A/B 运行之前固定**。
- 任务参数（公差 std、预算等）是在 A/B 之前，用不调用 LLM 的纯 GA 检查调出来的。调参的目的是保证"只用初始目标"时有改进空间、随机种群达不到阈值；调参过程没有使用任何 A/B 结果。
- MCP scorer 模块只支持 `--local` 模式（`run_scorers_in_docker=False`）。修改 `base.py` 后需要运行 `python -m modules.numeric_tasks.scorer_mcp.generate_inits`，重新生成 `__init__.py`。
- `mocks.py` 中都是 MOCK 组件（FakeLLMClient、ScriptedJudge、ScriptedValidator、规则 Planner、统计 Analyzer），只用于测试和离线流程检查。
