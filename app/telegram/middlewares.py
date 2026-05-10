import asyncio
from contextlib import suppress
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware, types
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from cachetools import TTLCache
from common.config import cfg
from crud.chats import chat_exists, owner_exists
from crud.targets import get_targets


class AuthChatMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[types.Message, Dict[str, Any]], Awaitable[Any]],
        event: types.Message,
        data: Dict[str, Any],
    ) -> Any:
        command = event.text.rstrip()
        user_id = event.from_user.id
        user_name = event.from_user.username

        if command == "/start":
            if user_name.lower() not in cfg.TELEGRAM_ALLOWED:
                with suppress(TelegramBadRequest, TelegramForbiddenError):
                    await event.answer("You are not allowed to use this bot")
                return
            else:
                return await handler(event, data)

        if not (await owner_exists(user_id)):
            return

        return await handler(event, data)


class AuthChannelMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[types.Message, Dict[str, Any]], Awaitable[Any]],
        event: types.Message,
        data: Dict[str, Any],
    ) -> Any:
        if not (await chat_exists(event.chat.id)):
            return
        return await handler(event, data)


class ForwardChannelMiddleware(BaseMiddleware):
    def __init__(self):
        super().__init__()
        self.delay = 15
        self.media_group_cache = TTLCache(ttl=60.0, maxsize=1000.0)
        self.lock = asyncio.Lock()

    async def __call__(
        self,
        handler: Callable[[types.Message, Dict[str, Any]], Awaitable[Any]],
        event: types.Message,
        data: Dict[str, Any],
    ) -> Any:
        chat_targets = await get_targets(event.chat.id)
        if not chat_targets:
            return

        if event.media_group_id == None:
            data["messages_group"] = [event]
            return await handler(event, data)
        async with self.lock:
            self.media_group_cache.setdefault(event.media_group_id, list())
            self.media_group_cache[event.media_group_id].append(event)
        await asyncio.sleep(self.delay)

        main_event: types.Message = None
        message: types.Message
        for message in self.media_group_cache.get(event.media_group_id, []):
            if not main_event:
                main_event = message
            message_text = (message.text or message.caption or "").strip()
            if message_text:
                main_event = message
                break
        if event.message_id != main_event.message_id:
            return

        # save ordered choice for smthg
        # media_group_id = event.media_group_id
        # message_id = event.message_id
        # for message in self.media_group_cache.get(media_group_id, []):
        #     if message.message_id < message_id_first:
        #         message_id_first = message.message_id
        # if message_id != message_id_first:
        #     return

        data["messages_group"] = self.media_group_cache.get(event.media_group_id, [])
        return await handler(event, data)
