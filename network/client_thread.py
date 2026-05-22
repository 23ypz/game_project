import asyncio
from typing import Any, Dict, Optional

import websockets
from PyQt6.QtCore import QThread, pyqtSignal

from common.protocol import MSG_CONNECT_ROOM, from_json, to_json


class NetworkThread(QThread):
    message_received = pyqtSignal(dict)
    status_changed = pyqtSignal(str)

    def __init__(self, url: str, player_name: str, room_id: str):
        super().__init__()
        self.url = url
        self.player_name = player_name
        self.room_id = room_id
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.queue: Optional[asyncio.Queue] = None
        self.ws: Any = None

    def send_json(self, data: Dict[str, Any]) -> None:
        if self.loop is None or self.queue is None:
            self.status_changed.emit("网络尚未连接")
            return

        self.loop.call_soon_threadsafe(self.queue.put_nowait, data)

    def run(self) -> None:
        try:
            asyncio.run(self._main())
        except Exception as e:
            self.status_changed.emit(f"连接结束：{e}")

    async def _main(self) -> None:
        self.loop = asyncio.get_running_loop()
        self.queue = asyncio.Queue()
        self.status_changed.emit(f"正在连接 {self.url} ...")

        async with websockets.connect(self.url) as ws:
            self.ws = ws
            self.status_changed.emit("已连接服务器")

            await self.queue.put({
                "type": MSG_CONNECT_ROOM,
                "player_name": self.player_name,
                "room_id": self.room_id,
            })

            async def sender() -> None:
                while True:
                    data = await self.queue.get()
                    await ws.send(to_json(data))

            async def receiver() -> None:
                async for raw in ws:
                    try:
                        data = from_json(raw)
                    except Exception:
                        continue
                    self.message_received.emit(data)

            await asyncio.gather(sender(), receiver())
