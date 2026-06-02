# EvoCode-Orchard-Lite 数据清洗与扩展指南

这份文档面向后续接手项目的 agent。

目标：把当前少量、带噪声的轨迹数据，扩展成可用于 SFT / Credit-SFT / DPO / GRPO 的高质量数据集。

## 结论先行

数据不是越多越好。

更准确地说：

```text
高质量、多样、可验证、低噪声的数据越多越好。
低质量、重复、含错误工具调用、结果不可验证的数据越多越糟。
```

当前数据适合做：

- 训练脚本 smoke test
- SFT / DPO 数据构造流程验证
- trace schema 检查
- 小规模 overfit demo

当前数据不适合直接宣称：

- 模型代码修复能力明显提升
- DPO 已经学会偏好
- GRPO 已经有效优化 agent 行为

原因：当前数据规模太小，且部分 SFT 样本包含错误工具调用，例如：

```text
Missing required argument
Unknown tool
```

这类样本不能直接作为高质量 SFT 数据。

## 当前服务器项目路径

```text
/mnt/disk/mxf/projects/monesy/mini-swe-agent-main
```

常用检查命令：

```bash
cd /mnt/disk/mxf/projects/monesy/mini-swe-agent-main

python -m evocode_orchard_lite.benchmark.validate_tasks
python -m evocode_orchard_lite.run_eval
python -m evocode_orchard_lite.data_builder.build_sft
```

当前已有数据大致包括：

```text
outputs/data/sft_data.jsonl
outputs/data/sft_combined.jsonl
outputs/data/credit_sft_data.jsonl
outputs/data/dpo_pairs.jsonl
outputs/traces/success/*.trace.json
outputs/traces/failed/*.trace.json
outputs/reports/real_baseline_report.md
```

## 数据分层原则

不同数据用于不同训练阶段，不要混用。

### 1. Clean SFT 数据

用途：教模型标准工具调用格式和测试驱动修复流程。

只保留：

- 任务最终成功
- 所有 action JSON 可解析
- 工具名合法
- 工具参数合法
- 没有 `Missing required argument`
- 没有 `Unknown tool`
- 没有 `Response is not valid JSON`
- 没有幻觉文件
- 没有无关文件编辑
- 最终 tests passed
- patch 非空且只修改 target files

不要保留：

- 成功但中间有明显错误工具调用的轨迹
- 成功但绕过测试的轨迹
- 成功但改了无关文件的轨迹
- 失败轨迹整条进入 SFT

失败轨迹不能直接用于 SFT，但可以用于 DPO rejected 或 Credit-SFT 片段。

### 2. Credit-SFT 数据

用途：从失败轨迹中抽取“有价值的前半段行为”。

可保留片段示例：

```text
run_tests
-> read_file target file
-> search_code relevant keyword
```

不要保留：

```text
edit wrong file
unknown tool
missing required argument
repeat same failed action
submit without test
```

### 3. DPO 数据

用途：让模型偏向好行为、远离坏行为。

chosen：

- clean success trace
- manually corrected trace
- high-quality productive segment

rejected：

- format error trace
- missing argument trace
- unknown tool trace
- no-test-before-submit trace
- wrong-file-edit trace
- loop trace
- test-still-fail trace

优先同一 task 内配对：

```text
same task chosen success vs rejected failure
```

同一 task 不够时再跨 task 配对，但要记录 `pair_type = cross_task`。

### 4. GRPO / Rollout 数据

用途：在线优化或离线分析。

不要一开始追求大规模。

建议：

```text
每个 task 2-4 条 rollout
先跑 30-50 easy tasks
max_steps 8-12
reward 简单
```

## 第一阶段：清洗当前 SFT 数据

新增脚本：

```text
evocode_orchard_lite/data_builder/filter_sft.py
```

输入：

```text
outputs/data/sft_combined.jsonl
```

输出：

```text
outputs/data/sft_clean.jsonl
outputs/data/sft_rejected_noisy.jsonl
outputs/data/sft_clean.stats.json
```

过滤规则：

```python
BAD_PATTERNS = [
    "Missing required argument",
    "Unknown tool",
    "Response is not valid JSON",
    "Path escapes workspace",
    "Old text not found",
]

ALLOWED_ACTIONS = {
    "list_files",
    "read_file",
    "search_code",
    "edit_file",
    "run_tests",
    "git_diff",
    "submit_patch",
}
```

每条 SFT 样本检查：

```text
1. messages 存在且长度 > 2
2. assistant 消息必须是 JSON
3. assistant JSON 必须包含 thought, action, arguments
4. action 必须在 ALLOWED_ACTIONS
5. arguments 必须是 dict
6. tool 消息不能包含 BAD_PATTERNS
7. 最后必须包含 submit_patch
8. 至少包含一次 run_tests
9. edit_file 的 path 必须属于 target_files
```

统计字段：

```json
{
  "input_samples": 34,
  "clean_samples": 0,
  "rejected_samples": 0,
  "reject_reasons": {
    "bad_observation": 0,
    "invalid_action_json": 0,
    "unknown_action": 0,
    "missing_submit": 0,
    "missing_run_tests": 0,
    "unrelated_edit": 0
  }
}
```

验收标准：

```text
filter_sft.py 能跑通
sft_clean.jsonl 只包含干净轨迹
sft_rejected_noisy.jsonl 保留被过滤样本和原因
```

## 第二阶段：扩展 Benchmark 到 100 个任务

当前 30 个任务太少。

建议目标：

```text
短期：100 个 toy tasks
中期：200-300 个 toy tasks
```

不要只堆同一种 bug。需要多样性。

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
list_mutation
set_operations
csv_parsing
url_parsing
config_defaults
unit_conversion
time_delta
floating_precision
input_validation
error_message
```

每个 bug 类型建议至少 5 个变体。

每个任务必须包含：

```text
benchmark/tasks/bugfix_xxx/
├── repo/
│   ├── target_file.py
│   └── tests/test_xxx.py
├── issue.md
└── metadata.json
```

`metadata.json` 必须包含：

```json
{
  "task_id": "bugfix_031",
  "bug_type": "input_validation",
  "language": "python",
  "test_command": "python -m pytest tests/test_xxx.py",
  "target_files": ["target_file.py"],
  "difficulty": "easy",
  "timeout": 30,
  "scripted_fix": {
    "path": "target_file.py",
    "old": "...",
    "new": "..."
  }
}
```

任务验收：

```bash
python -m evocode_orchard_lite.benchmark.validate_tasks
```

必须满足：

```text
initial_failed = true
edit_success = true
fixed_passed = true
```

## 第三阶段：增加难度分层

不要所有任务都 easy。

建议比例：

```text
easy: 60%
medium: 30%
hard: 10%
```

定义：

### Easy

- 单文件
- 单行修复
- 测试直接指出错误
- scripted_fix 一次 replace 可完成

### Medium

- 单文件或双文件
- 需要读 2-3 个函数
- 需要理解输入输出格式
- 可能需要新增简单条件判断

### Hard

- 多文件
- 需要跨模块理解
- 需要新增 helper
- 需要多处小改

第一版训练以 easy + medium 为主，hard 先用于 eval。

## 第四阶段：生成更多真实模型轨迹

扩展任务后，运行真实 baseline。

建议每个 task 多跑几次：

```text
rollouts_per_task = 2-4
temperature = 0.2 / 0.7 各一批
max_steps = 8-12
```

输出目录建议：

```text
outputs/traces/real_baseline/run_001/success/
outputs/traces/real_baseline/run_001/failed/
outputs/reports/real_baseline_run_001.md
```

每条 trace 必须保留：

- model name
- temperature
- max_steps
- task id
- success
- reward
- failure_type
- final_patch
- test_result
- steps

## 第五阶段：数据目标量

### 最低 smoke train

```text
clean SFT: 30-50
DPO pairs: 30-50
```

用途：只验证训练代码。

### 第一版有效 SFT

```text
clean SFT: 300-1000
Credit-SFT: 100-300
DPO pairs: 300-1000
tasks: 100-300
```

用途：可能改善工具格式、测试驱动流程和部分 toy task 成功率。

### 更可靠版本

```text
clean SFT: 2000+
DPO pairs: 2000+
tasks: 300-1000
多模型 rollout + 人工/脚本清洗
```

用途：更可能看到稳定提升。

## 第六阶段：训练前数据检查

训练前必须跑数据检查脚本。

建议新增：

```text
evocode_orchard_lite/data_builder/inspect_dataset.py
```

检查：

```text
样本数
平均 messages 数
平均 token 长度
action 分布
bug_type 分布
difficulty 分布
bad pattern 数量
重复样本比例
target_file 覆盖率
run_tests 出现率
submit_patch 出现率
```

训练前最低要求：

```text
bad pattern = 0
submit_patch rate > 95%
run_tests rate > 95%
unknown action = 0
unrelated edit = 0
```

## 第七阶段：切分 train / val / test

不能只在训练任务上评测。

建议按 task 切分：

```text
train: 70%
val: 15%
test: 15%
```

按 `task_id` 切，不要按单条样本随机切。否则同一 task 的相似轨迹会泄漏到 test。

新增：

```text
outputs/data/splits/train_tasks.txt
outputs/data/splits/val_tasks.txt
outputs/data/splits/test_tasks.txt
```

训练数据只用 train tasks。

最终报告必须包含 test tasks 上的评测结果。

## 第八阶段：DPO 数据质量

DPO 不是越多越好，pair 质量非常重要。

优先 pair：

```text
同一 task:
clean success trace vs failed trace
```

其次：

```text
同一 bug_type:
clean success trace vs failed trace
```

避免：

```text
完全不相关 task 的 chosen/rejected 硬配
```

每个 rejected 必须有明确坏行为：

```text
FORMAT_ERROR
MISSING_ARGUMENT
UNKNOWN_TOOL
NO_TEST_BEFORE_SUBMIT
WRONG_FILE_EDIT
LOOP
TEST_STILL_FAIL
```

如果 rejected 只是“最后没成功但过程还可以”，更适合用于 Credit-SFT，而不是 DPO rejected。

## 服务器训练建议

当前服务器有 RTX A6000 48GB，但显存占用可能较高。

训练前先查：

```bash
nvidia-smi
```

如果空闲显存 < 24GB：

- 优先 Qwen2.5-Coder-3B QLoRA
- 降低 max_seq_length 到 2048
- batch size = 1
- gradient accumulation

如果有完整 48GB 空闲：

- 可尝试 Qwen2.5-Coder-7B QLoRA
- max_seq_length 4096

不要在当前小数据上跑大模型长训练。先 smoke train：

```text
1 epoch
小 batch
确认 loss 正常下降
确认 adapter 可保存/加载
确认 eval pipeline 能跑
```

## 推荐下一步执行顺序

后续 agent 按这个顺序做：

```text
1. 实现 filter_sft.py
2. 清洗当前 sft_combined.jsonl
3. 实现 inspect_dataset.py
4. 扩展 benchmark 到 100 tasks
5. validate_tasks 全部通过
6. 跑真实 baseline 多 rollout
7. 重新构造 clean SFT / Credit-SFT / DPO
8. 做 train/val/test split
9. 做 SFT smoke train
10. 做 Base vs SFT eval
```

不要跳过清洗直接训练。

## 判断训练是否“有用”

训练后不要只看 task success。

必须同时看：

```text
tool_valid_rate
format_error_rate
run_test_before_submit_rate
patch_apply_rate
unrelated_edit_rate
avg_steps
failure_type distribution
```

如果 task success 没明显提升，但：

```text
format_error 降低
run_tests 更稳定
submit_patch 更规范
无关编辑减少
```

也说明 SFT 有一定作用。

如果所有指标都没变，通常原因是：

- 数据太少
- 数据太脏
- prompt/eval 不一致
- 训练学习率不合适
- 训练和推理模板不一致
- 模型本身已经会这些 toy task

## 最重要的原则

```text
先清洗，再扩量；
先验证，再训练；
先 smoke test，再正式实验；
先行为指标，再成功率；
失败轨迹不要浪费，但也不要直接塞进 SFT。
```
