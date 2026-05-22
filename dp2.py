from functools import lru_cache
from collections import defaultdict
from math import inf


def flip(op):
    if op == "+":
        return "*"
    if op == "*":
        return "+"
    raise ValueError("运算符只能是 + 或 *")


def solve_change(values0, ops0):
    values = values0 * 2
    ops = ops0 * 2
    n = len(values0)
    choice = defaultdict(tuple)

    @lru_cache(None)
    def dfs(l, r, use):
        """
        返回区间 [l, r] 在 use 状态下的 max, min。
        use = 0：该区间内没有用过改符号机会
        use = 1：该区间内已经用过一次改符号机会
        """
        if l == r:
            if use == 0:
                return values[l], values[l]
            else:
                # 一个点内部没有边，不能消耗改符号机会
                return -inf, inf
        mx, mi = -inf, inf
        for k in range(l, r):
            for ch in [0, 1]:
                # ch = 0：当前连接边不改
                # ch = 1：当前连接边改符号
                now_op = flip(ops[k]) if ch else ops[k]
                for lu in [0, 1]:
                    for ru in [0, 1]:
                        if lu + ru + ch != use:
                            continue
                        lmx, lmi = dfs(l, k, lu)
                        rmx, rmi = dfs(k + 1, r, ru)
                        candidates = [
                            (lmx, "max", rmx, "max"),
                            (lmx, "max", rmi, "min"),
                            (lmi, "min", rmx, "max"),
                            (lmi, "min", rmi, "min"),
                        ]
                        for lv, lt, rv, rt in candidates:
                            if lv in [-inf, inf] or rv in [-inf, inf]:
                                continue
                            if now_op == "+":
                                cur = lv + rv
                            else:
                                cur = lv * rv
                            if cur > mx:
                                mx = cur
                                choice[(l, r, use, "max")] = (k, lu, lt, ru, rt, ch)
                            if cur < mi:
                                mi = cur
                                choice[(l, r, use, "min")] = (k, lu, lt, ru, rt, ch)
        return mx, mi

    ans = -inf
    best_l = -1

    for l in range(n):
        r = l + n - 1
        cur = dfs(l, r, 1)[0]
        if cur > ans:
            ans = cur
            best_l = l

    path = []
    merge_edges = []
    changed_edge = -1
    old_op = ""
    new_op = ""
    def get_path(l, r, use, op):
        nonlocal changed_edge, old_op, new_op
        if l == r:
            return values[l], "", f"v{l % n + 1}({values[l]})"
        k, lu, lt, ru, rt, ch = choice[(l, r, use, op)]
        lv, ls, le = get_path(l, k, lu, lt)
        rv, rs, re = get_path(k + 1, r, ru, rt)
        real_op = ops[k]
        now_op = flip(real_op) if ch else real_op
        if now_op == "+":
            cur = lv + rv
        else:
            cur = lv * rv
        edge = k % n

        if ch:
            changed_edge = edge
            old_op = real_op
            new_op = now_op
            s = (
                f"先将原边 {edge + 1} 的符号由 {real_op} 改为 {now_op}，"
                f"再合并: {le} {now_op} {re} = {cur}"
            )
        else:
            s = f"使用原边 {edge + 1}({now_op}) 合并: {le} {now_op} {re} = {cur}"

        e = f"({le} {now_op} {re})"

        path.append(s)
        merge_edges.append(edge)

        return cur, s, e

    _, _, expr = get_path(best_l, best_l + n - 1, 1, "max")

    delete_edge = (best_l - 1) % n

    changed_ops = ops0[:]
    changed_ops[changed_edge] = new_op

    return {
        "max_score": ans,
        "delete_edge": delete_edge,
        "changed_edge": changed_edge,
        "old_op": old_op,
        "new_op": new_op,
        "changed_ops": changed_ops,
        "expression": expr,
        "path": path,
        "merge_edges": merge_edges,
    }


def main():
    values = [-5, -5, -5, 0]
    ops = ["+", "+", "*", "*"]
    res = solve_change(values, ops)
    print("修改一次后的最高分:", res["max_score"])
    print("第一步删除原边:", res["delete_edge"] + 1)
    print("修改原边:", res["changed_edge"] + 1)
    print("修改方式:", res["old_op"], "->", res["new_op"])
    print("修改后的边:", res["changed_ops"])
    print("表达式:", res["expression"])
    print("路径:")

    for i, s in enumerate(res["path"], 1):
        print(f"第 {i} 步:", s)


if __name__ == "__main__":
    main()
