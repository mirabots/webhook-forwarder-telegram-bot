from contextlib import suppress

from aiogram import Bot, F, Router, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from crud import targets as crud_targets

from ..utils import (
    CallbackChooseChat,
    CallbackEmpty,
    FormTargetAdd,
    get_choosed_callback_text,
    get_keyboard_abort,
    get_keyboard_empty,
)

router = Router()


@router.callback_query(CallbackChooseChat.filter(F.action == "tgta"))
async def target_add_start_handler(
    callback: types.CallbackQuery, callback_data: CallbackChooseChat, state: FSMContext
):
    chat_name = get_choosed_callback_text(
        callback.message.reply_markup.inline_keyboard, callback.data
    )

    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            text=f"'{chat_name}' choosen", reply_markup=None
        )
        abort_keyboard = get_keyboard_abort(callback_data.action)
        sended_message = await callback.message.answer(
            text="Enter target's webhook:",
            reply_markup=abort_keyboard.as_markup(),
        )

        await state.set_data(
            {
                "chat_id": callback_data.id,
                "outgoing_form_message_id": sended_message.message_id,
            }
        )
        await state.set_state(FormTargetAdd.webhook)


@router.message(FormTargetAdd.webhook)
async def target_add_webhook_form(
    message: types.Message, state: FSMContext, bot: Bot
) -> None:
    state_data = await state.get_data()
    outgoing_form_message_id = state_data["outgoing_form_message_id"]
    with suppress(TelegramBadRequest):
        await bot.edit_message_reply_markup(
            chat_id=message.from_user.id,
            message_id=outgoing_form_message_id,
            reply_markup=None,
        )

    webhook = message.text.rstrip()

    if await crud_targets.check_webhook(webhook):
        await state.clear()
        await message.answer(text="Webhook already exists!")
        return

    abort_keyboard = get_keyboard_abort("tgta")
    sended_message = await message.answer(
        text="Enter target's name:", reply_markup=abort_keyboard.as_markup()
    )

    # await state.update_data(webhook=webhook)
    state_data["webhook"] = webhook
    state_data["outgoing_form_message_id"] = sended_message.message_id
    await state.set_data(state_data)
    await state.set_state(FormTargetAdd.name)


@router.message(FormTargetAdd.name)
async def target_add_name_form(
    message: types.Message, state: FSMContext, bot: Bot
) -> None:
    state_data = await state.get_data()
    outgoing_form_message_id = state_data["outgoing_form_message_id"]
    with suppress(TelegramBadRequest):
        await bot.edit_message_reply_markup(
            chat_id=message.from_user.id,
            message_id=outgoing_form_message_id,
            reply_markup=None,
        )

    name = message.text.rstrip()

    main_keyboard = get_keyboard_empty("tgtak", "None")
    abort_keyboard = get_keyboard_abort("tgta")
    main_keyboard.attach(abort_keyboard)
    sended_message = await message.answer(
        text="Enter target's key (if None all messages will be forwarded):",
        reply_markup=main_keyboard.as_markup(),
    )

    state_data["name"] = name
    state_data["outgoing_form_message_id"] = sended_message.message_id
    await state.set_data(state_data)
    await state.set_state(FormTargetAdd.key)


@router.message(FormTargetAdd.key)
async def target_add_key_form(
    message: types.Message, state: FSMContext, bot: Bot
) -> None:
    state_data = await state.get_data()
    outgoing_form_message_id = state_data["outgoing_form_message_id"]
    with suppress(TelegramBadRequest):
        await bot.edit_message_reply_markup(
            chat_id=message.from_user.id,
            message_id=outgoing_form_message_id,
            reply_markup=None,
        )

    key = message.text.rstrip()

    main_keyboard = get_keyboard_empty("tgtap", "None")
    abort_keyboard = get_keyboard_abort("tgta")
    main_keyboard.attach(abort_keyboard)
    sended_message = await message.answer(
        text="Enter target's prefix:", reply_markup=main_keyboard.as_markup()
    )

    state_data["key"] = key
    state_data["outgoing_form_message_id"] = sended_message.message_id
    await state.set_data(state_data)
    await state.set_state(FormTargetAdd.prefix)


@router.callback_query(CallbackEmpty.filter(F.action == "tgtak"))
async def target_add_key_handler(
    callback: types.CallbackQuery, callback_data: CallbackEmpty, state: FSMContext
):
    state_data = await state.get_data()

    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            text="None target's key was choosen",
            reply_markup=None,
        )

        main_keyboard = get_keyboard_empty("tgtap", "None")
        abort_keyboard = get_keyboard_abort("tgta")
        main_keyboard.attach(abort_keyboard)
        sended_message = await callback.message.answer(
            text="Enter target's prefix:", reply_markup=main_keyboard.as_markup()
        )

        state_data["key"] = None
        state_data["outgoing_form_message_id"] = sended_message.message_id
        await state.set_data(state_data)
        await state.set_state(FormTargetAdd.prefix)


@router.message(FormTargetAdd.prefix)
async def target_add_final_form(
    message: types.Message, state: FSMContext, bot: Bot
) -> None:
    state_data = await state.get_data()
    outgoing_form_message_id = state_data["outgoing_form_message_id"]
    with suppress(TelegramBadRequest):
        await bot.edit_message_reply_markup(
            chat_id=message.from_user.id,
            message_id=outgoing_form_message_id,
            reply_markup=None,
        )

    chat_id = state_data["chat_id"]
    webhook = state_data["webhook"]
    name = state_data["name"]
    key = state_data["key"]
    prefix = message.text.rstrip()
    await state.clear()

    await crud_targets.add_target(webhook, name, chat_id, key, prefix)
    await message.answer(text="Target was added")


@router.callback_query(CallbackEmpty.filter(F.action == "tgtap"))
async def target_add_final_handler(
    callback: types.CallbackQuery, callback_data: CallbackEmpty, state: FSMContext
):
    state_data = await state.get_data()

    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            text="None target's prefix was choosen",
            reply_markup=None,
        )

        chat_id = state_data["chat_id"]
        webhook = state_data["webhook"]
        name = state_data["name"]
        key = state_data["key"]
        prefix = None
        await state.clear()

        await crud_targets.add_target(webhook, name, chat_id, key, prefix)
        await callback.message.answer(text="Target was added")
