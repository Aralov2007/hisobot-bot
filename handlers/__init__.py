from handlers.auth_handler import router as auth_router
from handlers.user_handler import router as user_router
from handlers.admin_handler import router as admin_router
from handlers.common_handler import router as common_router

__all__ = ["auth_router", "user_router", "admin_router", "common_router"]
