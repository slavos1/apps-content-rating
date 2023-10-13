import re
from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Optional, Set
from urllib.parse import parse_qs, urlparse

from loguru import logger


class Rating(IntEnum):
    _Unknown = 0
    General = -100
    Parental_Guidance = -150
    Rated_for_3 = -200
    Rated_for_7 = -300
    Rated_for_12 = -400
    Restricted_to_15 = -500
    Rated_for_16 = -600
    Mature = -800

    @classmethod
    def str_to_rating(cls, s: str) -> Any:
        if isinstance(s, str):
            label = re.sub(r"\W", "_", re.sub(r"\W+$", "", s))
        else:
            label = ""
        color_dict = {member.name: member for member in cls}
        return color_dict.get(label, Rating._Unknown)

    @property
    def label(self):
        _label = re.sub(r"(Rated|Restricted)_(for|to)_(\d+)", r"\1 \2 \3+", self.name)
        if _label == self.name:
            _label = {
                "_Unknown": "Unknown",
                "Parental_Guidance": "Parental Guidance",
            }.get(self.name, self.name)
        logger.debug("self.name={!r} -> label={!r}", self, _label)
        return _label


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

    def __post_init__(self):
        self.name = self.name.strip()

    @property
    def rating_order(self) -> Rating:
        return Rating.str_to_rating(self.content_rating)

    def __lt__(self, other) -> bool:
        return self.rating_order.value < other.rating_order.value

    def has_valid_rating(self, ignored_ratings: Optional[Set[Rating]] = None) -> bool:
        return not (ignored_ratings and self.rating_order in ignored_ratings)

    @property
    def play_store_id(self):
        try:
            params = parse_qs(urlparse(self.url).query.lower())
            logger.debug("Store id for {}: url={!r} -> params={!r}", self.name, self.url, params)
            _id = params.get("id", params.get("q"))
            if isinstance(_id, (list, tuple)):
                _id = _id[0]
        except Exception:
            _id = None
        logger.debug("Store id for {}: url={!r} -> params={!r}", self.name, self.url, _id)
        return _id

    @property
    def name_order(self):
        return self.name.lower()
