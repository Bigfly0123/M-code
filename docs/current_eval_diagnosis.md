# 当前评测诊断报告

> 生成时间：2026-06-04
> 阶段：Phase A - 冻结当前结果

---

## 1. 当前评测结果

| 指标 | 3B Base | 3B SFT | 7B Base |
|---|---:|---:|---:|
| **Success Rate** | **50.0%** | 36.4% | **71.9%** |
| JSON Parse Success | 67.9% | 61.4% | 68.8% |
| Tool Valid Rate | 64.3% | 68.2% | 65.6% |
| Run Tests Before Edit | 3.6% | 9.1% | 0.0% |
| Read Target File | 21.4% | **68.2%** | 25.0% |
| Edit Target File | 67.9% | **93.2%** | 100.0% |
| Test Pass After Edit | 50.0% | 36.4% | **71.9%** |
| Avg Steps | 9.8 | 8.2 | 8.5 |
| Loop Rate | 53.6% | 54.5% | 59.4% |
| Unrelated Edit Rate | 0.0% | 0.0% | 0.0% |

**评测配置：**
- Benchmark: 28 test tasks
- Max steps: 10
- Temperature: 0 (greedy)
- Model: Qwen2.5-Coder-3B/7B-Instruct
- SFT: LoRA adapter (sft_qwen_3b_v2)

---

## 2. 核心发现

### 2.1 任务和环境是可行的
- 7B Base达到71.9%，说明benchmark、tools、Env-lite、prompt和parser基本能工作
- 3B Base已有50.0%成功率，说明任务不是只有大模型才能做

### 2.2 旧SFT是"流程增强、修复退化"
**SFT学到了：**
- Read Target File: 21.4% → 68.2% (+46.8%)
- Edit Target File: 67.9% → 93.2% (+25.3%)
- Tool Valid Rate: 64.3% → 68.2% (+3.9%)
- Run Tests Before Edit: 3.6% → 9.1% (+5.5%)

**SFT没学到/退化了：**
- Success Rate: 50.0% → 36.4% (-13.6%)
- Test Pass After Edit: 50.0% → 36.4% (-13.6%)
- JSON Parse Success: 67.9% → 61.4% (-6.5%)

### 2.3 所有模型Loop Rate都高
- 3B Base: 53.6%
- 3B SFT: 54.5%
- 7B Base: 59.4%

这说明loop不是某个模型的问题，而是Agent控制层也需要处理。

---

## 3. 旧SFT失败诊断

### 3.1 问题根源
当前SFT的问题不是单纯LoRA参数或数据量，而是：

**训练目标和真实Agent行目标不一致。**

具体包括：
1. trajectory-level数据没有拆成step-level action samples
2. 训练prompt和eval prompt可能不完全一致
3. action schema可能不统一
4. thought质量不足或为空
5. 训练数据可能过于模板化
6. 成功轨迹质量不足，3B自己的低质量轨迹占比过高
7. 没有把7B/mimo的高质量修复策略蒸馏给3B
8. 没有针对错误编辑、循环、跳过测试做偏好优化

### 3.2 结论
SFT把模型从"靠base模型自身代码能力解决问题"拉向了"机械执行训练轨迹模板"，导致编辑正确性下降。

---

## 4. 当前Action Schema

```json
{"action": "list_files", "arguments": {}}
{"action": "read_file", "arguments": {"path": "xxx.py"}}
{"action": "search_code", "arguments": {"keyword": "..."}}
{"action": "edit_file", "arguments": {"path": "xxx.py", "old": "...", "new": "..."}}
{"action": "run_tests", "arguments": {}}
{"action": "git_diff", "arguments": {}}
{"action": "submit_patch", "arguments": {}}
```

---

## 5. 当前PromptBuilder

位置：`evocode_orchard_lite/harness/prompt_builder.py`

关键规则：
1. Respond with exactly one JSON object, NO markdown formatting, NO code blocks
2. For edit_file, MUST provide all three parameters: "path", "old", "new"
3. The "old" text must be EXACTLY as it appears in the file
4. Always run tests before submitting
5. DO NOT use ```json or ``` blocks, just raw JSON

---

## 6. 后续方向

根据诊断结果，后续应该：

1. **重构数据协议**：从trajectory-level改为step-level prompt-completion
2. **使用teacher轨迹**：用7B/mimo成功轨迹蒸馏3B
3. **DPO偏好优化**：抑制错误编辑、跳过测试、循环等坏行为
4. **Runtime Guard**：防止无效循环和不合规流程

---

## 7. 产物清单

- `docs/current_eval_diagnosis.md` - 本文档
- `outputs/reports/current_metrics_table.md` - 指标表格
- `outputs/reports/experiment_registry.json` - 实验配置记录
