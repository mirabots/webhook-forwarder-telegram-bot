import asyncio
from contextlib import suppress
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware, types
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from cachetools import TTLCache
from common.config import cfg
from crud.chats import chat_exists, owner_exists
from crud.targets import get_targets

from .utils import check_connection


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
        self.media_group_cache = TTLCache(ttl=40.0, maxsize=1000.0)
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

        message_entities = event.entities or event.caption_entities or []
        message_entities = sorted(
            [entity for entity in message_entities if entity.type == "url"],
            key=lambda entity: entity.offset,
        )
        # python get messages in utf-8, but telegram calculates offsets in utf-16, so
        # if message contains emojis, offsets will be shifted relative to utf-8
        fixed_message_entities = []
        message_text_utf_16 = message_text.encode("utf-16-le")
        for entity in message_entities:
            prefix_utf_16 = message_text_utf_16[: (entity.offset * 2)].decode(
                "utf-16-le"
            )
            entity.offset = len(prefix_utf_16)
            fixed_message_entities.append(entity)

        connections_storage = {}
        tasks_list = []
        for entity in fixed_message_entities:
            link = message_text[entity.offset : (entity.offset + entity.length)]
            if not link.startswith(("http://", "https://")):
                tasks_list.append(
                    asyncio.create_task(
                        check_connection(
                            link, "https", connections_storage, entity.offset
                        )
                    )
                )
                tasks_list.append(
                    asyncio.create_task(
                        check_connection(
                            link, "http", connections_storage, entity.offset
                        )
                    )
                )
        if tasks_list:
            await asyncio.gather(*tasks_list)

        message_text_edited_fixed_links = ""
        iterator = 0
        for entity in fixed_message_entities:
            message_text_edited_fixed_links += message_text[iterator : entity.offset]
            link = message_text[entity.offset : (entity.offset + entity.length)]
            if not link.startswith(("http://", "https://")):
                if connections_storage.get(("https", entity.offset)):
                    link = f"https://{link}"
                elif connections_storage.get(("http", entity.offset)):
                    link = f"http://{link}"
            if link.startswith(("http://", "https://")):
                link = f"<{link}>"

            message_text_edited_fixed_links += link
            iterator = entity.offset + entity.length
        message_text_edited_fixed_links += message_text[iterator:]

        for key in keys_to_remove:
            message_text_edited = message_text_edited.replace(key, "")
            message_text_edited_fixed_links = message_text_edited_fixed_links.replace(
                key, ""
            )
        message_text_edited = message_text_edited.lstrip().rstrip()
        message_text_edited_fixed_links = (
            message_text_edited_fixed_links.lstrip().rstrip()
        )

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
        data["message_text_edited"] = message_text_edited_fixed_links
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
