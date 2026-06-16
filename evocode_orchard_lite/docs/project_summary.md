# M-code (EvoCode-Orchard-Lite) 项目总结

> 最后更新: 2026-06-16
> 当前最佳结果: **74% New100** (100个更难的held-out任务)

---

## 一、项目定位

M-code 是一个 **Coding Agent 后训练框架**，灵感来自 Orchard 架构。目标是用小模型（3B）通过后训练（SFT → DPO → 系统级优化）达到高通过率的代码修复能力。

核心思路：
- 不依赖大模型（不用GPT-4/Claude做teacher）
- 用 step-level SFT 训练 agent 行为
- 用 verifier（测试反馈）驱动 repair 循环
- 逐步归因失败类型，针对性优化

---

## 二、完整结果演进

| Phase | 方法 | New50 | New100 | 关键改动 |
|---|---|---|---|---|
| Baseline | 3B Base (无训练) | 52% | 38% | — |
| Phase 2 | Step-SFT v2 | 90% | 58% | Step-level prompt-completion SFT |
| Phase 3 | + Read-to-Edit SFT | 94% | 62% | 解决 NO_EDIT 问题 |
| Phase 4 | Step-SFT v2.1-clean | **98%** | 66% | Clean数据管线 + EOS修复 |
| Phase 6 | + DPO (patch-correctness) | — | 68% | 收益递减 |
| Phase 7 | + Repair v1 | — | 69% | 单轮repair循环 |
| **Phase 7.1** | **+ Repair v2 + Guard** | — | **74%** | **Failure-type-specific prompts** |

**从 38% 到 74%，绝对提升 +36%，相对提升 +95%。**

---

## 三、各阶段详细分析

### Phase 2: Step-Level SFT（38% → 58%）

**核心发现：** Trajectory-level SFT 失败，Step-level SFT 成功。

- Trajectory-level: 把整条轨迹作为一个样本训练 → 模型学不到逐步决策
- Step-level: 每个 (prompt, action) 对独立训练 → 模型学会单步推理
- 关键修复：LoRA 加载方式（`is_trainable=True` + `requires_grad=True`，而非 `get_peft_model()`）

### Phase 3: Read-to-Edit Transition（58% → 62%）

**问题：** 模型只读文件不编辑（NO_EDIT 失败模式）

**方案：** 构建 read→edit 转换训练数据
- 从成功轨迹中提取"读文件 → 编辑文件"的转换模式
- 训练模型在读完文件后产出 edit_file 动作

**教训：** 数据管线必须过滤 train-only split，否则污染评估。

### Phase 4: v2.1-clean（62% → 66%）

**关键修复：**
1. EOS token 处理：训练数据添加 `eos_token`，`completion_only_loss=True`
2. 数据格式：`apply_chat_template(messages)` 后追加 completion 作为 assistant message
3. 路径解析：`path.relative_to(task.workspace.resolve())`

**结果：** New50 达到 98%，New100 达到 66%。

### Phase 6: DPO（66% → 68%）

**尝试了多种 DPO 策略：**
- Patch-correctness DPO：用正确/错误 patch 对训练
- DPO-v3-small (159 pairs)、DPO-v3-balanced (287 pairs)
- 最高 68%，收益递减

**教训：** DPO 对小模型的收益有限，数据质量 > 数据数量。

### Phase 6.5: Skill Injection（66% → 62%，负面）

**尝试：** 注入5个技能（搜索、阅读、编辑、测试、调试）
**结果：** 技能注入反而降低性能（66% → 62%）
**教训：** 技能干扰了模型已学会的行为模式。

### Phase 7: Verifier-Guided Repair v1（65% → 69%）

**方案：** 首轮失败后，用测试反馈构建 repair prompt，再跑一轮

**结果：**
- 首轮 65%，repair +4，最终 69%
- 3/4 repair 成功来自 NO_EDIT 类型
- **问题：** 11个 OTHER 失败 repair 后变成 NO_EDIT（repair prompt 让模型过于保守）

### Phase 7.1: Repair v2 + No-Edit Guard（69% → 74%）

**改进：**
1. **Failure-type-specific prompts：** 针对 NO_EDIT / TEST_STILL_FAIL / OTHER 三种失败类型设计不同 repair prompt
2. **No-Edit Guard：** 如果 repair 阶段仍无编辑，触发 forced_edit_repair

**结果：**
- Repair 成功率翻倍：v1=4/35 (11%) → v2=8/34 (24%)
- OTHER→NO_EDIT 回归消除：v1=11例 → v2=2例
- Forced-edit Guard：0/6 成功（负结果）
- **最终 74/100 (74%)**

---

## 四、关键技术突破

### 1. Step-Level SFT（而非 Trajectory-Level）

```
❌ Trajectory: "给定任务描述，生成完整轨迹" → 学不到
✅ Step: "给定当前观察，生成下一步动作" → 学会了
```

### 2. LoRA 加载方式

```python
❌ model = get_peft_model(base, config)  # 覆盖已训练权重
✅ model = PeftModel.from_pretrained(base, adapter_path, is_trainable=True)
   for p in model.parameters(): p.requires_grad = True
```

### 3. Failure-Type Classification

```python
def classify_failure(trace):
    if not has_edit:        return "NO_EDIT"
    if not has_tests:       return "NO_TEST_AFTER_EDIT"
    if not test_passed:     return "TEST_STILL_FAIL"
    return "OTHER"
```

### 4. Failure-Type-Specific Repair Prompts

```
NO_EDIT → "CRITICAL: You MUST make a source-code edit"
TEST_STILL_FAIL → "Your patch did not fix the test. Re-read and try differently"
OTHER → "Re-read source, run tests, then make minimal edit"
```

---

## 五、失败分析（当前瓶颈）

### 剩余 26/100 失败任务分布

| 类型 | 数量 | 占比 | 原因 |
|---|---|---|---|
| OTHER | 19 | 73% | 模型编辑了但编辑错误 |
| NO_EDIT | 6 | 23% | 模型无法产出编辑 |
| TEST_STILL_FAIL | 1 | 4% | 编辑后测试仍失败 |

### OTHER 二级分类计划（Phase 7.2）

| 子类型 | 定义 | 策略 |
|---|---|---|
| PATCH_WRONG_LOGIC | 语法正确但逻辑错误 | 更好的 test-output 推理 |
| PARTIAL_FIX | 修复了部分测试 | 多轮 repair 循环 |
| WRONG_FILE | 编辑了错误文件 | 更好的文件识别 prompt |
| OFF_BY_ONE | 边界错误 | 边界检查 prompt |
| REGRESSION | 修复破坏了已有测试 | 回归感知 repair |

---

## 六、关键教训

1. **数据管线比模型更重要**：v2.1-clean 的提升主要来自修复数据管线 bug，而非模型改动
2. **Step-level 是正确的训练粒度**：Trajectory-level 对小模型无效
3. **DPO 收益递减**：小模型的 DPO 收益有限，不如 system-level 优化
4. **技能注入有害**：已训练好的模型不需要额外技能注入
5. **Failure-type-specific > Generic**：针对性 prompt 比通用 prompt 效果好一倍
6. **负结果也是结果**：Forced-edit Guard 无效，但值得记录

---

## 七、技术栈

| 组件 | 技术 |
|---|---|
| 基础模型 | Qwen2.5-Coder-3B-Instruct |
| 训练方法 | QLoRA 4-bit SFT + DPO |
| LoRA | rank=16, alpha=32, target_modules=q_proj,v_proj |
| Agent 框架 | mini-swe-agent (modified) |
| 工具协议 | MCP-style (read_file, edit_file, run_tests, search_code) |
| 评估 | 400个bug-fix任务 (50 New50 + 100 New100 + 250 train) |
| GPU | NVIDIA RTX A6000 (48GB) |

---

## 八、项目文件结构

```
evocode_orchard_lite/
  training/           # SFT 和 DPO 训练脚本
    train_step_sft_v21_clean.py  # 主力训练脚本
    train_dpo_patch_correctness.py
  eval/               # 评估脚本
    eval_repair_v2.py  # Phase 7.1 评估
  data_builder/       # 数据管线
    build_step_sft_v21_clean.py
    mine_dpo_v3_full.py
  tools/              # MCP-style 工具
    basic_tools.py
  harness/            # Agent 循环
  env_lite/           # 代码修复环境
  docs/               # 阶段报告和规划
```

---

## 九、GitHub

仓库: https://github.com/Bigfly0123/M-code

| Commit | 描述 |
|---|---|
| ca32397 | Phase 7.1: Repair v2 achieves 74% New100 |
| 0026d61 | Phase 7: Verifier-Guided Repair 69% New100 |
| 2715900 | Phase 9: 7B diagnostic |
| 015d4ae | Phase 7.1: Skill injection A/B test |

---

## 十、下一步路线

### 短期（Phase 7.2）
- OTHER Failure Decomposition：对19个OTHER失败做二级分类
- 针对每个子类型设计专门的 repair 策略
- 目标：74% → 78-80%

### 中期（Phase 8）
- MCP Tool Protocol 升级：更丰富的工具接口
- 多轮 repair 循环（当前最多3轮，可扩展到5轮）

### 长期（Phase 9-10）
- Multi-Agent：repair agent + review agent 协作
- Self-Improvement：从失败轨迹中自动学习
- 7B 模型迁移（需要解决 EOS/loss mask 问题）

---

## 附录：关键数字速查

```
模型参数:           3B (QLoRA 4-bit, ~2GB VRAM)
训练数据:           ~2000 step-level samples
SFT 训练时间:       ~30 min (A6000)
评估任务:           New50 (50), New100 (100)
单轮评估时间:       ~40 min (100 tasks)
Repair 评估时间:    ~80 min (100 tasks, 2-3轮)
最佳 New50:         98% (v2.1-clean)
最佳 New100:        74% (Repair v2)
Repair 增益:        +8 tasks (11% → 24% success rate)
```
