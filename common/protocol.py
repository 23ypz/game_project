import json
from typing import Any, Dict


MSG_CONNECT_ROOM = "connect_room"
MSG_WELCOME = "welcome"
MSG_STATE_UPDATE = "state_update"
MSG_ERROR = "error"
MSG_START_GAME = "start_game"
MSG_DELETE_EDGE = "delete_edge"
MSG_MERGE_EDGE = "merge_edge"
MSG_CHANGE_EDGE = "change_edge"


def to_json(data: Dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False)


def from_json(raw: str) -> Dict[str, Any]:
    return json.loads(raw)


def error_msg(message: str) -> Dict[str, str]:
    return {
        "type": MSG_ERROR,
        "message": message,
    }
