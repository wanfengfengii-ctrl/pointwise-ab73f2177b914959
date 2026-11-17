'# 公开事故与核验入口\n\n现有归档的观测修订、完整行冻结、固定任务、报告保存及重开读取仍按 README.md 工作。本题修复既有检验，不新增估计器、p 值或交互界面。README.md 的全部数值、身份、精度和异常规则继续适用；原 tests/ 全部保留。\n\n## 可复算事件\n\n运行 `python3.11 -B incident.py`，逐例输出已发布的完整集合及有理点成员资格；业务偏差输出 AR_SET_MISMATCH 并退出 1。计算异常原样传播，不会被包装成该业务标记。所有样例通过后退出 0。该入口使用 Archive 的内存数据库；真实持久化与重开由原回归和演示核验。\n\n1. singleton：一行 y=0、x=1、Z=1，无 W、仅一组，c=1/2。b=0 时 T=0，其余实数 T=1，集合恰为 {0}。\n2. disconnected：两组各一行，(y,x,Z)=(1,0,1)、(0,-1,1)，c=3/2。T=(1+b)^2/(1+b^2)，集合为 (-∞,2-√3]∪[2+√3,+∞)。b=2 必须拒绝，正负远端均接受。\n3. joint_identity：两组 y=1、x=0，工具向量为 (1,0)、(0,1)，c=19/10。任意 b 的 T=2，集合为空。joint_shear 将工具向量换为 (1,0)、(1,1)，这是可逆有理列变换，集合仍为空。\n4. algebraic_rank_point：两组的联合仿射得分分别为 (b,1)、(2,b)，由 incident.py 中四行观测生成，c=1/2。b²≠2 时 T=2；b=√2 时 T>1/2；b=-√2 时 T<1/2。因此完整集合只有 {-√2}，必须保存精确代数根身份。\n\n当前故障版本在上述事件中发布了错误集合。修复范围仅为现有得分加工到完整集合反演链路。无干扰、常秩、空采用队列及零工具等已有行为同样保持契约语义。\n\n## 交付与运行\n\n保留公开 API、数据格式、全部原测试和原断言，补充必要业务回归及简短的根因、交接不变量和实际验证说明。可全量重算，仍按 README.md 的 24 候选、8 组、2 工具、4 干扰列边界工作；不要求增加性能、并发或迁移能力。\n\n.pointwise-runtime.json 是平台读取的运行清单：version 为 1，kind 为 cli，setup 是命令参数数组的列表，verify 和 demo 是单条命令的参数数组。当前 verify 为 `python3.11 -B incident.py --verify`，执行全部未修改的原回归并核对公开事故，失败保留非零退出码；单独原套件命令仍为 `python3.11 -B -m unittest discover -s tests -t . -v`。demo 继续执行 `python3.11 -B -m research demo`，展示真实 SQLite 归档、源更正和关闭重开后的旧研究，而不是打印预置结果。\n'
"""Observable confidence-set incidents; no implementation oracle."""
import sys
from fractions import Fraction as F
from research import Archive
from research.records.rows import dumps
from research.reports.sets import contains_parameter, encode_confidence_set


def observation(row_id, group, **values):
    return dict(row_id=row_id, revision=1, payload=dict(group=group, values=values))


def cases():
    return [
        dict(name="singleton", rows=[observation("a", "G", y=0, x=1, z=1)],
             z=["z"], threshold="1/2", probes=[(0, True), (1, False), (-1, False)],
             shape=(0, 1), expected="{0}"),
        dict(name="disconnected", rows=[
            observation("a", "A", y=1, x=0, z=1),
            observation("b", "B", y=0, x=-1, z=1)],
             z=["z"], threshold="3/2", probes=[(-100, True), (0, True), (2, False), (100, True)],
             shape=(2, 0), expected="(-inf,2-sqrt(3)] union [2+sqrt(3),+inf)"),
        dict(name="joint_identity", rows=[
            observation("a", "A", y=1, x=0, z=1, z2=0),
            observation("b", "B", y=1, x=0, z=0, z2=1)],
             z=["z", "z2"], threshold="19/10", probes=[(0, False), (2, False)],
             shape=(0, 0), expected="empty; T=2 for every b"),
        dict(name="joint_shear", rows=[
            observation("a", "A", y=1, x=0, z=1, z2=0),
            observation("b", "B", y=1, x=0, z=1, z2=1)],
             z=["z", "z2"], threshold="19/10", probes=[(0, False), (2, False)],
             shape=(0, 0), expected="empty; invertible shear of joint_identity"),
        dict(name="algebraic_rank_point", rows=[
            observation("a1", "A", y=0, x=-1, z=1, z2=0),
            observation("a2", "A", y=1, x=0, z=0, z2=1),
            observation("b1", "B", y=2, x=0, z=1, z2=0),
            observation("b2", "B", y=0, x=-1, z=0, z2=1)],
             z=["z", "z2"], threshold="1/2", probes=[(-2, False), (-1, False), (0, False), (2, False)],
             shape=(0, 1), expected="{-sqrt(2)}"),
    ]


def inspect(case):
    with Archive() as app:
        app.apply("incident", case["rows"])
        cohort = app.freeze(dict(row_ids=[r["row_id"] for r in case["rows"]],
                                 y="y", x="x", z=case["z"], w=[]))["cohort_id"]
        report = app.execute(app.create_task(cohort, case["threshold"]))
        result = report.confidence_set
        memberships = [(parameter, contains_parameter(result, F(parameter)))
                       for parameter, _ in case["probes"]]
        valid = (len(result.intervals), len(result.points)) == case["shape"]
        valid = valid and memberships == case["probes"]
        if case["name"] == "singleton":
            valid = valid and result.points == [F(0)]
        if case["name"] == "disconnected" and len(result.intervals) == 2:
            from research.inference.endpoints import sign_at_endpoint, compare_endpoints
            left, right = result.intervals
            valid = valid and left.left is None and right.right is None
            valid = valid and not left.left_closed and not right.right_closed
            valid = valid and left.right_closed and right.left_closed
            if left.right is None or right.left is None:
                valid = False
            else:
                valid = valid and sign_at_endpoint((F(1), F(-4), F(1)), left.right) == 0
                valid = valid and sign_at_endpoint((F(1), F(-4), F(1)), right.left) == 0
                valid = valid and compare_endpoints(left.right, F(0)) > 0
                valid = valid and compare_endpoints(left.right, F(1)) < 0
                valid = valid and compare_endpoints(right.left, F(3)) > 0
                valid = valid and compare_endpoints(right.left, F(4)) < 0
        if case["name"] == "algebraic_rank_point" and len(result.points) == 1:
            from research.inference.endpoints import sign_at_endpoint, compare_endpoints
            point = result.points[0]
            valid = valid and sign_at_endpoint((F(-2), F(0), F(1)), point) == 0
            valid = valid and compare_endpoints(point, F(-2)) > 0 and compare_endpoints(point, F(-1)) < 0
        return valid, dict(case=case["name"], expected=case["expected"],
                           actual=encode_confidence_set(result), probes=memberships)


def main():
    failed = []
    for case in cases():
        valid, evidence = inspect(case)
        print(dumps(evidence))
        if not valid:
            failed.append(case["name"])
    if failed:
        print("AR_SET_MISMATCH: " + ",".join(failed))
        return 1
    print("AR_SET_OK: all published incident sets agree")
    return 0


def verify_all():
    import unittest
    suite = unittest.TestLoader().discover("tests", top_level_dir=".")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    incident_status = main()
    return 0 if result.wasSuccessful() and incident_status == 0 else 1


if __name__ == "__main__":
    sys.exit(verify_all() if sys.argv[1:] == ["--verify"] else main())
