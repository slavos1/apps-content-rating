import pickle
import warnings
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from pathlib import Path

from urllib3.exceptions import InsecureRequestWarning

from . import __version__ as VERSION
from .dataclasses import Rating
from .gather import gather
from .log import setup_logging
from .report import report


def parse_args():
    parser = ArgumentParser("check_ratings", formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument("--version", action="version", version=VERSION)
    parser.add_argument("-q", "--quiet", action="store_true", help="Log less")
    parser.add_argument("-d", "--debug", action="store_true", help="Log more")
    parser.add_argument(
        "-l", "--log-path", metavar="PATH", default="log", help="Log folder", type=Path
    )
    parser.add_argument(
        "-i", "--input", required=True, type=Path, help="Input Markdown from 'List My Apps' app"
    )
    parser.add_argument(
        "-o", "--output", required=True, type=Path, help="Output Asciidoc with app content ratings"
    )

    commands = parser.add_subparsers(dest="command")

    gather = commands.add_parser("gather", help="Get app info")
    gather.add_argument("-n", "--max-urls", type=int, help="Limit to this many urls processed")

    report = commands.add_parser("report", help="Generate report from data gathered by 'gather'")
    report.add_argument(
        "-x", "--ignore", nargs="*", type=Rating.str_to_rating, help="Ignore these ratings"
    )

    return parser.parse_args()


def cli():
    warnings.simplefilter("ignore", InsecureRequestWarning)
    args = parse_args()
    setup_logging(args)
    if args.command == "gather":
        ratings = gather(args.input.open(), args.max_urls)
        pickle.dump(list(ratings), args.output.open("wb"), protocol=pickle.HIGHEST_PROTOCOL)
    elif args.command == "report":
        report(args)
