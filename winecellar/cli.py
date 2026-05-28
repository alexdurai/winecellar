import argparse
import sys
from pathlib import Path
from importlib.metadata import version, PackageNotFoundError

from .config import WinecellarConfig
from .bottle import Bottle
from .log import WinecellarLogger


MODES = ("create", "overrides","update", "backup", "restore")


def get_version() -> str:
    try:
        return version("winecellar")
    except PackageNotFoundError:
        return "0.0.0"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="winecellar",
        description="Single-user Bottle manager for Linux",
    )

    parser.add_argument(
        "-V", "--version",
        action="version",
        version=f"%(prog)s {get_version()}",
    )

    parser.add_argument(
        "mode",
        choices=MODES,
        help="Operation mode",
    )

    parser.add_argument(
        "-c", "--config",
        type=Path,
        required=True,
        help="Path to winecellar.yml",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done",
    )

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    cfg_path = args.config.expanduser()
    if not cfg_path.exists():
        print(f"ERROR: config file not found: {cfg_path}", file=sys.stderr)
        sys.exit(2)

    cfg = WinecellarConfig(cfg_path)

    logger_mgr = WinecellarLogger(cfg)
    logger_mgr.prepare_log_files()
    log = logger_mgr.logger

    log.info("Starting winecellar (%s)", args.mode)
    log.debug("Using config: %s", cfg_path)

    bottle = Bottle(cfg)

    if args.mode == "create":
        bottle.create(dry_run=args.dry_run)

    if args.mode == "update":
        bottle.update(dry_run=args.dry_run)

    elif args.mode == "backup":
        bottle.backup(dry_run=args.dry_run)

    elif args.mode == "restore":
        if not args.backup_tag:
            log.warning("No backup tag provided, restoring latest backup")

        bottle.restore(
            backup_tag=args.backup_tag,
            dry_run=args.dry_run,
        )
    elif args.mode == "overrides":
        bottle.apply_dll_overrides()

    elif args.mode == "environment":
        bottle.apply_environment()

    log.info("Done")


if __name__ == "__main__":
    main()
