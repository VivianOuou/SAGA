# 修复前试跑（不计入 A/B）

真实 LLM（gpt-5-mini）+ 合成任务，代码版本 f836c1a/db0c587。三格（spectral_signal s0 B 完成；robust_design s0 A 完成；robust_design s0 B 在第 6 轮失败）。

停用原因，两处问题对两组/结果有系统性影响，修复后全部 12 格从头重跑：
1. 原版 BasicAnalyzer 的解析要求 `</reasoning>` 闭合标签；gpt-5-mini 在 17 次分析中有 12 次省略了结尾的闭合标签（finish_reason=stop，内容完整），
   导致反复重试，robust_design s0 B 在第 6 轮超过重试上限而终止（与 Controller 无关，两组都可能遇到）。
2. Controller 的 Objective 补丁按名字合并，后续提议会覆盖已接受的同名操作（例如在已接受的 add 之后 set_weight），
   造成 3 次提议被误判为 invalid_decision。

这些文件保留用于追溯，结果不作为 A/B 证据。
