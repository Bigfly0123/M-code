# EvoCode-Orchard-Lite 后续改造计划

这份文档面向后续接手项目的 agent。

当前项目在用户本地 Windows 机器开发：

```text
E:\its4learning\mini-swe-agent-main
```

本地机器没有 GPU。所有需要大模型推理、LoRA/QLoRA、DPO、GRPO 的实验，后续需要通过 SSH 到用户的 GPU 服务器执行。

## 当前状态

第一层已经完成：

```text
Env-lite + Toy Benchmark + Structured Tools + Trace Logger + Eval + SFT Data Builder
```

已验证：

```bash
python -m evocode_orchard_lite.benchmark.validate_tasks
python -m evocode_orchard_lite.run_eval
python -m evocode_orchard_lite.data_builder.build_sft
```

当前结果：

- toy tasks: 10
- task validation: 10/10 valid
- scripted baseline: 10/10 success
- SFT samples: 10

关键产物：

```text
evocode_orchard_lite/docs/layer1_architecture.md
outputs/reports/task_validation.json
outputs/reports/baseline_report.md
outputs/data/sft_data.jsonl
outputs/traces/success/*.trace.json
```

`outputs/` 是运行产物，已被 `.gitignore` 忽略。

## 本地与服务器分工

### 本地 Windows 机器负责

- 改代码
- 维护 toy benchmark
- 跑 pytest 任务验证
- 跑 scripted baseline
- 生成 trace
- 生成 SFT/DPO 数据
- 写报告和 README
- 小规模 smoke test

本地默认命令：

```powershell
python -m evocode_orchard_lite.benchmark.validate_tasks
python -m evocode_orchard_lite.run_eval
python -m evocode_orchard_lite.data_builder.build_sft
```

### GPU 服务器负责

- 本地开源模型推理 baseline
- 批量 rollout
- LoRA / QLoRA SFT
- DPO training
- GRPO-lite experiments
- vLLM / transformers 推理服务
- 大规模 trace 生成

服务器实验前必须确认：

```text
1. SSH 地址、用户名、端口
2. 项目在服务器上的同步路径
3. Python/conda/uv 环境
4. CUDA 和 GPU 型号
5. 模型权重路径或 Hugging Face 下载权限
6. 是否允许联网下载依赖和模型
7. 实验输出目录和磁盘空间
```

不要假设本地有 GPU。

## 总体阶段

```text
Phase 2: 真实 LLM Baseline
Phase 3: 扩展 Benchmark 到 30-50 个任务
Phase 4: SFT / Credit-SFT-lite 数据增强
Phase 5: DPO 数据构造
Phase 6: 服务器训练环境准备
Phase 7: LoRA / QLoRA SFT
Phase 8: Base vs SFT Eval
Phase 9: DPO Training
Phase 10: BAR-lite / GRPO-lite
Phase 11: Skill Self-Distillation
```

## Phase 2：真实 LLM Baseline

目标：用真实模型替换 `ScriptedModel`，让模型自己完成 toy tasks，收集真实成功和失败轨迹。

新增：

```text
evocode_orchard_lite/models/
├── __init__.py
├── base.py
├── litellm_chat_model.py
└── local_openai_model.py
```

第一版支持：

- `LiteLLMChatModel`: API 模型或 LiteLLM 路由
- `LocalOpenAIModel`: 连接服务器上的 OpenAI-compatible endpoint，例如 vLLM

模型接口：

```python
class Model:
    name: str

    def generate(self, prompt: str) -> str:
        ...
```

模型必须输出严格 JSON：

```json
{
  "thought": "...",
  "action": "run_tests",
  "arguments": {}
}
```

需要补：

- format error retry
- max format error limit
- real baseline runner
- failed trace collection
- real baseline report

建议新增：

```text
harness/controller.py
harness/format_error.py
run_real_baseline.py
eval/failure_analysis.py
```

失败类型至少包括：

```text
FORMAT_ERROR
NO_TEST_BEFORE_SUBMIT
WRONG_FILE_EDIT
OVER_EDIT
LOOP
GIVE_UP
HALLUCINATED_FILE
PATCH_APPLY_ERROR
TEST_STILL_FAIL
TIMEOUT
```

验收标准：

```text
1. 真实模型能跑完 10 个任务
2. 每个任务都有 trace
3. 报告包含成功率和失败类型分布
4. 失败 trace 可用于 DPO rejected 数据
```

## Phase 3：扩展 Benchmark

目标：扩展到 30-50 个 toy code repair tasks。

任务类型建议：

```text
boundary_condition
type_conversion
dict_key
off_by_one
none_handling
regex
date_comparison
return_format
argument_order
simple_algorithm
string_split_join
default_argument
case_sensitivity
path_handling
json_serialization
sorting_key
deduplication
rounding
boolean_logic
exception_handling
```

每个任务必须满足：

```text
1. 初始状态 pytest fail
2. scripted_fix 应用后 pytest pass
3. issue.md 说明清楚
4. metadata.json 包含 task_id, bug_type, test_command, target_files, scripted_fix
5. 只需小范围修改
```

验收命令：

```bash
python -m evocode_orchard_lite.benchmark.validate_tasks
```

## Phase 4：SFT / Credit-SFT-lite 数据增强

当前只有 scripted success trace -> SFT。

后续扩展为：

```text
scripted success traces
+ real model success traces
+ manually corrected failed traces
+ productive segments from failed traces
```

增强：

```text
data_builder/build_sft.py
data_builder/build_credit_sft.py
```

Credit-SFT-lite 简单规则：

```text
run_tests: +1
read_file target file: +1
search_code: +1
edit unrelated file: -2
format error: -1
```

输出：

```text
outputs/data/sft_data.jsonl
outputs/data/credit_sft_data.jsonl
```

## Phase 5：DPO 数据构造

新增：

```text
data_builder/build_dpo.py
```

数据来源：

```text
chosen:
- scripted success trace
- real model success trace
- manually corrected trace
- high-quality productive segment

rejected:
- format error trace
- no-test-before-submit trace
- wrong-file-edit trace
- loop trace
- test-still-fail trace
```

输出格式：

```json
{
  "prompt": "...",
  "chosen": "...",
  "rejected": "...",
  "task_id": "bugfix_001",
  "chosen_source": "...",
  "rejected_source": "...",
  "rejected_failure_type": "NO_TEST_BEFORE_SUBMIT"
}
```

验收标准：

```text
1. 能生成 dpo_pairs.jsonl
2. chosen/rejected 来自同一 task 优先
3. 每个 pair 有 failure_type
4. 数据量至少 100 pairs 后再训练
```

## Phase 6：服务器训练准备

这一阶段需要 SSH 到 GPU 服务器。

同步项目建议：

```bash
rsync -av --exclude outputs --exclude __pycache__ ./ user@server:/path/to/evocode/
```

服务器检查：

```bash
nvidia-smi
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```

基础依赖：

```text
torch
transformers
datasets
accelerate
peft
trl
bitsandbytes
pytest
pyyaml
rich
typer
pydantic
```

模型优先级：

```text
Qwen/Qwen2.5-Coder-3B-Instruct
Qwen/Qwen2.5-Coder-7B-Instruct
deepseek-ai/deepseek-coder-6.7b-instruct
```

第一版不要用 14B+。

## Phase 7：LoRA / QLoRA SFT

新增：

```text
training/
├── train_sft.py
├── train_dpo.py
├── train_grpo.py
└── configs/
    ├── sft_qwen_3b.yaml
    └── sft_qwen_7b.yaml
```

第一版配置：

```yaml
model_name: Qwen/Qwen2.5-Coder-3B-Instruct
dataset_path: outputs/data/sft_data.jsonl
output_dir: outputs/models/sft_qwen_3b
max_seq_length: 4096
load_in_4bit: true
lora_r: 16
lora_alpha: 32
lora_dropout: 0.05
learning_rate: 2e-4
num_train_epochs: 2
per_device_train_batch_size: 1
gradient_accumulation_steps: 8
bf16: true
gradient_checkpointing: true
```

验收标准：

```text
1. 训练能完成
2. adapter 保存
3. training log 保存
4. SFT 模型能用于 real baseline runner
```

## Phase 8：Base vs SFT Eval

报告：

```text
outputs/reports/base_vs_sft_report.md
```

重点指标：

```text
task_success_rate
test_pass_rate
tool_valid_rate
format_error_rate
patch_apply_rate
run_test_before_submit_rate
unrelated_edit_rate
avg_steps
failure_counts
```

如果成功率没涨，也要检查行为指标是否改善。

## Phase 9：DPO Training

前提：

```text
SFT 模型已完成
dpo_pairs.jsonl 至少 100 pairs
```

目标：

```text
减少坏行为，而不是保证大幅提高成功率
```

输出：

```text
outputs/models/dpo_adapter
outputs/reports/base_sft_dpo_report.md
```

## Phase 10：BAR-lite / GRPO-lite

这是挑战层，不是第一优先级。

每个 task 采样 4 条 rollout：

```text
0 success -> too_hard
4 success -> too_easy
1-3 success -> informative
```

输出：

```text
outputs/data/rollout_groups.jsonl
outputs/data/informative_groups.jsonl
outputs/data/too_easy_groups.jsonl
outputs/data/too_hard_groups.jsonl
```

GRPO-lite 只在服务器上做。

建议：

```text
30-50 easy tasks
2-4 rollouts per task
max_steps 8-12
simple reward
```

reward：

```python
if format_error:
    return -0.3
if tests_passed:
    return 1.0
if patch_apply:
    return 0.2
if tool_valid:
    return 0.1
return 0.0
```

## Phase 11：Skill Self-Distillation

新增：

```text
skills/
├── skill_memory.py
└── retrieve.py

data_builder/build_skills.py
data_builder/build_skill_sd.py
training/train_skill_sd.py
```

Skill 示例：

```json
{
  "skill_id": "boundary_condition_repair",
  "source_task": "bugfix_001",
  "bug_type": "boundary_condition",
  "skill": "When equality boundary tests fail, inspect comparison operators such as <, <=, >, >=.",
  "recommended_actions": [
    "run failing test",
    "read target file",
    "make minimal edit",
    "rerun tests"
  ]
}
```

## 最终验收标准

最低完成：

```text
Layer 1 完整
30-50 toy tasks
real LLM baseline
SFT data
LoRA SFT
Base vs SFT report
```

中等完成：

```text
Credit-SFT-lite
DPO data
DPO training
Base vs SFT vs DPO report
```

高级完成：

```text
BAR-lite rollout selection
GRPO-lite smoke test
Skill Self-Distillation
Final ablation report
```

## 当前下一步建议

最合理的下一步是 Phase 2：

```text
接真实 LLM wrapper
-> 跑 10 个任务
-> 收集真实失败 trace
-> 生成 real_baseline_report.md
```

当前 Layer 1 已经能稳定产生理想轨迹，但项目真正的训练价值来自真实模型失败。

后续 agent 应优先实现真实模型 baseline，而不是马上写训练脚本。

## 给后续 agent 的注意事项

1. 不要删除或重写现有 `minisweagent/` 原项目代码。
2. 新功能优先放在 `evocode_orchard_lite/` 下。
3. 每次改动后至少跑：

```bash
python -m evocode_orchard_lite.benchmark.validate_tasks
python -m evocode_orchard_lite.run_eval
python -m evocode_orchard_lite.data_builder.build_sft
```

4. 服务器实验前必须确认 SSH 和 GPU 环境。
5. 不要在本地尝试大模型训练。
6. 训练输出和大规模 trace 放在 `outputs/`，不要提交。
7. 项目价值在闭环，不在把 runtime 写得很复杂。
