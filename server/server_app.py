from typing import Any, Dict

import websockets

from common.protocol import (
    MSG_CHANGE_EDGE,
    MSG_CONNECT_ROOM,
    MSG_DELETE_EDGE,
    MSG_MERGE_EDGE,
    MSG_START_GAME,
    MSG_WELCOME,
    error_msg,
    from_json,
    to_json,
)
from common.game_logic import (
    change_edge_symbol,
    create_room,
    make_player_id,
    make_room_id,
    public_state,
    player_name,
    start_game,
    delete_edge,
    merge_edge,
)


rooms: Dict[str, Dict[str, Any]] = {}
client_sessions: Dict[Any, Dict[str, str]] = {}


async def safe_send(ws: Any, data: Dict[str, Any]) -> None:
    try:
        await ws.send(to_json(data))
    except Exception:
        pass


async def broadcast(room_id: str, data: Dict[str, Any]) -> None:
    if room_id not in rooms:
        return

    room = rooms[room_id]
    dead = []

    for ws in list(room["sockets"]):
        try:
            await ws.send(to_json(data))
        except Exception:
            dead.append(ws)

    for ws in dead:
        room["sockets"].discard(ws)


async def handle_connect_room(ws: Any, msg: Dict[str, Any]) -> None:
    name = str(msg.get("player_name") or "玩家").strip()[:20] or "玩家"
    room_id = str(msg.get("room_id") or "").strip()

    if not room_id:
        room_id = make_room_id(rooms.keys())

    if room_id not in rooms:
        rooms[room_id] = create_room()

    room = rooms[room_id]

    if room["started"]:
        await safe_send(ws, error_msg("游戏已经开始，暂不允许中途加入"))
        return

    if len(room["players"]) >= 5:
        await safe_send(ws, error_msg("房间人数已满，最多 5 人"))
        return

    player_id = make_player_id(room)

    if not room["host_id"]:
        room["host_id"] = player_id

    room["players"].append({
        "id": player_id,
        "name": name,
    })
    room["scores"][player_id] = 0
    room["change_used"][player_id] = False
    room["sockets"].add(ws)

    client_sessions[ws] = {
        "room_id": room_id,
        "player_id": player_id,
    }

    await safe_send(ws, {
        "type": MSG_WELCOME,
        "room_id": room_id,
        "player_id": player_id,
        "host_id": room["host_id"],
    })

    room["history"].append(f"{name} 加入房间")
    await broadcast(room_id, public_state(room_id, room))


async def handle_start_game(ws: Any, msg: Dict[str, Any], room_id: str, player_id: str) -> None:
    room = rooms[room_id]

    if player_id != room["host_id"]:
        await safe_send(ws, error_msg("只有房主可以开始游戏"))
        return

    if len(room["players"]) < 2:
        await safe_send(ws, error_msg("至少需要 2 名玩家才能开始联机对战"))
        return

    try:
        values = [int(x) for x in msg.get("values", [])]
        ops = [str(x) for x in msg.get("ops", [])]
    except Exception:
        await safe_send(ws, error_msg("游戏数据格式错误"))
        return

    err = start_game(room, values, ops)
    if err:
        await safe_send(ws, error_msg(err))
        return

    await broadcast(room_id, public_state(room_id, room))


async def handle_change_edge(ws: Any, msg: Dict[str, Any], room_id: str, player_id: str) -> None:
    room = rooms[room_id]

    try:
        edge_index = int(msg.get("edge_index"))
        new_op = str(msg.get("new_op"))
    except Exception:
        await safe_send(ws, error_msg("改边消息格式错误"))
        return

    err = change_edge_symbol(room, player_id, edge_index, new_op)
    if err:
        await safe_send(ws, error_msg(err))

    await broadcast(room_id, public_state(room_id, room))


async def handle_game_action(ws: Any, msg: Dict[str, Any], room_id: str, player_id: str) -> None:
    room = rooms[room_id]

    try:
        edge_index = int(msg.get("edge_index"))
    except Exception:
        await safe_send(ws, error_msg("边编号格式错误"))
        return

    if msg.get("type") == MSG_DELETE_EDGE:
        err = delete_edge(room, player_id, edge_index)
    else:
        err = merge_edge(room, player_id, edge_index)

    if err:
        await safe_send(ws, error_msg(err))

    await broadcast(room_id, public_state(room_id, room))


async def handle_message(ws: Any, msg: Dict[str, Any]) -> None:
    msg_type = msg.get("type")

    if msg_type == MSG_CONNECT_ROOM:
        await handle_connect_room(ws, msg)
        return

    if ws not in client_sessions:
        await safe_send(ws, error_msg("请先连接房间"))
        return

    session = client_sessions[ws]
    room_id = session["room_id"]
    player_id = session["player_id"]

    if room_id not in rooms:
        await safe_send(ws, error_msg("房间不存在"))
        return

    if msg_type == MSG_START_GAME:
        await handle_start_game(ws, msg, room_id, player_id)
        return

    if msg_type == MSG_CHANGE_EDGE:
        await handle_change_edge(ws, msg, room_id, player_id)
        return

    if msg_type in [MSG_DELETE_EDGE, MSG_MERGE_EDGE]:
        await handle_game_action(ws, msg, room_id, player_id)
        return

    await safe_send(ws, error_msg(f"未知消息类型：{msg_type}"))


async def ws_handler(ws: Any, *args: Any) -> None:
    try:
        async for raw in ws:
            try:
                msg = from_json(raw)
            except Exception:
                await safe_send(ws, error_msg("收到的不是合法 JSON"))
                continue

            await handle_message(ws, msg)

    finally:
        session = client_sessions.pop(ws, None)
        if not session:
            return

        room_id = session["room_id"]
        player_id = session["player_id"]

        if room_id not in rooms:
            return

        room = rooms[room_id]
        name = player_name(room, player_id)
        room["sockets"].discard(ws)
        room["players"] = [p for p in room["players"] if p["id"] != player_id]
        room["scores"].pop(player_id, None)
        room["change_used"].pop(player_id, None)
        room["history"].append(f"{name} 离开房间")

        if not room["players"]:
            rooms.pop(room_id, None)
            return

        if room["host_id"] == player_id:
            room["host_id"] = room["players"][0]["id"]

        if room["current_player_index"] >= len(room["players"]):
            room["current_player_index"] = 0

        if room["started"] and not room.get("game_over", False):
            room["game_over"] = True
            room["history"].append("有玩家离开，当前对局结束")

        await broadcast(room_id, public_state(room_id, room))


async def run_server(host: str, port: int) -> None:
    async with websockets.serve(ws_handler, host, port):
        print(f"[server] listening on ws://{host}:{port}")
        await __import__("asyncio").Future()
