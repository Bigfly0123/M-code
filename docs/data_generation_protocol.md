# EvoCode-Orchard-Lite 数据生成协议：防覆盖、可续跑、可扩量

这份文档面向后续接手数据生成的 agent。

当前远端项目路径：

```text
/mnt/disk/mxf/projects/monesy/mini-swe-agent-main
```

## 当前问题

当前远端项目已经扩展到约 100 个 toy tasks，但 trace 文件只有约 114 个。

用户预期是类似：

```text
94 tasks x 2 rollouts = 188 traces
```

实际少很多的主要原因是：

```text
同一个 task 的多次 rollout 写到了同一个文件名：
outputs/traces/success/bugfix_001.trace.json
outputs/traces/failed/bugfix_001.trace.json
```

如果同一个任务跑多次：

```text
bugfix_001 rollout_001
bugfix_001 rollout_002
```

后一次会覆盖前一次。

所以后续数据生成必须先改 trace 存储规范，再重新生成数据。

## 核心原则

### 1. 每条 rollout 必须唯一

唯一键必须至少包含：

```text
run_id
task_id
rollout_id
model_name
temperature
seed
```

不要再用：

```text
{task_id}.trace.json
```

作为唯一文件名。

### 2. trace 先完整保存，再做清洗

不要边跑边覆盖、边跑边过滤。

正确流程：

```text
raw rollout traces
-> validation / quality check
-> clean SFT
-> credit SFT
-> DPO pairs
-> train / val / test split
```

### 3. 数据不是越多越好

目标是：

```text
干净 + 多样 + 可验证 + 可追溯 + 不重复
```

低质量数据越多越糟，尤其是 SFT。

### 4. 失败轨迹不能浪费

失败轨迹不要直接进入 SFT。

它们应该进入：

```text
DPO rejected
Credit-SFT productive segments
failure taxonomy
BAR-lite rollout grouping
```

## 推荐目录结构

以后不要继续把所有 trace 混在：

```text
outputs/traces/success/
outputs/traces/failed/
```

建议改成：

```text
outputs/
├── rollouts/
│   └── {run_id}/
│       ├── manifest.jsonl
│       ├── success/
│       │   └── bugfix_001/
│       │       ├── rollout_0001.trace.json
│       │       └── rollout_0002.trace.json
│       ├── failed/
│       │   └── bugfix_001/
│       │       ├── rollout_0003.trace.json
│       │       └── rollout_0004.trace.json
│       └── reports/
│           ├── run_summary.json
│           └── run_report.md
│
├── data/
│   ├── raw_sft_candidates.jsonl
│   ├── sft_clean.jsonl
│   ├── sft_rejected_noisy.jsonl
│   ├── credit_sft_data.jsonl
│   ├── dpo_pairs.jsonl
│   └── dataset_stats.json
│
└── reports/
    ├── dataset_quality_report.md
    └── data_generation_report.md
```

## 文件命名规范

每条 trace 文件名必须唯一。

推荐：

```text
rollout_{rollout_id}.trace.json
```

因为目录里已经有：

```text
{run_id}/{status}/{task_id}/
```

如果要扁平化保存，也可以用：

```text
{task_id}__r{rollout_id}__{model_slug}__t{temperature}__s{seed}.trace.json
```

例如：

```text
bugfix_001__r0002__qwen25_coder_7b__t07__s42.trace.json
```

禁止：

```text
bugfix_001.trace.json
```

用于多 rollout。

## manifest.jsonl 规范

每个 run 必须有一个 manifest。

路径：

```text
outputs/rollouts/{run_id}/manifest.jsonl
```

每一行记录一条 rollout：

```json
{
  "run_id": "20260531_qwen25_7b_t07",
  "task_id": "bugfix_001",
  "rollout_id": "0001",
  "status": "success",
  "trace_path": "outputs/rollouts/20260531_qwen25_7b_t07/success/bugfix_001/rollout_0001.trace.json",
  "model": "Qwen/Qwen2.5-Coder-7B-Instruct",
  "temperature": 0.7,
  "top_p": 0.95,
  "seed": 42,
  "max_steps": 10,
  "success": true,
  "reward": 1.0,
  "failure_type": null,
  "num_steps": 7
}
```

manifest 的作用：

- 防止重复跑
- 支持断点续跑
- 支持统计数据规模
- 支持后续构建 SFT / DPO / GRPO

## trace JSON 必须包含的字段

每条 trace 至少包含：

```json
{
  "run_id": "...",
  "task_id": "bugfix_001",
  "rollout_id": "0001",
  "model": "...",
  "model_config": {
    "temperature": 0.7,
    "top_p": 0.95,
    "seed": 42,
    "max_steps": 10
  },
  "success": true,
  "reward": 1.0,
  "failure_type": null,
  "steps": [],
  "final_patch": "...",
  "test_result": {},
  "metrics": {}
}
```

如果现有 `Trace` schema 没有这些字段，应扩展 schema，而不是用文件名硬推断。

## 原子写入，避免半文件

trace 保存必须使用原子写入：

```text
write rollout_0001.trace.json.tmp
fsync / close
rename to rollout_0001.trace.json
append manifest line
```

不要直接写最终文件，防止进程中断产生坏 JSON。

## 断点续跑策略

重新跑数据时，不要简单从头覆盖。

启动时读取：

```text
outputs/rollouts/{run_id}/manifest.jsonl
```

构造已完成集合：

```python
completed = {(task_id, rollout_id)}
```

如果已存在：

```text
(bugfix_001, 0001)
```

则跳过。

如果 trace 文件存在但 manifest 没记录，应进入 `orphan_traces` 检查，不要直接使用。

## 数据生成目标

最终不是只要 300-1000 条 raw traces，而是要 300-1000 条高质量训练样本。

建议目标：

```text
tasks: 100-300
rollouts_per_task: 3-5
raw traces: 300-1500
clean SFT: 300-1000
DPO pairs: 300-1000
Credit-SFT segments: 100-500
```

当前如果只有：

```text
100 tasks x 2 rollouts = 200 raw traces
```

也只是刚刚起步。

如果真实成功率约 70%，那么：

```text
200 raw traces -> 约 140 success traces
```

清洗后可能只剩：

```text
80-120 clean SFT
```

还不够正式训练，只适合 smoke training。

## 推荐生成批次

不要一次性乱跑。

分批跑：

### Run A：低温稳定行为

```text
temperature = 0.2
rollouts_per_task = 1
目标：获得 clean success traces
```

### Run B：中温多样行为

```text
temperature = 0.7
rollouts_per_task = 2
目标：获得多样成功和失败
```

### Run C：高温失败样本

```text
temperature = 1.0
rollouts_per_task = 1
目标：获得 DPO rejected / failure taxonomy
```

建议总量：

```text
100 tasks x (1 + 2 + 1) = 400 raw traces
```

如果扩展到 200 tasks：

```text
200 tasks x 4 = 800 raw traces
```

这才比较接近第一版训练数据规模。

## 任务扩展计划

当前 100 个任务可以继续扩，但要验证质量。

任务目标：

```text
短期：100 tasks 全部 valid
中期：200 tasks
较好：300 tasks
```

每个任务必须通过：

```bash
python -m evocode_orchard_lite.benchmark.validate_tasks
```

必须满足：

```text
initial_failed = true
edit_success = true
fixed_passed = true
```

任务类型要均衡。

建议至少覆盖：

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
csv_parsing
url_parsing
config_defaults
unit_conversion
time_delta
floating_precision
input_validation
error_message
```

每个 bug_type 至少 5-10 个变体。

## 数据生成脚本建议

新增脚本：

```text
evocode_orchard_lite/run_rollouts.py
```

命令示例：

```bash
python -m evocode_orchard_lite.run_rollouts \
  --run-id 20260531_qwen25_7b_t07 \
  --model Qwen/Qwen2.5-Coder-7B-Instruct \
  --tasks-file outputs/data/splits/train_tasks.txt \
  --rollouts-per-task 2 \
  --temperature 0.7 \
  --top-p 0.95 \
  --max-steps 10 \
  --seed 42 \
  --output-root outputs/rollouts
```

必须支持：

```text
--run-id
--tasks-file
--task bugfix_001
--rollouts-per-task
--temperature
--seed
--max-steps
--resume
--limit
--output-root
```

## run_rollouts.py 伪代码

```python
def main():
    args = parse_args()
    tasks = load_tasks(args.tasks_file or all_tasks)
    manifest = Manifest(args.output_root / args.run_id / "manifest.jsonl")
    completed = manifest.completed_keys()

    for task_id in tasks:
        for rollout_idx in range(args.rollouts_per_task):
            rollout_id = f"{rollout_idx:04d}"
            key = (task_id, rollout_id)
            if args.resume and key in completed:
                continue

            task = env.load_task(task_id)
            model = build_model(args)
            trace = agent.run(task)

            trace.run_id = args.run_id
            trace.rollout_id = rollout_id
            trace.model_config = {...}

            status = "success" if trace.success else "failed"
            trace_path = output_root / run_id / status / task_id / f"rollout_{rollout_id}.trace.json"
            atomic_write_json(trace_path, trace)
            manifest.append(trace_summary)
```

## workspace 也必须唯一

多 rollout 并行或断点续跑时，workspace 不能只用：

```text
outputs/workspaces/bugfix_001
```

否则不同 rollout 会互相覆盖工作目录。

改成：

```text
outputs/workspaces/{run_id}/{task_id}/rollout_{rollout_id}
```

例如：

```text
outputs/workspaces/20260531_qwen25_7b_t07/bugfix_001/rollout_0001
```

如果并行跑，还要避免多个进程写同一个 workspace。

## 清洗阶段

生成 raw traces 后，先清洗。

新增：

```text
evocode_orchard_lite/data_builder/filter_traces.py
evocode_orchard_lite/data_builder/filter_sft.py
evocode_orchard_lite/data_builder/inspect_dataset.py
```

### SFT clean 规则

只保留：

```text
success = true
tests_passed = true
patch_apply = true
tool_valid = true
format_errors = 0
unrelated_edit = false
至少一次 run_tests
至少一次 edit_file
最后 submit_patch
```

过滤：

```text
Missing required argument
Unknown tool
Response is not valid JSON
Old text not found
Path escapes workspace
hallucinated file
no final patch
wrong file edit
```

### DPO rejected 规则

失败轨迹可以保留为 rejected，但必须标注原因：

```text
FORMAT_ERROR
MISSING_ARGUMENT
UNKNOWN_TOOL
NO_TEST_BEFORE_SUBMIT
WRONG_FILE_EDIT
LOOP
TEST_STILL_FAIL
TIMEOUT
```

## DPO pair 构造

优先级：

```text
same task success vs same task failure
same bug_type success vs same bug_type failure
cross task success vs failure
```

每个 pair 必须记录：

```json
{
  "pair_id": "...",
  "task_id": "bugfix_001",
  "pair_type": "same_task",
  "chosen_trace": "...",
  "rejected_trace": "...",
  "rejected_failure_type": "LOOP"
}
```

不要大量构造 cross-task pair 来凑数量。

## BAR-lite 分组

当每个 task 有多条 rollout 后，可以做 BAR-lite。

按 task 聚合：

```text
0 success -> too_hard
all success -> too_easy
partial success -> informative
```

informative tasks 最适合：

```text
DPO
GRPO-lite
failure analysis
```

输出：

```text
outputs/data/rollout_groups.jsonl
outputs/data/informative_groups.jsonl
outputs/data/too_easy_groups.jsonl
outputs/data/too_hard_groups.jsonl
```

## 数据质量报告

每次生成数据后，必须生成：

```text
outputs/reports/data_generation_report_{run_id}.md
outputs/reports/dataset_quality_report.md
```

至少包含：

```text
task count
expected rollouts
actual trace files
missing rollouts
duplicate keys
success rate
failure type distribution
clean SFT count
DPO pair count
bad pattern count
avg steps
avg messages
bug_type distribution
difficulty distribution
```

特别检查：

```text
expected = task_count * rollouts_per_task
actual = manifest lines
trace_files = actual
```

如果三者不一致，必须停止并修复。

## 防覆盖验收标准

跑完一次 100 tasks x 2 rollouts 后，必须满足：

```text
manifest lines = 200
trace json files = 200
unique (task_id, rollout_id) = 200
no duplicate trace_path
no overwritten files
```

检查命令示例：

```bash
RUN_ID=20260531_qwen25_7b_t07
ROOT=outputs/rollouts/$RUN_ID

echo manifest
wc -l $ROOT/manifest.jsonl

echo trace files
find $ROOT -name "*.trace.json" | wc -l

echo unique keys
python - <<'PY'
import json
from pathlib import Path
root = Path("outputs/rollouts/20260531_qwen25_7b_t07")
keys = []
paths = []
for line in (root / "manifest.jsonl").read_text().splitlines():
    item = json.loads(line)
    keys.append((item["task_id"], item["rollout_id"]))
    paths.append(item["trace_path"])
print("rows", len(keys))
print("unique_keys", len(set(keys)))
print("unique_paths", len(set(paths)))
PY
```

## train / val / test split

数据扩展后必须按 task 切分。

不要按单条 trace 随机切。

建议：

```text
train: 70%
val: 15%
test: 15%
```

输出：

```text
outputs/data/splits/train_tasks.txt
outputs/data/splits/val_tasks.txt
outputs/data/splits/test_tasks.txt
```

训练只用 train tasks。

评测必须报告 test tasks。

## 推荐下一步执行顺序

后续 agent 应按这个顺序做：

```text
1. 修改 Trace schema，加入 run_id / rollout_id / model_config
2. 修改 TraceLogger，支持 outputs/rollouts/{run_id}/{status}/{task_id}/rollout_xxxx.trace.json
3. 修改 workspace reset，workspace 按 run_id/task_id/rollout_id 唯一
4. 实现 manifest.jsonl
5. 实现 run_rollouts.py，支持 --resume
6. 用 5 个任务 x 2 rollouts 做 smoke test
7. 验证 manifest lines = trace files = 10
8. 跑 100 tasks x 2 rollouts
9. 生成 data_generation_report
10. 清洗 SFT / DPO / Credit-SFT
11. 统计 clean 样本数量
12. 不够 300 clean SFT 前，不做正式训练，只做 smoke train
```

## 对当前覆盖事故的处理建议

当前旧目录：

```text
outputs/traces/success/
outputs/traces/failed/
```

里面的 114 条 trace 可以保留作参考，但不要再作为正式生成目录。

建议：

```text
mkdir -p outputs/archive
mv outputs/traces outputs/archive/traces_overwritten_legacy
```

如果不想移动，也至少不要继续写入这个目录。

新的数据全部写入：

```text
outputs/rollouts/{run_id}/
```

## 最终目标

第一版有效训练数据目标：

```text
tasks: 100-300
raw traces: 500-1000
clean SFT: 300-1000
Credit-SFT: 100-500
DPO pairs: 300-1000
```

在达到这个规模前：

```text
可以做训练代码 smoke test
不要期待模型能力显著提升
不要写“后训练显著提升代码修复能力”
```

达到这个规模后，再做：

```text
Qwen2.5-Coder-3B QLoRA SFT
Base vs SFT eval
SFT vs SFT+DPO eval
```

## 最重要提醒

```text
先修 trace 唯一性，再重新生成数据。
先清洗，再训练。
先检查 manifest，再相信样本数量。
```

不要再用 task_id 作为 trace 文件唯一名。
