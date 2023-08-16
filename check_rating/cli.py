from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from dataclasses import asdict, dataclass
from functools import partial
from itertools import filterfalse
import json
from operator import attrgetter, itemgetter
from pathlib import Path
import pickle
import re
import sys
from typing import Iterable, Optional, Tuple
import warnings
from loguru import logger
import concurrent.futures
from lxml import etree
from urllib3.exceptions import InsecureRequestWarning
import jinja2

from requests import get
from . import __version__ as VERSION


UA = "Mozilla/5.0"
ENCODING = "utf-8"

suppress_ratingS = ["General", "Rated 3+"]


@dataclass
class AppDeveloper:
    name: str
    url: str


@dataclass
class AppInfo:
    name: str
    url: str
    content_rating: Optional[str] = None
    description: Optional[str] = None
    original_name: Optional[str] = None
    developer: Optional[AppDeveloper] = None
    star_rating: Optional[float] = None

    def __lt__(self, other) -> bool:
        return self.content_rating < other.content_rating


def _get_urls(stream, max_urls: Optional[int] = None) -> Iterable[AppInfo]:
    count = 0
    for line in stream:
        try:
            d = re.search(r"^\*\s+\[(?P<name>.*?)\]\((?P<url>.*?)\)", line).groupdict()
        except:
            continue
        # logger.info("d={}", d)
        yield AppInfo(**d)
        count += 1
        if max_urls and count >= max_urls:
            break


def load_url(info: AppInfo) -> AppInfo:
    logger.debug("Loading {}", info.url)
    response = get(info.url, headers={"User-agent": UA}, verify=False)
    if response.ok:
        html = etree.fromstring(response.text, parser=etree.HTMLParser())
        # Path("x.dump.html").open("w").write(response.text)
        name = html.xpath('.//h1[@itemprop="name"]/span/text()')
        if name:
            # reset the name as comes from the Play Store
            info.original_name = name[0].strip()
        developer = html.xpath('.//a[starts-with(@href,"/store/apps/dev")]')
        if developer:
            info.developer = AppDeveloper(
                developer[0].xpath("span/text()")[0].strip(), developer[0].get("href")
            )
        logger.debug("{} -> found name={}", info.name, name)
        content_rating = html.xpath('.//*[@itemprop="contentRating"]/span/text()')
        if content_rating:
            info.content_rating = content_rating[0].strip()
        desc = html.xpath('.//*[@itemprop="description"]/@content')
        if desc:
            info.description = desc[0].strip()
        star_rating = html.xpath('.//*[@itemprop="starRating"]/div/text()')
        if star_rating:
            info.star_rating = float(star_rating[0].strip())
    return info


def main(stream, max_urls: Optional[int] = None, max_workers: int = 10) -> Iterable[AppInfo]:
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Start the load operations and mark each future with its URL
        futures = list(map(partial(executor.submit, load_url), _get_urls(stream, max_urls)))
        for future in concurrent.futures.as_completed(futures):
            try:
                info: AppInfo = future.result()
            except Exception as exc:
                logger.error("{}: {}", future, exc)
            else:
                logger.info("{} has content rating {!r}", info.name, info.content_rating)
                yield info


def is_safe_rating(args, info: AppInfo) -> bool:
    is_safe = args.ignore and info.content_rating in args.ignore
    logger.debug("name={}, content_rating={} -> is_safe={}", info.name, info.content_rating, is_safe)
    return is_safe


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
    report.add_argument("-x", "--ignore", nargs="*", help="Ignore these ratings")

    return parser.parse_args()


def cli():
    warnings.simplefilter("ignore", InsecureRequestWarning)
    args = parse_args()
    setup_logging(args)
    if args.command == "gather":
        ratings = main(args.input.open(), args.max_urls)
        pickle.dump(list(ratings), args.output.open("wb"), protocol=pickle.HIGHEST_PROTOCOL)
    elif args.command == "report":
        ratings = sorted(
            filterfalse(partial(is_safe_rating, args), pickle.load(args.input.open("rb")))
        )
        logger.info("Have {} apps", len(ratings))
        jinja = jinja2.Environment(loader=jinja2.FileSystemLoader("templates"))
        jinja.filters.update(
            sorted=lambda it, attr: sorted(it, key=attrgetter(attr)),
        )
        args.output.open("wb").write(
            jinja.get_template("ratings.tmpl.adoc")
            .render(apps=ratings, ignore=args.ignore)
            .encode(ENCODING)
        )
