import logging
from logging import StreamHandler
from datetime import datetime
from pathlib import Path
import os
from tqdm import tqdm


class WinecellarLogger:
    """
    Logger configured from winecellar YAML config.
    """

    LEVEL_MAP = {
        1: logging.CRITICAL,
        2: logging.ERROR,
        3: logging.WARNING,
        4: logging.INFO,
        5: logging.DEBUG,
    }

    def __init__(self, cfg: dict):
        """
        cfg = parsed winecellar YAML dict
        """
        self.cfg = cfg
        self.cfg = cfg
        self.data = cfg.data 
        self.log_cfg = self.data.get("logging", {})

        self.logger = self._setup_logger()

    def _setup_logger(self):
        level_num = self.log_cfg.get("level", 4)
        log_level = self.LEVEL_MAP.get(level_num, logging.INFO)

        log_dir = Path(
            os.path.expanduser(
                self.log_cfg.get(
                    "log_dir",
                    "~/.local/state/winecellar/logs",
                )
            )
        )
        log_dir.mkdir(parents=True, exist_ok=True)

        log_file = log_dir / self.log_cfg.get("file", "winecellar.log")

        logger = logging.getLogger("winecellar")
        logger.setLevel(log_level)
        logger.propagate = False

        # Avoid duplicate handlers on re-init
        logger.handlers.clear()

        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s"
        )

        # --- File handler ---
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # --- Console handler (optional, tqdm-safe) ---
        if self.log_cfg.get("console", True):
            console_handler = TqdmLoggingHandler()
            console_handler.setLevel(log_level)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

        return logger

    def get_logger(self):
        return self.logger

    def prepare_log_files(self):
        """
        Prepare (and rotate) winecellar log files using winecellar YAML config.
        """


        log_dir = Path(
            os.path.expanduser(
                self.log_cfg.get(
                    "log_dir",
                    "~/.local/state/winecellar/logs",
                )
            )
        )
        log_dir.mkdir(parents=True, exist_ok=True)

        log_file = log_dir / self.log_cfg.get("file", "winecellar.log")

        if log_file.exists():
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            archived = log_dir / f"{log_file.stem}_{ts}{log_file.suffix}"
            log_file.rename(archived)

class TqdmLoggingHandler(StreamHandler):
    def emit(self, record):
        try:
            msg = self.format(record)
            tqdm.write(msg)
        except RecursionError:
            raise
        except Exception:
            self.handleError(record)
