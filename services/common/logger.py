import logging
import os
from datetime import datetime

AIMIND_LEVEL_NUM = 25  # giữa INFO (20) và WARNING (30)
logging.addLevelName(AIMIND_LEVEL_NUM, "AIMIND")

class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: "\033[37m",    # xám
        logging.INFO: "\033[36m",     # cyan
        logging.WARNING: "\03[33m",  # vàng
        logging.ERROR: "\033[31m",    # đỏ
        logging.CRITICAL: "\033[41m", # nền đỏ
        AIMIND_LEVEL_NUM: "\033[32m"  # xanh lá
    }
    RESET = "\033[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelno, self.RESET)
        time_str = self.formatTime(record, self.datefmt)
        levelname = f"{record.levelname:<8}"
        header = f"[{time_str}] {levelname} | "
        if getattr(record, "continuation", False):
            return f"{color}{' ' * (len(header) - 2)}| {record.getMessage()}{self.RESET}"
        else:
            return f"{color}{header}{record.getMessage()}{self.RESET}"

'''
@brief Logger module - Provides colored console and file logging with custom levels.
@details
- Supports AIMIND custom log level for special messages.
- Handles log formatting and file output.
@constructor
- @param name (str): Logger name.
- @param log_dir (str): Directory for log files.
- @param log_level (int): Logging level.
@method
- `get_logger() -> logging.Logger`
    - @return (Logger): Configured logger instance.
'''
class Logger:
    def __init__(self, name: str, log_dir: str = "logs", log_level=logging.INFO):
        '''
        @brief Constructor for Logger.
        @param name (str): Logger name.
        @param log_dir (str): Directory for log files.
        @param log_level (int): Logging level.
        '''
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f"{name}_{timestamp}.log")

        self.logger = logging.getLogger(name)
        self.logger.setLevel(log_level)

        if not self.logger.handlers:
            ch = logging.StreamHandler()
            ch.setLevel(log_level)
            ch_formatter = ColorFormatter(datefmt="%H:%M:%S")
            ch.setFormatter(ch_formatter)

            fh = logging.FileHandler(log_file, encoding="utf-8")
            fh.setLevel(log_level)
            fh_formatter = logging.Formatter(
                "[%(asctime)s] %(levelname)-8s | %(message)s",
                "%Y-%m-%d %H:%M:%S"
            )
            fh.setFormatter(fh_formatter)

            self.logger.addHandler(ch)
            self.logger.addHandler(fh)

        # Thêm method aispeak()
        def aispeak(self_logger, message, *args, **kws):
            if not self_logger.isEnabledFor(AIMIND_LEVEL_NUM):
                return
            if not isinstance(message, str):
                message = str(message)
            lines = message.splitlines()
            if lines:
                self_logger._log(AIMIND_LEVEL_NUM, lines[0], args, **kws)
                for line in lines[1:]:
                    extra = kws.get("extra", {}).copy() if "extra" in kws else {}
                    extra["continuation"] = True
                    self_logger._log(AIMIND_LEVEL_NUM, line, args, extra=extra)

        setattr(self.logger, "aispeak", aispeak.__get__(self.logger, logging.Logger))

    def get_logger(self):
        '''
        @brief Returns the configured logger instance.
        @return (Logger): Configured logger.
        '''
        return self.logger

# Hàm tiện ích để lấy logger
def get_logger(name: str, log_dir: str = "logs", log_level=logging.INFO):
    """
    Hàm tiện ích để lấy logger instance
    :param name: Tên logger
    :param log_dir: Thư mục lưu log file
    :param log_level: Mức log
    :return: Logger instance
    """
    logger_instance = Logger(name, log_dir, log_level)
    return logger_instance.get_logger()
