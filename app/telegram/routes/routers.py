from aiogram import Router

from .general import router as router_general
from .target_add import router as router_target_add

router = Router()
router.include_routers(router_general, router_target_add)
