from functools import lru_cache
from collections import defaultdict
from math import inf


def solve(values0, ops0):
    """
    不修改符号，求多边形游戏最高分。
    values0: 原始点权
    ops0: 原始边符号，ops0[i] 连接 values0[i] 和 values0[(i + 1) % n]
    """
    values = values0 * 2
    ops = ops0 * 2
    n = len(values0)
    choice = defaultdict(tuple)
    @lru_cache(None)
    def dfs(l, r):
        if l == r:
            return values[l], values[l]   # max, min
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
                if ops[k] == "+":
                    cur = lv + rv
                else:
                    cur = lv * rv
                if cur > mx:
                    mx = cur
                    choice[(l, r, "max")] = (k, lt, rt)
                if cur < mi:
                    mi = cur
                    choice[(l, r, "min")] = (k, lt, rt)
        return mx, mi

    ans = -inf
    best_l = -1
    for l in range(n):
        r = l + n - 1
        cur = dfs(l, r)[0]
        if cur > ans:
            ans = cur
            best_l = l

    path = []
    merge_edges = []
    def get_path(l, r, op):
        if l == r:
            return values[l], "", f"v{l % n + 1}({values[l]})"
        k, lt, rt = choice[(l, r, op)]
        lv, ls, le = get_path(l, k, lt)
        rv, rs, re = get_path(k + 1, r, rt)
        if ops[k] == "+":
            cur = lv + rv
        else:
            cur = lv * rv
        edge = k % n
        s = f"使用原边 {edge + 1}({ops[k]}) 合并: {le} {ops[k]} {re} = {cur}"
        e = f"({le} {ops[k]} {re})"
        path.append(s)
        merge_edges.append(edge)
        return cur, s, e

    _, _, expr = get_path(best_l, best_l + n - 1, "max")
    delete_edge = (best_l - 1) % n
    return {
        "max_score": ans,
        "delete_edge": delete_edge,
        "expression": expr,
        "path": path,
        "merge_edges": merge_edges,
    }


def main():
    values = [-5, -5, -5, 0]
    ops = ["+", "+", "*", "*"]
    res = solve(values, ops)
    print("最高分:", res["max_score"])
    print("第一步删除原边:", res["delete_edge"] + 1)
    print("表达式:", res["expression"])
    print("路径:")
    for i, s in enumerate(res["path"], 1):
        print(f"第 {i} 步:", s)

if __name__ == "__main__":
    main()