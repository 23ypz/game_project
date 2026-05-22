# 多边形游戏项目

本项目是算法设计课程实践作业，题目为多边形游戏。项目基于 Python 开发，支持单人模式和多人联机模式，并提供动态规划最高分求解、最优方案演示、当前局面提示、修改一次边符号等功能。

## 一、项目功能

### 1. 单人模式

单人模式支持本地游玩，主要功能包括：

- 手动输入游戏数据
- 随机生成游戏数据
- 图形化显示多边形状态
- 点击边进行删边或合并
- 每一步支持撤销和重做
- 显示历史操作步骤
- 计算原始数据的最高分方案
- 计算修改一次边符号后的最高分方案
- 基于当前剩余点和边计算最高分
- 给出当前局面的下一步最优提示
- 自动演示动态规划求出的最优操作过程

### 2. 多人联机模式

多人联机模式支持局域网内多名玩家对战，主要功能包括：

- 创建房间
- 加入房间
- 房主设置游戏数据
- 多名玩家轮流操作
- 服务端同步游戏状态
- 玩家分数统计
- 显示历史操作记录
- 每名玩家有一次修改边符号的机会
- 支持当前局面动态规划分析和下一步提示

多人规则如下：

1. 房主创建房间并设置初始数据。
2. 至少两名玩家加入后，房主可以开始游戏。
3. 当前玩家第一步删除一条边。
4. 后续玩家轮流选择一条边合并。
5. 每名玩家有且仅有一次机会修改当前某条边的符号。
6. 修改符号只能在自己的回合使用，不消耗回合。
7. 每次合并得到的新值计入当前玩家分数。
8. 最后所有边合并完成后，累计分数最高者获胜。

## 二、项目使用技术

本项目主要使用以下技术：

### 1. Python

项目主体使用 Python 编写。Python 代码结构清晰，适合实现动态规划算法、图形界面和网络通信。

### 2. PyQt6

图形界面使用 PyQt6 实现，主要用于：

- 模式选择窗口
- 单人模式界面
- 联机模式界面
- 按钮、输入框、表格等控件
- 多边形状态的图形化显示
- 鼠标点击边进行交互操作
- 最优方案自动演示

其中多边形图形由 `QPainter` 动态绘制，包括顶点、边、边上的运算符和当前状态。

### 3. WebSocket

多人联机模式使用 WebSocket 实现客户端与服务器之间的实时通信。

联机模式采用“服务端权威状态”设计：

- 客户端只负责显示界面和发送操作请求。
- 服务端负责判断操作是否合法。
- 服务端更新游戏状态。
- 服务端将最新状态广播给所有客户端。
- 客户端收到状态后刷新界面。

这样可以避免多个客户端状态不同步的问题。

### 4. JSON

客户端和服务端之间使用 JSON 格式传递消息，例如：

```json
{
  "type": "merge_edge",
  "edge_index": 2
}
```

JSON 格式结构清晰，便于调试和扩展。

### 5. QThread

PyQt 界面线程不能被网络通信阻塞，因此客户端网络通信放在 `QThread` 后台线程中执行。

主线程负责界面显示和用户操作，网络线程负责连接服务器、发送消息和接收服务器广播。

### 6. 区间动态规划

项目核心算法是区间动态规划，用于计算多边形游戏的最高得分。

普通动态规划状态为：

```python
dfs(l, r)
```

表示区间 `[l, r]` 合并后能够得到的最大值和最小值。

由于顶点值可能为负数，并且边运算符包含乘法，所以每个区间不能只保存最大值，还必须同时保存最小值。

对于乘法，需要考虑：

```text
最大值 × 最大值
最大值 × 最小值
最小值 × 最大值
最小值 × 最小值
```

多边形是环形结构，项目通过“复制数组 + 枚举断边位置”的方式，将环形问题转化为链式区间动态规划问题。

普通最高分 DP 的时间复杂度为：

```text
O(n^3)
```

空间复杂度为：

```text
O(n^2)
```

### 7. 修改一次符号的动态规划优化

项目加入了“每名玩家可以修改一次边符号”的扩展规则。

为了避免枚举每条边后重复执行 DP，项目将状态扩展为：

```python
dfs(l, r, used)
```

其中：

```text
used = 0 表示区间内还没有使用过修改符号机会
used = 1 表示区间内已经使用过修改符号机会
```

在状态转移时，修改符号机会可能出现在：

- 左区间
- 右区间
- 当前连接左右区间的边

因此，该算法不需要外层枚举修改哪条边，时间复杂度仍然保持为：

```text
O(n^3)
```

空间复杂度为：

```text
O(n^2)
```

## 三、项目实现思路

### 1. 游戏数据结构

游戏状态主要包括：

```text
values      当前顶点值
ops         当前边运算符
edge_ids    当前边对应的原始边编号
is_chain    当前是否已经由多边形转为链
history     历史操作记录
scores      联机模式下玩家得分
```

其中 `ops[i]` 表示连接 `values[i]` 和 `values[i + 1]` 的边。

在初始多边形中，最后一条边连接最后一个顶点和第一个顶点。

### 2. 删除边

游戏第一步是删除一条边。

删除边后，多边形会被剪成一条链，但不会立即计算两个端点的值。

### 3. 合并边

删除边之后，每一步选择一条边，将这条边和它两端的两个顶点合并成一个新的顶点。

例如：

```text
3 + 5 = 8
```

则两个旧顶点被新顶点 `8` 替代。

### 4. 撤销和重做

单人模式中，撤销和重做使用双栈实现：

```text
undo_stack
redo_stack
```

每次操作前保存当前状态，撤销时恢复上一个状态，重做时恢复被撤销的状态。

### 5. 最优路径回溯

动态规划在更新最大值或最小值时，会使用 `choice` 记录转移来源。

普通 DP 记录形式类似：

```python
choice[(l, r, "max")] = (k, left_type, right_type)
```

修改一次符号的 DP 记录形式类似：

```python
choice[(l, r, used, "max")] = (
    k,
    left_used,
    left_type,
    right_used,
    right_type,
    change_current
)
```

通过 `choice` 可以从最终最优解反向回溯出完整操作过程，包括：

- 删除哪条边
- 修改哪条边的符号
- 每一步合并哪条边
- 每一步的计算结果
- 最终表达式

## 四、项目结构

```text
game_project/
├── run_client.py              # 客户端启动入口
├── run_server.py              # 联机服务端启动入口
├── requirements.txt           # 项目依赖
├── README.md                  # 项目说明文档
├── common/
│   ├── dp_solver.py           # 动态规划算法
│   ├── game_logic.py          # 游戏规则和状态更新逻辑
│   └── protocol.py            # 网络通信消息类型
├── network/
│   └── client_thread.py       # 客户端网络线程
├── server/
│   └── server_app.py          # WebSocket 服务端
└── ui/
    ├── launcher.py            # 模式选择窗口
    ├── single_window.py       # 单人模式窗口
    ├── main_window.py         # 联机模式窗口
    └── polygon_canvas.py      # 多边形绘制控件
```

## 五、运行环境

建议使用 Python 3.10 或以上版本。

安装依赖：

```bash
pip install -r requirements.txt
```

如果没有安装依赖，也可以手动安装：

```bash
pip install PyQt6 websockets
```

## 六、运行项目

### 1. 启动客户端

```bash
python run_client.py
```

启动后会出现模式选择界面，可以选择：

```text
单人模式
联机模式
```

### 2. 启动联机服务端

如果要使用联机模式，需要先启动服务端：

```bash
python run_server.py --host 0.0.0.0 --port 8765
```

### 3. 本机联机测试

先启动服务端，然后打开两个客户端：

```bash
python run_client.py
```

两个客户端都选择联机模式，服务器地址填写：

```text
ws://127.0.0.1:8765
```

第一个客户端房间号留空，点击“连接 / 创建房间”。

第二个客户端输入第一个客户端显示的房间号，再点击连接。

### 4. 局域网联机测试

服务端运行在一台电脑上，其他电脑客户端填写服务端电脑的局域网 IP。

例如服务端电脑 IP 为：

```text
192.168.1.23
```

则客户端服务器地址填写：

```text
ws://192.168.1.23:8765
```

## 七、从 GitHub 拉取项目

项目仓库地址：

```text
https://github.com/23ypz/game_project
```

组员第一次拉取项目时，执行：

```bash
git clone https://github.com/23ypz/game_project.git
cd game_project
```

安装依赖：

```bash
pip install -r requirements.txt
```

运行项目：

```bash
python run_client.py
```

如果需要测试联机模式，先运行：

```bash
python run_server.py --host 0.0.0.0 --port 8765
```

## 八、协同开发流程

### 1. 不要直接修改 main 分支

`main` 分支用于保存稳定版本。

每个成员开发新功能时，应先创建自己的分支。

例如：

```bash
git checkout -b feature/dp
```

常见分支命名：

```text
feature/dp
feature/ui
feature/online
feature/game-logic
feature/test-doc
```

### 2. 每次开发前先同步主分支

```bash
git checkout main
git pull origin main
```

然后切换到自己的分支：

```bash
git checkout feature/dp
```

如果需要把主分支最新代码合并到自己的分支：

```bash
git merge main
```

### 3. 提交自己的修改

查看修改状态：

```bash
git status
```

添加修改文件：

```bash
git add .
```

提交修改：

```bash
git commit -m "说明本次修改内容"
```

例如：

```bash
git commit -m "optimize dp with one change state"
```

### 4. 推送自己的分支

第一次推送新分支：

```bash
git push -u origin feature/dp
```

之后继续推送该分支时，只需要：

```bash
git push
```

### 5. 在 GitHub 上发起 Pull Request

推送分支后，在 GitHub 仓库页面点击：

```text
Compare & pull request
```

填写本次修改内容，例如：

```text
本次修改：
1. 优化修改一次符号的动态规划
2. 添加当前局面下一步提示
3. 更新 DP 结果显示格式

测试：
1. 运行 python run_client.py 正常
2. 单人模式正常
3. 联机模式可以正常连接
```

由组长或负责集成的同学检查后，再合并到 `main` 分支。

### 6. 解决冲突

如果两名成员修改了同一个文件，可能会产生冲突。

冲突文件中会出现类似内容：

```text
<<<<<<< HEAD
当前分支代码
=======
另一个分支代码
>>>>>>> feature/xxx
```

需要手动保留正确代码，删除冲突标记，然后执行：

```bash
git add .
git commit -m "resolve merge conflict"
git push
```

## 九、常用 Git 命令

查看当前状态：

```bash
git status
```

查看当前分支：

```bash
git branch
```

创建并切换分支：

```bash
git checkout -b feature/xxx
```

切换分支：

```bash
git checkout main
```

拉取远程最新代码：

```bash
git pull origin main
```

提交代码：

```bash
git add .
git commit -m "提交说明"
```

推送代码：

```bash
git push
```

第一次推送新分支：

```bash
git push -u origin feature/xxx
```


## 十、注意事项

1. 不要提交虚拟环境文件夹，例如 `venv/`、`.venv/`。
2. 不要提交 `__pycache__/` 缓存文件。
3. 每次开发前先 `git pull`。
4. 修改前确认自己所在分支，不要误改 `main`。
5. 合并代码前至少运行一次项目，确认没有语法错误。
6. 大改动提前在小组群里说明，避免多人同时修改同一个文件。
