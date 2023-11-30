from argparse import ArgumentParser

parser = ArgumentParser(description="Webhook Forwarder Telegram Bot")
parser.add_argument(
    "--host",
    "-H",
    action="store",
    dest="host",
    default="127.0.0.1",
    help="Host addr",
)
parser.add_argument(
    "--port",
    "-P",
    action="store",
    dest="port",
    default="8810",
    help="Port",
)
parser.add_argument(
    "--env",
    "-E",
    action="store",
    dest="env",
    default="dev",
    help="Running environment",
)
args = parser.parse_args()
CURRENT_ENV = args.env

from common.config import cfg

cfg.load_creds(CURRENT_ENV)
print("INFO:\t  Config was loaded")
cfg.load_secrets()
print("INFO:\t  Secrets were loaded to config")


from contextlib import asynccontextmanager

import uvicorn
from aiogram import Bot, Dispatcher, types
from common.utils import exception_handlers, verify_telegram_secret
from db.utils import _engine, check_db
from fastapi import BackgroundTasks, Depends, FastAPI
from telegram.middlewares import (
    AuthChannelMiddleware,
    AuthChatMiddleware,
    ForwardChannelMiddleware,
)
from telegram.routes.routers import router
from telegram.utils import COMMANDS

bot = Bot(token=cfg.TELEGRAM_TOKEN)
dp = Dispatcher()


@asynccontextmanager
async def lifespan_function(app: FastAPI):
    print(f"INFO:\t  {args.env} running {args.host}:{args.port}")
    print()

    await check_db()

    webhook_info = await bot.get_webhook_info()
    if webhook_info.url != f"https://{cfg.DOMAIN}/webhooks/telegram":
        await bot.set_webhook(
            url=f"https://{cfg.DOMAIN}/webhooks/telegram",
            secret_token=cfg.TELEGRAM_SECRET,
        )

    dp.include_router(router)
    dp.message.middleware(AuthChatMiddleware())
    dp.channel_post.middleware(AuthChannelMiddleware())
    dp.channel_post.middleware(ForwardChannelMiddleware())
    await bot.set_my_commands(COMMANDS)
    await bot.set_my_description("Webhook Forwarder Telegram Bot")

    if CURRENT_ENV != "dev":
        owner_info = await bot.get_chat(cfg.OWNER_ID)
        if owner_info.username == cfg.OWNER_LOGIN:
            await bot.send_message(
                chat_id=cfg.OWNER_ID, text="ADMIN MESSAGE\nBOT STARTED"
            )

    yield

    await _engine.dispose()
    await bot.session.close()


FastAPP = FastAPI(
    lifespan=lifespan_function,
    title="",
    version="",
    exception_handlers=exception_handlers,
    openapi_url=None,
    docs_url=None,
    redoc_url=None,
)


@FastAPP.post("/webhooks/telegram", dependencies=[Depends(verify_telegram_secret)])
async def webhook_telegram(update: dict, background_tasks: BackgroundTasks):
    print(update)
    telegram_update = types.Update(**update)
    if update.get("channel_post", {}).get("media_group_id"):
        background_tasks.add_task(dp.feed_webhook_update, bot, update)
    else:
        await dp.feed_webhook_update(bot=bot, update=telegram_update)


if __name__ == "__main__":
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["access"][
        "fmt"
    ] = "%(asctime)s - %(client_addr)s - '%(request_line)s' %(status_code)s"

    uvicorn.run(
        "main:FastAPP",
        host=args.host,
        port=int(args.port),
        proxy_headers=True,
        log_config=log_config,
        reload=False,
    )
