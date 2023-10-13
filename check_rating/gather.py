import concurrent.futures
import re
from functools import partial
from typing import Iterable, Optional

from loguru import logger
from lxml import etree
from requests import get

from .dataclasses import AppDeveloper, AppInfo

UA = "Mozilla/5.0"


def _get_urls(stream, max_urls: Optional[int] = None) -> Iterable[AppInfo]:
    count = 0
    for line in stream:
        try:
            d = re.search(r"^\*\s+\[(?P<name>.*?)\]\((?P<url>.*?)\)", line).groupdict()
        except Exception as exc:
            logger.debug("Exception for line {!r}: {!r}", line, exc)
            continue
        # logger.info("d={}", d)
        yield AppInfo(**d)
        count += 1
        if max_urls and count >= max_urls:
            break


def _load_url(info: AppInfo) -> AppInfo:
    logger.debug("Loading {}", info.url)
    response = get(info.url, headers={"User-agent": UA}, verify=False)
    if response.ok:
        html = etree.fromstring(response.text, parser=etree.HTMLParser())
        # Path("x.dump.html").open("w").write(response.text)
        name = html.xpath('.//h1[@itemprop="name"]/span/text()')
        logger.debug("{!r} -> found name={!r}", info.name, name)
        if name:
            # reset the name as comes from the Play Store
            info.original_name = name[0].strip()
        developer = html.xpath('.//a[starts-with(@href,"/store/apps/dev")]')
        if developer:
            info.developer = AppDeveloper(
                developer[0].xpath("span/text()")[0].strip(), developer[0].get("href")
            )
        content_rating = html.xpath('.//*[@itemprop="contentRating"]/span/text()')
        if content_rating:
            info.content_rating = content_rating[0].strip()
        else:
            logger.warning("Unable to find rating for {!r} ({!r})", info.name, html)
        desc = html.xpath('.//*[@itemprop="description"]/@content')
        if desc:
            info.description = desc[0].strip()
        star_rating = html.xpath('.//*[@itemprop="starRating"]/div/text()')
        if star_rating:
            info.star_rating = float(star_rating[0].strip())
    return info


def gather(stream, max_urls: Optional[int] = None, max_workers: int = 10) -> Iterable[AppInfo]:
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Start the load operations and mark each future with its URL
        futures = list(map(partial(executor.submit, _load_url), _get_urls(stream, max_urls)))
        for future in concurrent.futures.as_completed(futures):
            try:
                info: AppInfo = future.result()
            except Exception as exc:
                logger.error("{}: {}", future, exc)
            else:
                logger.info("{!r} has content rating {!r}", info.name, info.content_rating)
                yield info
