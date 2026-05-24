"""
Enhanced Logging Configuration using Loguru.

Features:
- Structured logging with rotation and compression
- Different log levels for development and production
- Separate error log for easier monitoring
- Performance timing helper
- Thread-safe async logging
- Trace ID injection for request tracking
"""
from loguru import logger
import sys
import time
from pathlib import Path
from app.config.settings import settings
from app.core.trace import get_trace_id


class PerformanceTimer:
    """
    Context manager for performance logging.
    
    Usage:
        with PerformanceTimer("Database query"):
            result = await db.execute(query)
        
        # Output:
        # DEBUG - Starting: Database query
        # DEBUG - Completed: Database query (150ms)
    """
    
    def __init__(self, operation: str, log_level: str = "DEBUG"):
        self.operation = operation
        self.log_level = log_level
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        logger.log(self.log_level, f"Starting: {self.operation}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start_time) * 1000
        if exc_type:
            logger.error(
                f"Failed: {self.operation} | "
                f"Duration: {duration_ms:.0f}ms | "
                f"Error: {exc_val}"
            )
        else:
            logger.log(
                self.log_level,
                f"Completed: {self.operation} ({duration_ms:.0f}ms)"
            )


def setup_logger():
    """
    Configure enhanced Loguru logger with appropriate handlers.
    
    Sets up:
    - Console logging (DEBUG for dev, INFO for prod)
    - Daily rotating file log with compression
    - Separate error log for monitoring
    - Thread-safe async logging
    - Trace ID injection in all logs
    """
    # Remove default handler
    logger.remove()
    
    # Ensure logs directory exists
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # ✅ 修复：检测是否在Celery环境中运行
    # Celery Worker在沙箱环境中，enqueue=True会导致PermissionError
    import sys
    is_celery_worker = 'celery' in sys.modules or 'celery_worker' in sys.argv[0] if sys.argv else False
    
    # Trace ID filter - injects Trace ID into all log records
    def trace_id_filter(record):
        """Log filter: automatically inject Trace ID"""
        trace_id = get_trace_id()
        record["extra"]["traceId"] = trace_id if trace_id else "no-trace-id"
        return True
    
    # Console handler
    if settings.DEBUG:
        # Development: colorful, detailed with Trace ID
        logger.add(
            sys.stderr,
            level="DEBUG",
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                "<level>{level: <8}</level> | "
                "<yellow>{extra[traceId]: <32}</yellow> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                "<level>{message}</level>"
            ),
            colorize=True,
        )
    else:
        # Production: plain, concise with Trace ID
        logger.add(
            sys.stderr,
            level="INFO",
            format=(
                "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
                "{level: <8} | "
                "{extra[traceId]: <32} | "
                "{message}"
            ),
        )
    
    # File handler - Daily rotation with compression
    logger.add(
        str(log_dir / "ip_creator_{time:YYYY-MM-DD}.log"),
        rotation="00:00",  # Rotate at midnight
        retention="30 days",
        compression="zip",
        level="DEBUG",
        encoding="utf-8",
        enqueue=False,  # ✅ 修复：禁用enqueue避免沙箱环境PermissionError
        backtrace=True,
        diagnose=settings.DEBUG,
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
            "{level: <8} | "
            "{extra[traceId]: <32} | "
            "{name}:{function}:{line} | "
            "{message}"
        ),
    )
    
    # Separate error log for easier monitoring
    logger.add(
        str(log_dir / "error_{time:YYYY-MM-DD}.log"),
        rotation="00:00",
        retention="90 days",  # Keep errors longer
        compression="zip",
        level="ERROR",
        encoding="utf-8",
        enqueue=False,  # ✅ 修复：禁用enqueue避免沙箱环境PermissionError
        backtrace=True,
        diagnose=settings.DEBUG,
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
            "{level: <8} | "
            "{extra[traceId]: <32} | "
            "{name}:{function}:{line} | "
            "{message}\n{exception}"
        ),
    )
    
    # Apply Trace ID filter
    logger.configure(patcher=lambda record: trace_id_filter(record))
    
    return logger


# Initialize logger
logger = setup_logger()
