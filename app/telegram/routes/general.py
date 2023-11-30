import time
from contextlib import suppress

import httpx
from aiogram import Bot, F, Router, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import IS_ADMIN, IS_NOT_MEMBER, ChatMemberUpdatedFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.utils import formatting
from common.config import cfg
from crud import chats as crud_chats
from crud import targets as crud_targets

from ..utils import (
    CallbackAbort,
    CallbackChooseChat,
    CallbackChooseTarget,
    get_choosed_callback_text,
    get_keyboard_abort,
    get_keyboard_chats,
    get_keyboard_targets,
)

router = Router()


@router.message(Command("start"))
async def start_handler(message: types.Message):
    chat_id = message.chat.id
    owner_id = message.from_user.id

    print(
        f"Start: {owner_id=} {message.from_user.username=} {chat_id=} {time.asctime()}"
    )

    chat_added = await crud_chats.add_chat(chat_id, owner_id)
    message_text = (
        "Bot started\nUse /info for some information"
        if chat_added
        else "Bot already started"
    )
    with suppress(TelegramBadRequest):
        await message.answer(text=message_text)


@router.my_chat_member(ChatMemberUpdatedFilter(IS_NOT_MEMBER >> IS_ADMIN))
async def start_channel_handler(event: types.ChatMemberUpdated, bot: Bot):
    if not cfg.BOT_ACTIVE:
        return
    if event.chat.type in ("group", "supergroup", "private"):
        return

    user_id = event.from_user.id
    chat_id = event.chat.id
    user_membership = await bot.get_chat_member(chat_id, user_id)
    if user_membership.status != "creator":
        print(
            f"Start NOT OWNER: {user_id=} {event.from_user.username=} {chat_id=} {event.chat.title=} {time.asctime()}"
        )
        await bot.leave_chat(chat_id)
        message_text = (
            f"Notification\nCan't add channel '{event.chat.title}' - you are not owner"
        )
        with suppress(TelegramBadRequest):
            await bot.send_message(chat_id=user_id, text=message_text)
        return

    if not (await crud_chats.owner_exists(user_id)):
        return

    print(
        f"Start: {user_id=} {event.from_user.username=} {chat_id=} {event.chat.title=} {time.asctime()}"
    )

    chat_added = await crud_chats.add_chat(chat_id, user_id)
    if chat_added:
        message_text = f"Notification\nChannel '{event.chat.title}' added"
        with suppress(TelegramBadRequest):
            await bot.send_message(chat_id=user_id, text=message_text)


@router.message(Command("stop"))
async def stop_handler(message: types.Message, bot: Bot):
    chat_id = message.chat.id
    owner_id = message.from_user.id

    print(f"Stop: {owner_id=} {message.from_user.username=} {time.asctime()}")

    owned_chats = await crud_chats.get_owned_chats(owner_id)
    if not owned_chats:
        message_text = "Bot already stopped"
        await message.answer(text=message_text)
        return

    await crud_chats.remove_chats(owned_chats)

    for chat_id in owned_chats:
        if chat_id != owner_id:
            await bot.leave_chat(chat_id)

    message_text = "Bot stopped, owned channels were leaved, targets removed"
    await message.answer(text=message_text)


@router.my_chat_member(ChatMemberUpdatedFilter(IS_ADMIN >> IS_NOT_MEMBER))
async def stop_channel_handler(event: types.ChatMemberUpdated, bot: Bot):
    if not cfg.BOT_ACTIVE:
        return
    if event.chat.type in ("group", "supergroup", "private"):
        return

    from_id = event.from_user.id
    from_name = event.from_user.username
    chat_id = event.chat.id
    chat_title = event.chat.title
    bot_id = (await bot.get_me()).id

    if from_id == bot_id:
        from_id = await crud_chats.get_owner(chat_id)
        if from_id == None:
            return

    if not (await crud_chats.check_ownership(chat_id, from_id)):
        return

    print(f"Stop: {from_id=} {from_name=} {chat_id=} {chat_title=} {time.asctime()}")

    await crud_chats.remove_chats([chat_id])
    message_text = f"Notification\nBot leaved from channel '{chat_title}'"
    await bot.send_message(chat_id=from_id, text=message_text)


@router.message(Command("info"))
async def info_handler(message: types.Message, bot: Bot):
    bot_name = (await bot.me()).username
    bot_channel_link = (
        f"tg://resolve?domain={bot_name}&startchannel&admin=edit_messages"
    )

    info = formatting.as_marked_section(
        formatting.Bold("Here is simple instruction how to use bot:"),
        formatting.Text(
            "First of all, you need to add bot to the channel with only admin ",
            formatting.Italic("EDIT POSTS"),
            " permission ",
            formatting.TextLink("or use this link", url=bot_channel_link),
            ".",
        ),
        "Secondly, you need to add target to the channel, using /target_add command. That's all.",
        "Other commands can be found in command-menu near text-input.",
        marker="● ",
    )

    with suppress(TelegramBadRequest):
        await message.answer(**info.as_kwargs())


@router.message(Command("add_channel"))
async def add_channel_handler(message: types.Message, bot: Bot):
    bot_name = (await bot.me()).username
    bot_channel_link = (
        f"tg://resolve?domain={bot_name}&startchannel&admin=edit_messages"
    )
    message_text = formatting.TextLink(
        "Use this link to select channel", url=bot_channel_link
    )

    with suppress(TelegramBadRequest):
        await message.answer(**message_text.as_kwargs())


@router.callback_query(CallbackAbort.filter())
async def abort_handler(
    callback: types.CallbackQuery, callback_data: CallbackAbort, state: FSMContext
):
    await state.clear()

    action = callback_data.action
    action_text = ""
    if action == "tgts":
        action_text = "Getting targets"
    if action == "tgta":
        action_text = "Add target"
    if action == "tgtr":
        action_text = "Remove target"
    # if action == "tgtu":
    #     action_text = "Update target"
    if action == "chnla":
        action_text = "Add channel"
    if action == "chnlr":
        action_text = "Remove channel"

    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            text=f"{action_text} operation was aborted".lstrip().capitalize(),
            reply_markup=None,
        )


@router.message(Command("targets"))
@router.message(Command("target_add"))
@router.message(Command("target_remove"))
# @router.message(Command("target_update"))
@router.message(Command("remove_channel"))
async def chats_handler(message: types.Message, bot: Bot):
    command_text = message.text.rstrip()

    action = "tgts"
    if "/target_add" in command_text:
        action = "tgta"
    if "/target_remove" in command_text:
        action = "tgtr"
    # if "/target_update" in command_text:
    #     action = "tgtu"
    if "/remove_channel" in command_text:
        action = "chnlr"

    chats_ids = await crud_chats.get_owned_chats(message.from_user.id)
    chats = [
        await bot.get_chat(chat_id)
        for chat_id in chats_ids
        if chat_id != message.from_user.id
    ]
    if not chats:
        with suppress(TelegramBadRequest):
            await message.answer(text="No channels")
        return

    main_keyboard = get_keyboard_chats(chats, action)
    main_keyboard.adjust(3)
    abort_keyboard = get_keyboard_abort(action)
    main_keyboard.attach(abort_keyboard)
    with suppress(TelegramBadRequest):
        await message.answer(
            text="Choose channel:", reply_markup=main_keyboard.as_markup()
        )


@router.callback_query(CallbackChooseChat.filter(F.action == "tgts"))
async def targets_handler(
    callback: types.CallbackQuery, callback_data: CallbackChooseChat
):
    chat_name = get_choosed_callback_text(
        callback.message.reply_markup.inline_keyboard, callback.data
    )

    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            text=f"'{chat_name}' choosen", reply_markup=None
        )
        targets = await crud_targets.get_targets(callback_data.id)
        if not targets:
            message_text = "No targets"
        else:
            message_text = "Targets:"
            for target in targets:
                name = target["name"]
                webhook = target["webhook"]
                key = target["key"]
                prefix = target["prefix"]
                message_text += (
                    f"\n● {name}\n○ {webhook}\n○ key: {key}\n○ prefix: {prefix}"
                )
        await callback.message.answer(
            text=message_text, reply_markup=None, disable_web_page_preview=True
        )


@router.callback_query(CallbackChooseChat.filter(F.action == "tgtr"))
async def target_remove_start_handler(
    callback: types.CallbackQuery, callback_data: CallbackChooseChat
):
    chat_name = get_choosed_callback_text(
        callback.message.reply_markup.inline_keyboard, callback.data
    )
    chat_id = callback_data.id

    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            text=f"'{chat_name}' choosen", reply_markup=None
        )
        targets = await crud_targets.get_targets(callback_data.id)
        if not targets:
            await callback.message.answer(text="No targets", reply_markup=None)
        else:
            main_keyboard = get_keyboard_targets("tgtr", targets, chat_id)
            main_keyboard.adjust(3)
            abort_keyboard = get_keyboard_abort(callback_data.action)
            main_keyboard.attach(abort_keyboard)

            await callback.message.answer(
                text="Choose target to remove:",
                reply_markup=main_keyboard.as_markup(),
            )


@router.callback_query(CallbackChooseTarget.filter(F.action == "tgtr"))
async def unsubscribe_streamer_handler(
    callback: types.CallbackQuery, callback_data: CallbackChooseTarget
):
    target_name = get_choosed_callback_text(
        callback.message.reply_markup.inline_keyboard, callback.data
    )

    await crud_targets.remove_target(callback_data.target_id, callback_data.chat_id)

    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            text=f"Removed target '{target_name}'", reply_markup=None
        )


@router.callback_query(CallbackChooseChat.filter(F.action == "chnlr"))
async def remove_channel_handler(
    callback: types.CallbackQuery, callback_data: CallbackChooseChat, bot: Bot
):
    chat_name = get_choosed_callback_text(
        callback.message.reply_markup.inline_keyboard, callback.data
    )
    await bot.leave_chat(callback_data.id)

    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            text=f"'{chat_name}' channel removed", reply_markup=None
        )


@router.channel_post()
async def channel_post_handler(
    channel_post: types.Message,
    bot: Bot,
    message_text_original: str,
    message_text_edited: str,
    messages_group,
):
    owner_id = await crud_chats.get_owner(channel_post.chat.id)
    pictures = {}
    counter = 1
    post: types.Message
    for post in messages_group:
        if post.photo:
            orig_photo = types.PhotoSize(
                file_id="0", file_unique_id="0", width=0, height=0, file_size=0
            )
            for photo in post.photo:
                if photo.file_size > orig_photo.file_size:
                    orig_photo = photo

            orig_photo_bytes = await bot.download(orig_photo)
            pictures[f"file{counter}"] = (
                f"file{counter}.jpg",
                orig_photo_bytes,
                "image/jpeg",
            )
            counter += 1

    if not message_text_original and not pictures:
        return

    async with httpx.AsyncClient() as ac:
        chat_targets = await crud_targets.get_targets(channel_post.chat.id)
        for target in chat_targets:
            webhook = target["webhook"]
            key = target["key"]
            prefix = target["prefix"]

            message_text_to_send = str(message_text_edited)
            if prefix:
                message_text_to_send = f"{prefix} {message_text_to_send}"
            json = {"content": message_text_to_send}

            if not key or key in message_text_original:
                try:
                    if pictures:
                        answer = await ac.post(webhook, files=pictures, data=json)
                    else:
                        answer = await ac.post(webhook, json=json)
                    if answer.status_code < 200 or answer.status_code > 299:
                        if owner_id:
                            await bot.send_message(
                                chat_id=owner_id,
                                text=f"Channel message wasn't forwarded - {answer.status_code}",
                            )
                except Exception:
                    if owner_id:
                        await bot.send_message(
                            chat_id=owner_id, text="Channel message wasn't forwarded"
                        )
