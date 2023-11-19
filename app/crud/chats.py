from db.models import Chats, Targets
from db.utils import async_session
from sqlalchemy import delete, insert, select


async def chat_exists(chat_id: int) -> bool:
    async with async_session() as session:
        async with session.begin():
            db_chat = await session.scalar(select(Chats).where(Chats.id == chat_id))
            if db_chat:
                return True
            return False


async def owner_exists(owner_id: int) -> bool:
    async with async_session() as session:
        async with session.begin():
            db_chat = await session.scalar(
                select(Chats).where(Chats.owner_id == owner_id)
            )
            if db_chat:
                return True
            return False


async def check_ownership(chat_id: int, owner_id: int) -> bool:
    async with async_session() as session:
        async with session.begin():
            db_chat = await session.scalar(
                select(Chats).where(Chats.owner_id == owner_id, Chats.id == chat_id)
            )
            if db_chat:
                return True
            return False


async def add_chat(chat_id: int, owner_id: int) -> bool:
    async with async_session() as session:
        async with session.begin():
            db_chat = await session.scalar(select(Chats).where(Chats.id == chat_id))
            if db_chat:
                return False

            await session.execute(
                insert(Chats).values({"id": chat_id, "owner_id": owner_id})
            )
            return True


async def remove_chats(chat_ids: list[int]) -> None:
    async with async_session() as session:
        async with session.begin():
            await session.execute(delete(Targets).where(Targets.chat_id.in_(chat_ids)))
            await session.execute(delete(Chats).where(Chats.id.in_(chat_ids)))


async def get_owned_chats(owner_id: int) -> list[int]:
    async with async_session() as session:
        async with session.begin():
            db_chats = await session.scalars(
                select(Chats).where(Chats.owner_id == owner_id)
            )

            return [chat.id for chat in db_chats]


async def get_owner(chat_id: int) -> int:
    async with async_session() as session:
        async with session.begin():
            db_chat = await session.scalar(select(Chats).where(Chats.id == chat_id))
            if not db_chat:
                return None
            return db_chat.owner_id
