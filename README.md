# 多边形游戏 - 单人 / 多人联机版

本版本更新了动态规划分析功能。

## 新增 DP 功能

单人模式和联机模式都支持：

1. 原始数据最高分方案：不修改符号的 max。
2. 原始数据最高分方案：允许且必须修改一次边符号后的 max。
3. 两种方案都会显示最高得分、建议删除边、最优表达式、完整合并演示过程。
4. 当前局面分析：基于当前剩下的点和边求最高分，并给出下一步最优提示。

## 运行

```bash
pip install -r requirements.txt
python run_client.py
```

联机模式需要先启动服务端：

```bash
python run_server.py --host 0.0.0.0 --port 8765
```

## 文件说明

```text
common/dp_solver.py       普通 DP、改一次符号 DP、当前局面 DP、下一步提示
ui/single_window.py       单人模式
ui/main_window.py         联机模式
common/game_logic.py      联机状态同步，包含原始数据字段
```

## DP 优化说明

`common/dp_solver.py` 中的 `solve_polygon_dp_with_one_change` 已改为三维状态：

```python
dfs(l, r, used)
```

其中 `used=0/1` 表示区间内是否已经使用过一次改符号机会。这样不再枚举每一条边后重复跑 DP，时间复杂度从 `O(n^4)` 降为 `O(n^3)`，空间复杂度为 `O(n^2)`。
