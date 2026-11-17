# 修复说明：得分到置信集合链路

## 根因

1. **联合工具坐标被池化**（`research/scores/bundles.py`）：双工具时 `build_score_bundle`
   把各组仿射得分向量平均进第一个坐标、其余置零。联合坐标被压扁后，可逆有理工具列
   变换（如剪切）会改变池化结果，统计量随之改变，导致 joint_shear 与 joint_identity
   结论不同，且点统计量偏离投影恒等式。
2. **协方差被冻结在参考点**（`research/inference/rank_cells.py` 原 `_reference_quadratic`）：
   反演集合时用 b=0 处的 S(0) 代替 S(b)=Σs_g(b)s_g(b)ᵀ，并用 T(-1)、T(0)、T(1) 拟合
   二次边界。参考点秩亏（singleton 中 S(0)=0）时统计量被冻成 0，整条实轴被误收；
   首项系数为负的真实二次边界（disconnected）被拟合错，断开双射线被报成单个有界
   区间；双工具下真实的四次边界与奇异点更无法表示。

## 修复

- `bundles.py`：删除池化，联合仿射得分按原坐标贯穿加工、检验与审计。
- `rank_cells.py`：由组仿射得分精确构造边界多项式（有理系数、升幂）：
  - 一维：P(b)=q(b)²−c·S(b) 在处处判定（S(b)=0 蕴含 q(b)=0，与零矩阵统计量一致）。
  - 二维且 det S 不恒零：P(b)=qᵀadj(S)q−c·det S 判定满秩参数；奇异参数是 det S 的
    实根（奇异点处 q(b)∈range S(b)，故必为 P 的根，无需另合并事件），按该点实际秩用
    R(b)=qᵀSq−c·(tr S)² 判定。
  - 二维且 det S 恒零（持续秩亏）：R(b) 在处处判定。
  - 零工具：统计量恒零。
  事件为边界多项式的全部实根，单元接受性由精确符号判定给出，区间合并、孤立点、
  开闭性与端点表示沿用原 `sets.py`/`endpoints.py` 约定。`statistic_at` 原本即按点
  实际秩计算，未改动。

## 交接不变量

- 组身份与联合工具坐标从冻结队列经 ScoreBundle 到 audit 不变；可逆有理工具列变换
  与相容冗余干扰列不改变统计量与集合。
- 接受集合恰为 {b∈ℝ : q(b)ᵀS(b)⁺q(b) ≤ c}，S⁺ 为 Moore–Penrose 逆；零矩阵统计量为
  零；奇异参数按该点实际秩判定；协方差随参数变化。
- 空集、断开区间、无界端（None 且开闭标志 False）、孤立点、精确有理端点与
  AlgebraicEndpoint 根身份（见证多项式 + 序号 + ≤10⁻⁸ 隔离界）全部保留。
- 仅改动得分加工与集合反演；records/cohorts/reports 的存储、发布、失败回滚与重开
  读取语义不变，旧任务与旧报告保持原值。

## 验证

- `python3.11 -B incident.py --verify`：23 项原回归 + 5 项新增回归全过，5 个公开事故
  集合全部一致，输出 AR_SET_OK，退出 0。
- `python3.11 -B -m unittest discover -s tests -t . -v`：28 项全过（原断言未改）。
- `python3.11 -B -m research demo`：真实 SQLite 归档输出三个手算研究（disconnected
  双射线、singleton 孤立点 {0}、projection 空集），源更正后新研究接受 b=2，关闭重开
  后旧报告原值，输出 REOPEN_OK。
- 新增 `tests/test_regression.py`：有理奇异点按实际秩判定（T(0)=1、T(b≠0)=2，阈值
  3/2、1、1/2 三档）、四次边界断开集合内嵌秩亏点、事故阈值下剪切不变性与审计中的
  完整联合坐标。
- 额外抽查：300 个随机设计（1–6 行、1/2 工具、可选干扰列、阈值 0–3/2）上 11700 个
  有理探针，发布集合成员资格与 `statistic_at` 逐点定义全部一致，无不匹配。
