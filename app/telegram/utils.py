from aiogram import types
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

COMMANDS = [
    types.BotCommand(command="start", description="Start bot"),
    types.BotCommand(command="info", description="Simple info"),
    types.BotCommand(command="add_channel", description="Add bot to channel"),
    types.BotCommand(command="remove_channel", description="Remove bot from channel"),
    types.BotCommand(command="targets", description="List of channel's targets"),
    types.BotCommand(command="target_add", description="Add target to channel"),
    types.BotCommand(command="target_remove", description="Remove target from channel"),
    # types.BotCommand(command="target_update", description="Update channel's target"),
    types.BotCommand(command="stop", description="Stop bot"),
]


class CallbackAbort(CallbackData, prefix="abort"):
    action: str


class CallbackChooseChat(CallbackData, prefix="chat"):
    id: int
    action: str


class CallbackChooseTarget(CallbackData, prefix="target"):
    action: str
    target_id: int
    chat_id: int


class CallbackEmpty(CallbackData, prefix="empty"):
    action: str


def get_keyboard_abort(action: str) -> InlineKeyboardBuilder:
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Abort", callback_data=CallbackAbort(action=action))
    return keyboard


def get_keyboard_chats(chats: list[types.Chat], action: str) -> InlineKeyboardBuilder:
    keyboard = InlineKeyboardBuilder()
    for chat in chats:
        keyboard.button(
            text=chat.title,
            callback_data=CallbackChooseChat(id=str(chat.id), action=action),
        )
    return keyboard


def get_keyboard_targets(
    action: str, targets: list[dict[str, str]], chat_id: int
) -> InlineKeyboardBuilder:
    keyboard = InlineKeyboardBuilder()
    for target in targets:
        keyboard.button(
            text=target["name"],
            callback_data=CallbackChooseTarget(
                action=action,
                target_id=target["id"],
                chat_id=chat_id,
            ),
        )
    return keyboard


def get_keyboard_empty(action: str, name: str) -> InlineKeyboardBuilder:
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text=name, callback_data=CallbackEmpty(action=action))
    return keyboard


class FormTargetAdd(StatesGroup):
    webhook = State()
    name = State()
    key = State()
    prefix = State()


def get_choosed_callback_text(keyboards, callback_data) -> str:
    for keyboard in keyboards:
        for button in keyboard:
            if button.callback_data == callback_data:
                return button.text
