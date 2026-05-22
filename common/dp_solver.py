from dataclasses import dataclass
from functools import lru_cache
from math import inf
from typing import Dict, List, Optional, Tuple


@dataclass
class DPSolution:
    max_score: int
    delete_edge: int
    expression: str
    merge_edge_ids: List[int]
    step_texts: List[str]


@dataclass
class DPChangeSolution:
    max_score: int
    change_edge: int
    old_op: str
    new_op: str
    after_change_ops: List[str]
    base_solution: DPSolution


@dataclass
class ChainSolution:
    max_score: int
    expression: str
    merge_edge_ids: List[int]
    step_texts: List[str]
    first_edge_id: Optional[int]


def flip_op(op: str) -> str:
    if op == "+":
        return "*"
    if op == "*":
        return "+"
    raise ValueError("运算符只能是 + 或 *")


def solve_polygon_dp(raw_values: List[int], raw_ops: List[str]) -> DPSolution:
    """
    不修改符号：求原始多边形最高得分。
    保留递归记忆化 + choice 回溯路径的风格。
    """
    n = len(raw_values)
    if n == 0:
        raise ValueError("顶点数不能为 0")
    if len(raw_ops) != n:
        raise ValueError("边数必须等于顶点数")
    if any(op not in ["+", "*"] for op in raw_ops):
        raise ValueError("运算符只能是 + 或 *")

    if n == 1:
        return DPSolution(
            max_score=raw_values[0],
            delete_edge=0,
            expression=str(raw_values[0]),
            merge_edge_ids=[],
            step_texts=[],
        )

    values = raw_values * 2
    ops = raw_ops * 2
    choice: Dict[Tuple[int, int, str], Tuple[int, str, str]] = {}

    @lru_cache(None)
    def dfs(l: int, r: int) -> Tuple[int, int]:
        if l == r:
            return values[l], values[l]

        mx, mi = -inf, inf

        for k in range(l, r):
            lmx, lmi = dfs(l, k)
            rmx, rmi = dfs(k + 1, r)

            candidates = [
                (lmx, "max", rmx, "max"),
                (lmx, "max", rmi, "min"),
                (lmi, "min", rmx, "max"),
                (lmi, "min", rmi, "min"),
            ]

            for lv, lt, rv, rt in candidates:
                cur = lv + rv if ops[k] == "+" else lv * rv

                if cur > mx:
                    mx = cur
                    choice[(l, r, "max")] = (k, lt, rt)
                if cur < mi:
                    mi = cur
                    choice[(l, r, "min")] = (k, lt, rt)

        return int(mx), int(mi)

    def get_path(l: int, r: int, kind: str):
        if l == r:
            return values[l], [], [], f"v{l % n + 1}({values[l]})"

        k, lt, rt = choice[(l, r, kind)]
        lv, left_edges, left_steps, left_expr = get_path(l, k, lt)
        rv, right_edges, right_steps, right_expr = get_path(k + 1, r, rt)

        cur = lv + rv if ops[k] == "+" else lv * rv
        edge_id = k % n
        step = f"使用原边 {edge_id + 1}({ops[k]}) 合并：{left_expr} {ops[k]} {right_expr} = {cur}"
        expr = f"({left_expr} {ops[k]} {right_expr})"

        return (
            cur,
            left_edges + right_edges + [edge_id],
            left_steps + right_steps + [step],
            expr,
        )

    ans = -inf
    best_l = -1

    for l in range(n):
        r = l + n - 1
        cur = dfs(l, r)[0]
        if cur > ans:
            ans = cur
            best_l = l

    delete_edge = (best_l - 1) % n
    _, merge_edge_ids, step_texts, expression = get_path(best_l, best_l + n - 1, "max")

    return DPSolution(
        max_score=int(ans),
        delete_edge=delete_edge,
        expression=expression,
        merge_edge_ids=merge_edge_ids,
        step_texts=step_texts,
    )


def solve_polygon_dp_with_one_change(raw_values: List[int], raw_ops: List[str]) -> DPChangeSolution:
    """
    允许且必须修改一次边符号：O(n^3) 做法。

    状态：
        dfs(l, r, used)
        used = 0 表示区间 [l, r] 内没有使用改符号机会
        used = 1 表示区间 [l, r] 内已经使用一次改符号机会

    转移：
        枚举断点 mid。
        改符号机会可能在左区间、右区间，或当前连接边 mid 上。
        left_used + right_used + change_current == used。

    复杂度：
        状态数 O(n^2 * 2)，每个状态枚举 O(n) 个断点，used 分配为常数，
        所以总时间复杂度仍为 O(n^3)，空间复杂度 O(n^2)。
    """
    n = len(raw_values)
    if n == 0:
        raise ValueError("顶点数不能为 0")
    if len(raw_ops) != n:
        raise ValueError("顶点数必须等于边数")
    if any(op not in ["+", "*"] for op in raw_ops):
        raise ValueError("运算符只能是 + 或 *")
    if n == 1:
        raise ValueError("只有一个顶点时没有边可修改")

    values = raw_values * 2
    ops = raw_ops * 2

    # choice[(l, r, used, "max" / "min")] =
    # (mid, left_used, left_kind, right_used, right_kind, change_current)
    choice: Dict[Tuple[int, int, int, str], Tuple[int, int, str, int, str, int]] = {}

    @lru_cache(None)
    def dfs(l: int, r: int, used: int) -> Tuple[int, int]:
        if l == r:
            if used == 0:
                return values[l], values[l]
            # 单个顶点内部没有边，不能消耗一次改符号机会
            return -inf, inf

        mx, mi = -inf, inf

        for mid in range(l, r):
            for change_current in (0, 1):
                use_op = flip_op(ops[mid]) if change_current else ops[mid]

                for left_used in (0, 1):
                    for right_used in (0, 1):
                        if left_used + right_used + change_current != used:
                            continue

                        lmx, lmi = dfs(l, mid, left_used)
                        rmx, rmi = dfs(mid + 1, r, right_used)

                        candidates = [
                            (lmx, "max", rmx, "max"),
                            (lmx, "max", rmi, "min"),
                            (lmi, "min", rmx, "max"),
                            (lmi, "min", rmi, "min"),
                        ]

                        for lv, lt, rv, rt in candidates:
                            # 跳过非法状态
                            if lv in (-inf, inf) or rv in (-inf, inf):
                                continue

                            cur = lv + rv if use_op == "+" else lv * rv

                            if cur > mx:
                                mx = cur
                                choice[(l, r, used, "max")] = (
                                    mid,
                                    left_used,
                                    lt,
                                    right_used,
                                    rt,
                                    change_current,
                                )

                            if cur < mi:
                                mi = cur
                                choice[(l, r, used, "min")] = (
                                    mid,
                                    left_used,
                                    lt,
                                    right_used,
                                    rt,
                                    change_current,
                                )

        return int(mx), int(mi)

    ans = -inf
    best_l = -1

    # used=1 表示最终方案必须使用一次改符号机会
    for l in range(n):
        r = l + n - 1
        cur = dfs(l, r, 1)[0]
        if cur > ans:
            ans = cur
            best_l = l

    if best_l == -1:
        raise ValueError("无法找到使用一次改符号后的方案")

    path: List[str] = []
    merge_edge_ids: List[int] = []
    changed_edge: Optional[int] = None
    old_op: Optional[str] = None
    new_op: Optional[str] = None

    def get_path(l: int, r: int, used: int, kind: str):
        nonlocal changed_edge, old_op, new_op

        if l == r:
            return values[l], f"v{l % n + 1}({values[l]})"

        (
            mid,
            left_used,
            left_kind,
            right_used,
            right_kind,
            change_current,
        ) = choice[(l, r, used, kind)]

        lv, left_expr = get_path(l, mid, left_used, left_kind)
        rv, right_expr = get_path(mid + 1, r, right_used, right_kind)

        real_op = ops[mid]
        use_op = flip_op(real_op) if change_current else real_op
        edge_id = mid % n

        if change_current:
            changed_edge = edge_id
            old_op = real_op
            new_op = use_op

        cur = lv + rv if use_op == "+" else lv * rv

        if change_current:
            step = (
                f"先将原边 {edge_id + 1} 的符号由 {real_op} 改为 {use_op}，"
                f"再合并：{left_expr} {use_op} {right_expr} = {cur}"
            )
        else:
            step = f"使用原边 {edge_id + 1}({use_op}) 合并：{left_expr} {use_op} {right_expr} = {cur}"

        path.append(step)
        merge_edge_ids.append(edge_id)

        expr = f"({left_expr} {use_op} {right_expr})"
        return cur, expr

    _, expression = get_path(best_l, best_l + n - 1, 1, "max")
    delete_edge = (best_l - 1) % n

    if changed_edge is None or old_op is None or new_op is None:
        raise ValueError("回溯失败：没有找到被修改的边")

    changed_ops = raw_ops[:]
    changed_ops[changed_edge] = new_op

    base_solution = DPSolution(
        max_score=int(ans),
        delete_edge=delete_edge,
        expression=expression,
        merge_edge_ids=merge_edge_ids,
        step_texts=path,
    )

    return DPChangeSolution(
        max_score=int(ans),
        change_edge=changed_edge,
        old_op=old_op,
        new_op=new_op,
        after_change_ops=changed_ops,
        base_solution=base_solution,
    )


def solve_chain_dp(values: List[int], ops: List[str], edge_ids: Optional[List[int]] = None) -> ChainSolution:
    """
    基于当前已经剩下的链式局面求最高分。
    ops[i] 连接 values[i] 和 values[i + 1]。
    edge_ids[i] 是当前第 i 条边对应的原边编号，0 下标。
    """
    m = len(values)
    if m == 0:
        raise ValueError("当前顶点为空")
    if m == 1:
        return ChainSolution(
            max_score=values[0],
            expression=str(values[0]),
            merge_edge_ids=[],
            step_texts=[],
            first_edge_id=None,
        )
    if len(ops) != m - 1:
        raise ValueError("链式局面下，边数必须等于顶点数 - 1")

    if edge_ids is None:
        edge_ids = list(range(len(ops)))

    choice: Dict[Tuple[int, int, str], Tuple[int, str, str]] = {}

    @lru_cache(None)
    def dfs(l: int, r: int) -> Tuple[int, int]:
        if l == r:
            return values[l], values[l]

        mx, mi = -inf, inf

        for mid in range(l, r):
            lmx, lmi = dfs(l, mid)
            rmx, rmi = dfs(mid + 1, r)

            candidates = [
                (lmx, "max", rmx, "max"),
                (lmx, "max", rmi, "min"),
                (lmi, "min", rmx, "max"),
                (lmi, "min", rmi, "min"),
            ]

            for lv, lt, rv, rt in candidates:
                cur = lv + rv if ops[mid] == "+" else lv * rv

                if cur > mx:
                    mx = cur
                    choice[(l, r, "max")] = (mid, lt, rt)
                if cur < mi:
                    mi = cur
                    choice[(l, r, "min")] = (mid, lt, rt)

        return int(mx), int(mi)

    def get_path(l: int, r: int, kind: str):
        if l == r:
            return values[l], [], [], f"p{l + 1}({values[l]})"

        mid, lt, rt = choice[(l, r, kind)]
        lv, left_edges, left_steps, left_expr = get_path(l, mid, lt)
        rv, right_edges, right_steps, right_expr = get_path(mid + 1, r, rt)

        cur = lv + rv if ops[mid] == "+" else lv * rv
        edge_id = edge_ids[mid]
        step = f"使用当前边 {mid + 1} / 原边 {edge_id + 1}({ops[mid]}) 合并：{left_expr} {ops[mid]} {right_expr} = {cur}"
        expr = f"({left_expr} {ops[mid]} {right_expr})"

        return (
            cur,
            left_edges + right_edges + [edge_id],
            left_steps + right_steps + [step],
            expr,
        )

    best_score = dfs(0, m - 1)[0]
    _, merge_edge_ids, step_texts, expression = get_path(0, m - 1, "max")
    first_edge_id = merge_edge_ids[0] if merge_edge_ids else None

    return ChainSolution(
        max_score=int(best_score),
        expression=expression,
        merge_edge_ids=merge_edge_ids,
        step_texts=step_texts,
        first_edge_id=first_edge_id,
    )


def current_state_best(values: List[int], ops: List[str], edge_ids: List[int], is_chain: bool):
    """
    当前局面最高分和下一步最优提示。
    - 多边形状态：建议下一步删边。
    - 链式状态：建议下一步合并边。
    """
    if not values:
        raise ValueError("当前没有数据")

    if not is_chain:
        sol = solve_polygon_dp(values, ops)
        return {
            "mode": "polygon",
            "score": sol.max_score,
            "action": "delete",
            "edge_id": sol.delete_edge,
            "edge_index": sol.delete_edge,
            "expression": sol.expression,
            "steps": sol.step_texts,
            "solution": sol,
        }

    sol = solve_chain_dp(values, ops, edge_ids)
    if sol.first_edge_id is None:
        edge_index = None
    else:
        edge_index = edge_ids.index(sol.first_edge_id) if sol.first_edge_id in edge_ids else None

    return {
        "mode": "chain",
        "score": sol.max_score,
        "action": "merge",
        "edge_id": sol.first_edge_id,
        "edge_index": edge_index,
        "expression": sol.expression,
        "steps": sol.step_texts,
        "solution": sol,
    }
