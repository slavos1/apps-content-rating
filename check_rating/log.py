import sys

from loguru import logger


def setup_logging(args) -> None:
    if args.quiet:
        level = "WARNING"
    elif args.debug:
        level = "DEBUG"
    else:
        level = "INFO"
    logger.configure(
        handlers=[
            {"sink": sys.stderr, "diagnose": False, "level": level},
            *(
                (
                    {
                        "sink": args.log_path / "debug.log",
                        "mode": "a",
                        "level": 0,
                        "backtrace": False,
                        "diagnose": False,
                        "rotation": "10 MB",
                        "compression": "bz2",
                        "retention": 3,
                        "enqueue": True,
                    },
                )
                if args.log_path
                else ()
            ),
        ]
    )
