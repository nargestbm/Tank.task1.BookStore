from fastapi import Request
from fastapi.responses import JSONResponse
from exceptions import BookStoreException
import logging
from datetime import datetime

# راه‌اندازی لاگر
logging.basicConfig(
    filename='error.log',
    level=logging.ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def error_handler(request: Request, call_next):
    try:
        return await call_next(request)
    except BookStoreException as exc:
        # ثبت خطا در لاگ
        logger.error(
            f"BookStore Error: {exc.message}",
            extra={
                "timestamp": datetime.now().isoformat(),
                "path": request.url.path,
                "method": request.method,
                "details": exc.details
            }
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": True,
                "message": exc.message,
                "details": exc.details,
                "path": request.url.path,
                "timestamp": datetime.now().isoformat()
            }
        )
    except Exception as exc:
        # ثبت خطاهای پیش‌بینی نشده
        logger.error(
            f"Unexpected Error: {str(exc)}",
            extra={
                "timestamp": datetime.now().isoformat(),
                "path": request.url.path,
                "method": request.method
            },
            exc_info=True
        )
        
        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "message": "خطای داخلی سرور",
                "path": request.url.path,
                "timestamp": datetime.now().isoformat()
            }
        )