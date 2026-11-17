# Frozen Research Archive

Python 3.11 标准库研究归档。导入有理观测修订，冻结完整行队列，登记并执行分组稳健工具变量检验，保存完整置信集合。源更正影响后来冻结的研究；旧队列和报告在关闭重开后保持原值。无需安装依赖。

运行完整回归：`python3.11 -B -m unittest discover -s tests -t . -v`。
运行真实磁盘演示：`python3.11 -B -m research demo`。演示使用临时目录，输出三个手算研究、更正后的新研究，并重开核对旧报告。有限夹具及手算见 samples.json。

## 公开 API

```python
from research import Archive

with Archive("study.sqlite") as app:
    app.apply("import-1", [
        {"row_id": "a", "revision": 1,
         "payload": {"values": {"y": 0, "x": 1, "z": 1}, "group": "G"}}
    ])
    frozen = app.freeze({"row_ids": ["a"], "y": "y", "x": "x",
                         "z": ["z"], "w": []})
    task = app.create_task(frozen["cohort_id"], "1/2")
    report = app.execute(task)
    assert report.confidence_set.points == [0]
    assert app.read_report(task) == report
```

Archive 默认使用 SQLite 内存库，传入路径使用持久库。每个实例持有一个连接，面向单工作者调用；不在调用外开启事务。close 和上下文管理均可关闭。read_cohort(cohort_id) 返回独立的冻结值对象，供追溯使用。

apply(batch_id, revisions) 返回含 batch_id、inserted、replayed 的字典；后两项为 [row_id, revision] 列表。行、组及批次 ID 为非空字符串或非布尔整数，整数与字符串身份不同。每批行 ID 唯一，修订为正整数。载荷 values 是列名到整数、Fraction、有理字符串或 None 的映射；浮点与布尔数拒绝。group 可为 None，表示缺少分组。withdrawn 默认为 False，设 True 生成撤回修订；更高版本可恢复。列名为非空字符串且不能以 $ 开头。

同版同规范内容可重放，历史重放不回退当前指针；未曾接纳的逆序修订拒绝。同版不同内容或同批次 ID 不同规范请求整批拒绝。成功批次重放返回当时原回执。批次比较不依赖行输入次序或映射键次序；等值分数表示等价。输入随后修改不影响存储。修订历史、当前指针与回执一起提交。

freeze(spec) 返回 cohort_id、adopted 和 excluded。规格必须有 row_ids、y、x、z、w 五个字段；候选 ID 唯一。至多24个候选、8个采用组、2个工具列、4个干扰列；允许零工具列和空采用队列。所有角色名称必须不同并曾在本归档列目录出现；数值线性相关但名称不同的列合法。没有隐含截距。读取同一次当前源快照后，以完整行规则统一选择。排除原因优先顺序为 not_found、withdrawn、missing_group、missing:列名列表。采用记录携带修订和原组身份；采用行的完整载荷及所有排除记录被复制存储，之后不变。无效规格不产生队列。

create_task(cohort_id, c) 返回整数任务 ID，固定队列、列角色、非负有理阈值及检验版本 group-ar-v1；创建不计算。execute(task_id) 返回 AnalysisReport；成功任务再次执行返回原成果，不重算。read_report(task_id) 仅读取已发布成果，不计算。报告含 task_id、binding、confidence_set、audit、receipt。audit 保存行修订、组身份、坐标维数、干扰秩、有效工具秩以及各组有理仿射系数。

## 检验与结果

在同一冻结完整行集合上按 W 的列空间正交消除 y、x、Z，允许空、零列和秩亏 W。各组 s_g(b)=a_g-b d_g，其中 a_g=ΣZ_i y_i，d_g=ΣZ_i x_i，使用残差化坐标。组身份独立于行排序，零得分组仍保存。联合工具顺序贯穿加工和检验。

q(b)=Σs_g(b)，S(b)=Σs_g(b)s_g(b)ᵀ，接受条件为 qᵀS⁺q≤c，S⁺为 Moore–Penrose 逆。零矩阵统计量为零；奇异参数按该点实际秩计算。可逆有理工具列变换与相容冗余干扰列不改变集合。

ConfidenceSet.intervals 为全部互不重叠 Interval；每项有 left、right、left_closed、right_closed。无界端为 None，且开闭标志为 False。points 保存孤立点。空集的两列表均空，整条实轴为一个两端 None 的区间。有理端点直接为 Fraction；AlgebraicEndpoint 保存见证 polynomial（升幂有理系数）、全部不同实根中的零起始 index 以及 lo、hi 隔离界，宽度≤10⁻⁸。根身份包含多项式和序号；不同见证间用精确代数比较，不能直接比较显示小数或隔离区间重叠。

research.reports.sets.contains_parameter(set, rational) 查询有理点。
encode_confidence_set / decode_confidence_set 转换独立字典，保留端点类型、根身份和开闭性；research.records.rows.dumps / loads 将 Fraction 精确编码为分子分母 JSON。端点值对象不可变；报告列表、绑定和审计为独立对象。

## 错误与发布边界

非法载荷、冲突、规格越界、非法阈值抛 ValueError；未知队列或任务抛 KeyError；已有未成功任务读取抛 LookupError。输入拒绝不新增相应状态。计算异常原样传播。execute(task_id, fault=callback) 是受控失败接口，在 after_scores 和 before_commit 阶段调用 callback(stage)；回调只用于抛出异常，不应递归调用归档或提交事务。计算失败、提交前回调失败均不发布报告或审计，任务保持 pending，可在重开后重试。完整报告、得分审计、成功状态和唯一发布回执同事务提交。数据库连接提交本身失败时也由事务上下文回滚。

## 职责与回归

records 的 rows/revisions 定义规范内容及版本规则，batches 协调原子接纳，store 保存历史及回执，current 生成源快照。cohorts 的 specs/selection 执行规格与完整行规则，freeze/store/readback 保存并读取不可变队列。scores 的 design/projection/groups/bundles 建立共同坐标与可追溯组得分。inference 的 statistic、polynomials、isolation、endpoints、rank_cells 负责点检验与全实轴集合。reports 的 tasks、publish、sets、store、readback 负责固定任务、集合表示和完整成果发布读取。

tests/test_records.py 覆盖批次冲突、语义重放、逆序、输入复制及大整数修订。test_cohorts.py 覆盖缺测、撤回、缺组、未知身份、规格边界和恢复。test_inference.py 覆盖孤立点、零秩、持续秩亏、联合剪切、冗余干扰、交错分组、无界分支、代数根身份及独立点统计核账。test_reports.py 覆盖任务绑定、失败回滚重试、成功重放、更正后新旧研究并存、磁盘重开和读取隔离。
