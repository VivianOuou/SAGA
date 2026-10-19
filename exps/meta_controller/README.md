# Intervention-aware Meta-Controller（MVP）

在 SAGA 的 Analyzer 之后，用普通 LLM Judge 提议**一个**有界干预；候选在隔离环境中执行，由**预先固定、
与干预目标分离**的验证器比较"当前已接受状态"和"候选"，然后 accept 或 reject。默认关闭。

本文档只描述机制和复现方式。真实 A/B 的结果见 `results/ab_summary.md`（如果存在）。用 MOCK 组件得到的
结果放在 `results/offline_mock/`，只能证明流程能跑通，不能证明真实 LLM Judge 提升了 SAGA。

## 1. 插入位置与默认关闭

`scileo_agent/core/orchestrator.py` 中 `OptimizationOrchestrator.run()` 的每一轮：

```
Planning -> Scorer Creation -> [apply_accepted_state] -> Optimization -> Analysis -> [MetaController.step] -> 原有停止判断 -> 下一轮
```

- `apply_accepted_state(objectives)`：在 scorer creation 之后，把已接受的 Objective/Implementation 补丁重新应用到本轮目标上（在第一次 accept 之前不做任何事）。
- `step(...)`：在 Analysis 之后、原有 `should_stop` 判断之前执行；它从不修改 `should_stop`。Analyzer 要求停止，或者已经是最后一轮时，直接跳过（记为 `skipped`）。
- 关闭方式：不配置 `loop_config["meta_controller"]`，或者设置 `enabled: false`。此时 `orchestrator.meta_controller is None`，不导入 controller 包，不发生 Judge 调用，`api_usage_statistics.json` 中也没有 `meta_controller` 项。
- 预算上限 `loop_config["budget"]` 是独立的可选项，A/B 两组使用相同的上限。达到上限时，在下一轮开始前停止（`termination_reason="budget_exhausted"`）。

开启示例：

```python
loop_config["meta_controller"] = {
    "enabled": True,
    "task_id": "spectral_signal", "seed": 0,
    "judge": {"type": "llm", "model_name": "openai/gpt-5-mini-2025-08-07"},   # 不填则沿用 planner 的模型
    "validator": "spectral_signal_truth",          # register_validator() 注册的名字；没有验证器时永不 accept
    "validation": {"seeds": [1001, 1002], "min_improvement": 0.01, "trial_optimizer_overrides": {}},
}
loop_config["budget"] = {"max_llm_calls": 50, "max_total_tokens": 600000, "max_oracle_evals": 8000, "max_wall_time_s": 3600}
```

范围说明：Controller 只依据 Analyzer 报告做改进，**不会**恢复 Analyzer 之前抛出的任意运行时异常，这类异常仍然会像原来一样终止运行。

## 2. 决策结构（`scileo_agent/meta_controller/schema.py`）

| 字段 | 说明 |
|---|---|
| `failure_location` | 问题表现在哪里：objective / planning / implementation / optimization_workflow / analysis / none / unknown |
| `root_cause_hypothesis` | 可能的原因，允许不确定 |
| `intervention_target` | objective / planning / implementation / optimization_workflow / no_change，可以与 `failure_location` 不同 |
| `rationale` | 依据的可观察证据 |
| `proposed_change` | 按目标严格校验的有界修改（`extra="forbid"`，有数值范围） |
| `expected_benefit` | 假设，不是测量值 |
| `validation_plan` | 只作记录；验收规则在运行前固定，Judge 不能修改 |
| `confidence` | 可选。模型自报、**未经校准**，不等于实际收益的概率 |

以下情况都记录原因并保持已接受状态，不会改成别的干预：

- 解析失败、调用失败：`judge_error`
- schema 或现场校验失败：`invalid_decision`
- 模块不支持该动作：`unsupported`
- 预算不足：`skipped` 或 `rejected`

Judge 接口很小：`BaseJudge.decide(context) -> JudgeOutput`。目前只实现了 `LLMJudge`，复用 SAGA 的 `LLMClient` 和 models.yaml。**没有实现、也没有接入任何 JEV。**

## 3. 每类目标对应的真实动作

| 目标 | 动作 | 在哪里生效 |
|---|---|---|
| objective | `set_weight` / `drop` / `add_from_registry`（1–3 个操作） | 每轮 scorer creation 之后按名字重新应用，optimizer 用到的就是修改后的目标集合 |
| planning | 持久的策略指导文本（replace/append） | `GeneralPlanner.set_strategy_guidance()`，追加到第 2 轮及以后的目标规划 prompt 末尾。Planner 仍然自己决定目标，这与 Objective 的直接修改不同 |
| implementation | `rebind_scorer`（绑定到同类型的已注册 scorer）、`sanitize_outputs`（非有限值或越界值记为失败）、`rebuild_scorer`（需要 coding agent） | 每轮 scorer creation 之后重新应用。改绑定后用的是另一个 scorer 名字，会重新计算分数，不会命中旧 scorer 的缓存；同时清除当前种群上该目标的统计缓存。`rebuild_scorer` 生成带版本号的新 scorer（`<name>__mc_v<k>_it<t>`）。**当前配置下没有 Claude Code，所以记为 unsupported；这条路径的接线只做过单元级检查，没有用真实 coding agent 跑过** |
| optimization_workflow | 只开放 optimizer 声明的 `tunable_params()`（numeric GA：mutation_sigma、mutation_prob、crossover_rate、elite_fraction、tournament_size），外加 loop 参数 `random_candidate_ratio` | optimizer 参数通过 `set_tunable_params()` 写到主 optimizer，在每代的 `optimize()` 里读取；`random_candidate_ratio` 写入 `loop_config`，由 `_optimization_phase` 读取。这些参数都不改变评估额度 |
| no_change | 不做任何修改 | 已接受状态不变，原生 SAGA 流程照常进入下一轮（Planner 正常拿到 Analyzer 报告）。它不是终止 |

## 4. 独立验证与 accept/reject

```
当前已接受状态 S --Judge--> 候选 S' = S + change（现场校验）
    隔离执行：candidate trial(S') 与 baseline trial(S)
        同一个起始种群（深拷贝）、同一组种子、同样的 optimizer 评估额度（一个完整的"下一轮"）
        planning 目标：克隆 Planner（深拷贝 message_history）+ 新建 scorer creator 实例，两侧都重新规划
    验证器只用 validation split 从候选表示重新计算质量，不读 candidate.scores
    accept iff 所有试验成功 且 没有违反约束 且 预算未超 且 mean(cand) - mean(base) > 0 且 >= min_improvement
```

- 验证器（`modules/numeric_tasks/validators.py`）衡量的是**系统自己排在最前面的 5 个候选的真实质量**。目标被重新定义或缩放时，被重算的仍是"系统选中的候选"的真实质量，所以分数膨胀骗不过它（见测试 `test_rescaled_objective_cannot_pass_validation`：把目标放大 1000 倍，delta=0，被拒绝）。
- validation、test、calibration 三个 split 使用相互独立的随机抽样。Controller 只能用 validation（代码中写死，测试里的 mock 验证器还会断言这一点）；test 只在 A/B 结束后由实验脚本用于报告。
- 隔离与回滚：
  - 试验从不写 KnowledgeManager，不调用 `_planning_phase`。
  - 用的是克隆的 Planner，以及新建的 scorer creator 和 optimizer 实例。
  - 试验前保存、试验后恢复 Python 和 numpy 的全局 RNG。
  - 试验中新注册的 scorer 会被注销（只保留被接受的重建 scorer），试验目录会被删除。
  - 测试会对比拒绝前后的指纹：Planner 历史、KM、种群（含分数缓存）、scorer 注册表、optimizer 参数、loop_config、已接受状态。
- Planning 试验和主流程共用 Planner 的 LLM client，所以这些调用计入 `api_usage_statistics.json` 的 planner 项；决策日志里会把它们分别记到 candidate 和 validation 成本中。

## 5. 记录与成本覆盖范围

- `runs/<run_id>/outputs/meta_controller_decisions.jsonl`：每轮一条记录，包括 task_id、seed、iteration、模式、Judge 配置（不含凭据）、决策字段、change 指纹、候选状态、验证前后指标、outcome 及原因、judge/candidate/validation/total 四段成本（调用、tokens、cost、评估数、耗时）、预算上限/已用/剩余。写入前会对类似密钥的字符串做脱敏。
- RunTracker 中有 `meta_controller` 和 `meta_controller_apply` 两类 phase；结束时生成 `meta_controller_summary.json`，配置了预算时还会生成 `budget_usage.json`。
- 统计口径：
  - 只统计经过 `LLMClient` 的调用。共用的 client 只计一次。
  - `call_count` 只计成功的调用；被重试的失败尝试不计入。
  - 没有 usage 信息的响应计入 `calls_missing_usage`，此时 tokens 记为 **null**，不是 0。
  - coding agent 和 candidate analyzer 合并进来的用量只有 tokens，没有调用次数（本配置中两者都关闭）。
  - oracle 评估数要求 optimizer 提供 `num_evaluations`，否则记为 null。

## 6. 测试与复现

环境（远程 Gautschi）：`/scratch/gautschi/ou57/conda-envs/saga`，Python 3.11。其中 mcp 1.14.0 和 pydantic 2.11.7 与 SAGA 的 Docker 镜像一致；mcp 2.x 会破坏 SAGA 的 import。

```bash
cd /scratch/gautschi/ou57/SAGA
export PATH=/scratch/gautschi/ou57/conda-envs/saga/bin:$PATH     # SAGA 用 PATH 里的 python 启动 MCP scorer
python -m pytest tests/meta_controller -q                        # 离线测试：mock 组件 + 真实 MCP smoke，无需 key
python exps/meta_controller/calibrate_tasks.py                   # 重新生成固定成功阈值（A/B 之前已生成）
python exps/meta_controller/launch_ab.py --offline-mock          # MOCK 全流程检查（结果不是证据）

# 真实 A/B（需要 OPENAI_API_KEY）
cp exps/meta_controller/models.example.yaml llm_configs/models.yaml
cp exps/meta_controller/credentials.example.yaml llm_configs/credentials.yaml   # 里面只写环境变量名
sbatch exps/meta_controller/slurm_ab.sbatch                      # 或 bash exps/meta_controller/tmux_ab.sh
cat exps/meta_controller/results/grid_status.json                # 进度
cat exps/meta_controller/results/ab_summary.md                   # 汇总
python exps/meta_controller/run_numeric_ab.py --task spectral_signal --seed 0 --arm B   # 单个格子
```

## 7. A/B 设计与解读边界

- A = Controller 关闭（原始 SAGA 流程），B = Controller 开启（普通 LLM Judge）。3 个合成数值任务 × 2 个种子，每个 task-seed 都跑 A 和 B。
- 两组共享：任务、初始种群、初始目标、模块与模型、评价标准、种子、预算上限（调用/tokens/评估/墙钟时间）、试验额度、超时。B 的 Judge、候选试验和验证都从同一个预算里扣除。
- 当前环境的限制：
  - Implementer 的 coding agent 和 Analyzer 的 candidate analysis 需要 Claude Code + Docker，Gautschi 上没有，所以两组都关闭这两项。scorer 只能从已注册的 MCP scorer 中匹配，名字匹配加 LLM 匹配。
  - 因此这是 SAGA 的一个受限配置，不是完整的科研任务。
- 不报告统计显著性，不推断泛化能力。原始 SAGA 与 Judge 的对比也**不能**说明"按干预目标选择"优于"改错误发生的位置"。要支持后者，还需要"故障位置驱动"或"随机选择"等对照组。
- 一次任务分数的提高不等于实现了通用的递归自我改进。
