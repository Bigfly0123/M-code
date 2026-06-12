# Phase 6 DPO 实验总结

> 生成时间：2026-06-12
> 阶段判断：DPO 分支进入边际收益递减阶段

---

## 1. DPO 实验目标

Phase 6 的目标是通过 DPO（Direct Preference Optimization）提升 3B 模型在 harder tasks 下的 patch correctness，解决 v2.1-clean 在 New100 上 66% 失败中主要的 TEST_STILL_FAIL 和 WRONG_PATCH 问题。

---

## 2. DPO 数据版本演进

| 版本 | Pairs 数 | 数据来源 | 去重方式 |
|---|---|---|---|
| DPO-sanity | 108 | 平衡采样 | task-level |
| DPO-main | 108 | balanced subset | task-level |
| DPO-main-v2 | 120 | +12 independent failures | task-level |
| DPO-v3-small | 159 | +mimo teacher rollouts | task-level |
| DPO-v3-balanced | 146 | v3 按类型 cap 平衡 | task-level |
| DPO-v3-full (未训练) | 331 | pair-level dedup | pair-level |

关键数据来源：
- 早期 mimo v2.5-pro rollouts（bugfix_001-200，67 个有 success+failure）
- 7B Base / 3B Base / v2.1-clean 失败轨迹（new100）
- mimo v2.5-pro teacher rollouts on new100（100 tasks，97.5% success）
- mimo v2.5-pro teacher rollouts on 351-400（50 tasks，78% success）
- scripted_fix 作为 chosen 替代

---

## 3. 评测集说明

| 评测集 | 任务范围 | 角色 | 是否参与 DPO 训练 |
|---|---|---|---|
| New50 easy | bugfix_201-250 | reference eval | 否 |
| New100 hard | bugfix_251-350 | reference eval | 部分是（用于 DPO pair 构造） |
| 351-400 | bugfix_351-400 | contaminated reference | 是（用于 DPO pair 构造） |
| 401-450 | bugfix_401-450 | clean independent eval | 否（尚未构建） |

注意：200 tasks 评测结果包含 351-400（已参与训练），不是完全 clean 的泛化证明。

---

## 4. 各 DPO 版本结果

### 4.1 New50 easy held-out

| 模型 | Success |
|---|---:|
| 3B Base | 46% |
| 3B SFT v2 | 54% |
| v2.1-clean | 98% |
| DPO-sanity | 98% |
| 7B Base | 82% |

DPO 在 easy tasks 上没有退化，也没有提升（已经 98%）。

### 4.2 200 tasks（new50 + new100 + 351-400）

| 模型 | Pairs | Success | TEST_STILL_FAIL | PATCH_ERROR |
|---|---:|---:|---:|---:|
| v2.1-clean (180 tasks) | — | 73.9% | 29 | 18 |
| DPO-main (180 tasks) | 108 | 75.0% | 26 | 19 |
| DPO-main-v2 | 120 | 67.0% | 40 | 26 |
| DPO-v3-small | 159 | 66.5% | 43 | 24 |
| **DPO-v3-balanced** | **146** | **68.0%** | **41** | **23** |
| 7B Base | — | — | — | — |

注：v2.1-clean 和 DPO-main 是 180 tasks 结果（不含 381-400），其余为 200 tasks。

### 4.3 DPO-v3-balanced vs DPO-main-v2

| 指标 | DPO-main-v2 | DPO-v3-balanced | 变化 |
|---|---:|---:|---:|
| Success | 67.0% | 68.0% | +1.0% |
| TEST_STILL_FAIL | 40 | 41 | +1 |
| PATCH_ERROR | 26 | 23 | -3 |

---

## 5. 为什么 DPO 提升有限

### 5.1 数据规模瓶颈

当前 DPO pairs 在 100-160 范围内反复尝试，结果在 66%-68% 之间波动。继续在小规模数据上调整，边际收益很低。

### 5.2 数据质量问题

- WRONG_PATCH 类 pairs 始终偏少（12-20 个）
- TEST_FEEDBACK_CORRECTION pairs 几乎没有
- PATCH_APPLY_STABILITY pairs 没有专门构造
- teacher chosen 轨迹覆盖不足（只有 bugfix_001-200 有完整 mimo rollouts）

### 5.3 模型能力上限

3B 模型在 harder bugs 下的 patch reasoning 能力有限。DPO 可以教模型"更敢改"，但教不了"改得对"——后者需要更强的代码推理能力。

### 5.4 Benchmark 难度

New100 + 351-400 的 harder tasks 已经接近 3B 模型的能力边界。DPO 在此难度下提升空间有限。

---

## 6. 当前最优版本

**DPO-v3-balanced** 是当前 DPO 分支的阶段最优版本：
- 146 pairs，failure type 分布最健康
- TEST_STILL_FAIL 80 + WRONG_PATCH 12 + NO_EDIT 10 + FORMAT_ERROR 10
- 200 tasks 上 68.0%

但不要把它写成"最终突破"或"DPO 成功解决 patch correctness"。

---

## 7. 当前瓶颈

当前主要瓶颈已经不是：

```
格式问题（已解决）
工具调用（已解决）
是否敢编辑（已解决）
```

而是：

```
harder tasks 下的 patch correctness
3B 模型的代码推理能力上限
复杂 bug 的修复策略
```

---

## 8. 下一步方向

### 8.1 暂停继续 DPO 小修

不再继续：
- 扩 DPO pairs 到 220-300
- 训 DPO-v4/v5
- 调整 balanced 策略

### 8.2 项目固化

优先做：
- 完善 README
- 整理最终项目报告
- 准备简历表达
- 整理面试 QA

### 8.3 技术下一步评估

| 方向 | 优先级 | 说明 |
|---|---|---|
| Skill Self-Distillation | 高 | 将成功轨迹沉淀为可复用 skill |
| GRPO-lite | 中 | 环境 reward RL，但需要更大 rollout 规模 |
| 更强 base model | 中 | 7B+ 模型可能直接解决 patch reasoning |
| Harder benchmark | 低 | 扩展更难的任务验证上限 |

---

## 9. 结论

DPO-v3-balanced 可以作为当前 DPO 分支的阶段最优结果。DPO 能带来小幅收益（+1%），但没有彻底解决 harder tasks 下的 patch correctness。在当前数据规模和模型能力下，DPO 分支进入边际收益递减阶段。

下一步应转向项目固化，将完整的技术路线（SFT 失败 → step-level SFT → NO_EDIT 修复 → DPO 尝试）整理为可展示的项目成果。技术层面可探索 Skill Self-Distillation 或更强 base model。
