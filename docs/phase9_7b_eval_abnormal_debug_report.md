# Phase 9: 7B Same-Pipeline 诊断报告

> 状态：初步异常结果，需进一步排查

---

## 1. 实验目标

验证 EvoCode-Agent 后训练管线是否可迁移到 7B 模型。如果 7B 也能从同一管线中提升，说明方法具有 backbone 可迁移性。

## 2. 实验设计

使用与 3B 完全一致的数据和流程：
- 7B Base：原始能力基线
- 7B Step-SFT v2：4425 条 step-level SFT 数据，lr=2e-5
- 7B v2.1-clean：3899 条混合数据（70% original + 30% clean r2e），lr=2e-5

基座：Qwen2.5-Coder-7B-Instruct
方法：QLoRA 4-bit, LoRA r=16, alpha=32

## 3. 训练结果

7B Step-SFT v2 和 v2.1-clean 均正常完成训练，loss 下降，无 NaN。

## 4. 评测结果（New100）

| 模型 | Success | 问题 |
|---|---|---|
| 7B Base | 58.0% | 正常 |
| 7B Step-SFT v2 | **31.0%** | 严重退化 |
| 7B v2.1-clean | eval 空输出 | 评测异常 |

## 5. 诊断发现

### 5.1 7B Step-SFT v2：EOS 行为被破坏

调试测试显示：
- max_new_tokens=50: 输出 219 chars，**无 EOS**
- max_new_tokens=100: 输出 282 chars，有 EOS
- 但 eval 中 max_new_tokens=2048 时，模型输出打满 2048 tokens 不停
- 输出内容是 markdown 包裹的 JSON，action 字段是自由文本而非合法 tool name

根因：`completion_only_loss=False` 导致模型在整个序列（包括 prompt）上训练，7B 模型因此学会了不正确的 EOS 行为。

### 5.2 7B v2.1-clean：NO_EDIT 模式

调试测试显示：
- 输出长度正常（80-100 chars），JSON 格式正确
- 但 action 只有 `list_files` 和 `read_file`，从不 `edit_file`
- eval 中长 prompt 场景下产生空输出，可能与 prompt 长度或 EOS token 有关

### 5.3 7B Base：正常

输出 238-840 chars，edit_file 等 action 都有，JSON 格式正确。

## 6. 根因分析

**不是"管线不可迁移"，而是训练配置不适合 7B：**

1. **completion_only_loss=False** 对 7B 影响更大 — 模型在 prompt 上也计算 loss，干扰了 EOS 学习
2. **lr=2e-5 对 7B 可能过高** — 3B 用同样 lr 能训好，但 7B 更敏感
3. **数据配比未适配** — 3B 数据侧重"教格式"，7B Base 已经会格式，需要侧重"保留能力 + 修正失败"
4. **缺少 base behavior replay** — 没有混入 7B 自身的成功轨迹，导致原有能力被覆盖

## 7. 结论

直接复用 3B-oriented step-level SFT 数据与超参会损伤 7B backbone，说明 Agentic post-training 数据需要根据模型容量和基础能力重新配比。不能简单复制 3B pipeline 到 7B。

这不是最终迁移性结论。修复训练配置后（completion_only_loss=True、降低 lr、混入 base 成功轨迹），7B 有可能从同一管线中获益。

## 8. 下一步

1. 尝试 7B-safe SFT：lr=5e-6, completion_only_loss=True, 混入 7B base 成功轨迹
2. 如果 7B-safe SFT 有效，再做 7B read-to-edit
3. 如果无效，说明当前管线确实偏向小模型，需要重新设计数据配比
