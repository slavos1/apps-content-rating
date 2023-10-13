import pickle
from operator import attrgetter

import jinja2
from loguru import logger

ENCODING = "utf-8"


def report(args):
    logger.debug("ignored_ratings={!r}", args.ignore)
    ratings = sorted(
        app for app in pickle.load(args.input.open("rb")) if app.has_valid_rating(args.ignore)
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
