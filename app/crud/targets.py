from db.models import Targets
from db.utils import async_session
from sqlalchemy import delete, insert, select, update


async def check_webhook(webhook: str) -> bool:
    async with async_session() as session:
        async with session.begin():
            db_target = await session.scalar(
                select(Targets).where(Targets.webhook == webhook)
            )
            if db_target:
                return True
            return False


async def add_target(
    webhook: str,
    name: str,
    chat_id: int,
    key: str | None,
    prefix: str,
    always_link_preview: bool,
) -> bool:
    async with async_session() as session:
        async with session.begin():
            db_target = await session.scalar(
                select(Targets).where(
                    Targets.webhook == webhook, Targets.chat_id == chat_id
                )
            )
            if db_target:
                return False

            await session.execute(
                insert(Targets).values(
                    {
                        "webhook": webhook,
                        "name": name,
                        "chat_id": chat_id,
                        "key": key,
                        "prefix": prefix,
                        "always_link_preview": always_link_preview,
                    }
                )
            )
            return True


async def remove_target(id: int, chat_id: int) -> None:
    async with async_session() as session:
        async with session.begin():
            await session.execute(
                delete(Targets).where(Targets.id == id, Targets.chat_id == chat_id)
            )


async def update_target(target_id: int, update_data: dict[str, str]) -> None:
    async with async_session() as session:
        async with session.begin():
            db_target = await session.scalar(
                select(Targets).where(Targets.id == target_id)
            )
            if not db_target:
                return False

            await session.execute(
                update(Targets).where(Targets.id == target_id).values(update_data)
            )
            return True


async def get_targets(chat_id: int) -> dict[str, dict[str, str]]:
    async with async_session() as session:
        async with session.begin():
            db_targets = await session.scalars(
                select(Targets).where(Targets.chat_id == chat_id)
            )

            return [
                {
                    "id": target.id,
                    "webhook": target.webhook,
                    "name": target.name,
                    "key": target.key,
                    "prefix": target.prefix,
                    "always_link_preview": target.always_link_preview,
                }
                for target in db_targets
            ]
