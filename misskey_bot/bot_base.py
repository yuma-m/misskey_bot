import logging

from aiohttp import ClientWebSocketResponse
from mipa import Bot
from mipa.router import IChannel
from mipac import Note


class MisskeyBot(Bot):
    def __init__(self, channels: list[IChannel]):
        super().__init__()
        self._channels = channels
        self.logger = self._setup_logger()

    @staticmethod
    def _setup_logger():
        logger = logging.getLogger("MisskeyBot")
        logger.setLevel(logging.DEBUG)
        logger.propagate = False
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s - %(message)s"))
        logger.addHandler(handler)
        return logger

    async def _connect_channel(self) -> None:
        await self.router.connect_channel(self._channels)
        self.logger.debug(f'Connected to {", ".join(self._channels)} channel')

    async def on_ready(self, ws: ClientWebSocketResponse) -> None:
        self.logger.debug(f'Logged in as {self.user.username}')
        await self._connect_channel()

    async def on_reconnect(self, _: ClientWebSocketResponse) -> None:
        await self._connect_channel()

    def _should_ignore(self, note: Note) -> bool:
        return (note.cw is not None
                or (not note.text)
                or note.user.username == self.user.username)

    async def _create_note(self, msg: str, **kwargs) -> None:
        try:
            await self.client.note.action.create(text=msg, **kwargs)
        except Exception as e:
            self.logger.error(e)
