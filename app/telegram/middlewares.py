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
        self.delay = 5
        self.media_group_cache = TTLCache(ttl=10.0, maxsize=1000.0)
        self.lock = asyncio.Lock()

    async def __call__(
        self,
        handler: Callable[[types.Message, Dict[str, Any]], Awaitable[Any]],
        event: types.Message,
        data: Dict[str, Any],
    ) -> Any:
        message_text = event.text
        if not message_text:
            message_text = event.caption or ""
        message_text = message_text.rstrip()

        chat_targets = await get_targets(event.chat.id)
        keys_to_remove = [target["key"] for target in chat_targets if target["key"]]
        message_text_edited = str(message_text)

        message_entities = event.entities or event.caption_entities
        for entity in message_entities:
            if entity.type == "url":
                link = message_text[entity.offset : (entity.offset + entity.length)]
                if not ("http://" in link or "https://" in link):
                    message_text_edited = message_text_edited.replace(
                        link, f"http://{link}"
                    )

        for key in keys_to_remove:
            message_text_edited = message_text_edited.replace(key, "")
        message_text_edited = message_text_edited.lstrip().rstrip()

        # check if message doesn't have 'payload' (no pics and all text is keys)
        if event.text and message_text_edited == "":
            return
        if message_text_edited != message_text:
            with suppress(TelegramBadRequest):
                if event.text:
                    await event.edit_text(text=message_text_edited)
                if event.caption:
                    await event.edit_caption(caption=message_text_edited)

        data["message_text_original"] = message_text
        data["message_text_edited"] = message_text_edited
        if event.media_group_id == None:
            data["messages_group"] = [event]
            return await handler(event, data)

        media_group_id = event.media_group_id
        message_id = event.message_id

        async with self.lock:
            self.media_group_cache.setdefault(media_group_id, list())
            self.media_group_cache[media_group_id].append(event)

        await asyncio.sleep(self.delay)

        message_id = event.message_id
        message_id_first = event.message_id

        message: types.Message
        for message in self.media_group_cache.get(media_group_id, []):
            if message.message_id < message_id_first:
                message_id_first = message.message_id

        if message_id != message_id_first:
            return

        data["messages_group"] = self.media_group_cache.get(media_group_id, [])
        return await handler(event, data)
