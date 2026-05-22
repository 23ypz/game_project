import random
from typing import Any, Dict, List, Optional


def make_room_id(existing_room_ids) -> str:
    while True:
        room_id = str(random.randint(1000, 9999))
        if room_id not in existing_room_ids:
            return room_id


def make_player_id(room: Dict[str, Any]) -> str:
    idx = len(room["players"]) + 1
    while True:
        player_id = f"p{idx}"
        if player_id not in [p["id"] for p in room["players"]]:
            return player_id
        idx += 1


def create_room() -> Dict[str, Any]:
    return {
        "host_id": "",
        "players": [],
        "sockets": set(),
        "values": [],
        "ops": [],
        "original_values": [],
        "original_ops": [],
        "edge_ids": [],
        "is_chain": False,
        "deleted_edge": None,
        "started": False,
        "game_over": False,
        "final_value": None,
        "winners": [],
        "current_player_index": 0,
        "scores": {},
        "change_used": {},
        "history": [],
    }


def validate_values_ops(values: List[int], ops: List[str]) -> Optional[str]:
    if len(values) < 3:
        return "多边形至少需要 3 个顶点"
    if len(values) != len(ops):
        return "顶点数必须等于边数"
    if any(op not in ["+", "*"] for op in ops):
        return "运算符只能是 + 或 *"
    return None


def player_name(room: Dict[str, Any], player_id: str) -> str:
    for player in room["players"]:
        if player["id"] == player_id:
            return player["name"]
    return player_id


def current_player_id(room: Dict[str, Any]) -> Optional[str]:
    if not room["players"] or room.get("game_over", False):
        return None
    return room["players"][room["current_player_index"]]["id"]


def advance_turn(room: Dict[str, Any]) -> None:
    if room["players"]:
        room["current_player_index"] = (room["current_player_index"] + 1) % len(room["players"])


def public_state(room_id: str, room: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "type": "state_update",
        "room_id": room_id,
        "host_id": room["host_id"],
        "players": room["players"],
        "values": room["values"],
        "original_values": room.get("original_values", []),
        "original_ops": room.get("original_ops", []),
        "ops": room["ops"],
        "edge_ids": room["edge_ids"],
        "is_chain": room["is_chain"],
        "deleted_edge": room["deleted_edge"],
        "started": room["started"],
        "game_over": room.get("game_over", False),
        "final_value": room.get("final_value"),
        "winners": room.get("winners", []),
        "current_player_id": current_player_id(room),
        "scores": room["scores"],
        "change_used": room.get("change_used", {}),
        "history": room["history"],
    }


def start_game(room: Dict[str, Any], values: List[int], ops: List[str]) -> Optional[str]:
    err = validate_values_ops(values, ops)
    if err:
        return err

    room["values"] = values[:]
    room["ops"] = ops[:]
    room["original_values"] = values[:]
    room["original_ops"] = ops[:]
    room["edge_ids"] = list(range(len(ops)))
    room["is_chain"] = False
    room["deleted_edge"] = None
    room["started"] = True
    room["game_over"] = False
    room["final_value"] = None
    room["winners"] = []
    room["current_player_index"] = 0

    for player in room["players"]:
        pid = player["id"]
        room["scores"][pid] = 0
        room["change_used"][pid] = False

    room["history"].append(f"房主开始游戏：顶点 {values}，边 {ops}")
    return None


def change_edge_symbol(
    room: Dict[str, Any],
    player_id: str,
    edge_index: int,
    new_op: str,
) -> Optional[str]:
    """
    每名玩家只有一次改边符号机会。
    设计为：只能在自己的回合使用，不消耗回合。
    """
    if not room["started"]:
        return "游戏尚未开始"
    if room.get("game_over", False):
        return "游戏已经结束"
    if player_id != current_player_id(room):
        return "还没有轮到你，不能修改边符号"
    if room["change_used"].get(player_id, False):
        return "你已经使用过改边符号机会"
    if new_op not in ["+", "*"]:
        return "新运算符只能是 + 或 *"
    if edge_index < 0 or edge_index >= len(room["ops"]):
        return "边编号不合法"

    old_op = room["ops"][edge_index]
    if old_op == new_op:
        return "新符号不能和原符号相同"

    original_edge = room["edge_ids"][edge_index]
    room["ops"][edge_index] = new_op
    room["change_used"][player_id] = True

    room["history"].append(
        f"{player_name(room, player_id)} 使用一次改符号机会："
        f"将原边 {original_edge + 1} 从 {old_op} 改为 {new_op}"
    )

    return None


def delete_edge(room: Dict[str, Any], player_id: str, edge_index: int) -> Optional[str]:
    if not room["started"]:
        return "游戏尚未开始"
    if room.get("game_over", False):
        return "游戏已经结束"
    if player_id != current_player_id(room):
        return "还没有轮到你"
    if room["is_chain"]:
        return "已经删除过边了，接下来应选择边合并"

    n = len(room["values"])
    if edge_index < 0 or edge_index >= n:
        return "边编号不合法"

    old_values = room["values"][:]
    old_ops = room["ops"][:]
    start = (edge_index + 1) % n

    room["values"] = [old_values[(start + i) % n] for i in range(n)]
    room["ops"] = [old_ops[(start + i) % n] for i in range(n - 1)]
    room["edge_ids"] = [(start + i) % n for i in range(n - 1)]
    room["is_chain"] = True
    room["deleted_edge"] = edge_index

    room["history"].append(
        f"{player_name(room, player_id)} 删除原边 {edge_index + 1}，多边形被剪成链"
    )

    advance_turn(room)
    return None


def finish_if_needed(room: Dict[str, Any]) -> None:
    if room["started"] and len(room["values"]) == 1:
        room["game_over"] = True
        room["final_value"] = room["values"][0]

        if room["scores"]:
            best_score = max(room["scores"].values())
            room["winners"] = [
                pid for pid, score in room["scores"].items()
                if score == best_score
            ]
        else:
            room["winners"] = []

        winner_names = ", ".join(player_name(room, pid) for pid in room["winners"])
        room["history"].append(
            f"游戏结束，最终节点值为 {room['final_value']}，胜者：{winner_names}"
        )


def merge_edge(room: Dict[str, Any], player_id: str, edge_index: int) -> Optional[str]:
    if not room["started"]:
        return "游戏尚未开始"
    if room.get("game_over", False):
        return "游戏已经结束"
    if player_id != current_player_id(room):
        return "还没有轮到你"
    if not room["is_chain"]:
        return "第一步需要先删除一条边"
    if len(room["values"]) <= 1:
        return "没有可合并的边"
    if edge_index < 0 or edge_index >= len(room["ops"]):
        return "边编号不合法"

    a = room["values"][edge_index]
    b = room["values"][edge_index + 1]
    op = room["ops"][edge_index]
    result = a + b if op == "+" else a * b
    original_edge = room["edge_ids"][edge_index]

    room["values"] = room["values"][:edge_index] + [result] + room["values"][edge_index + 2:]
    room["ops"] = room["ops"][:edge_index] + room["ops"][edge_index + 1:]
    room["edge_ids"] = room["edge_ids"][:edge_index] + room["edge_ids"][edge_index + 1:]

    room["scores"][player_id] += result

    room["history"].append(
        f"{player_name(room, player_id)} 使用原边 {original_edge + 1}({op})："
        f"{a} {op} {b} = {result}，得分增加 {result}"
    )

    finish_if_needed(room)
    if not room.get("game_over", False):
        advance_turn(room)

    return None
