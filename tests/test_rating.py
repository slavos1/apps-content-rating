import pytest
from loguru import logger

from check_rating.dataclasses import Rating


@pytest.mark.parametrize(
    "s, expected",
    [
        ("Mature", Rating.Mature),
        ("Rated for 3+", Rating.Rated_for_3),
        ("Unknown Rating", Rating._Unknown),
        (None, Rating._Unknown),
        ("", Rating._Unknown),
        (b"some bytes", Rating._Unknown),
        (b"Rated for 3+", Rating._Unknown),
    ],
)
def test_str_to_rating(s, expected):
    logger.debug("fuka!")
    assert Rating.str_to_rating(s) == expected


@pytest.mark.parametrize(
    "rating, expected",
    [
        (Rating.Mature, "Mature"),
        (
            Rating.Rated_for_3,
            "Rated for 3+",
        ),
        (
            Rating._Unknown,
            "Unknown",
        ),
        (
            Rating.Parental_Guidance,
            "Parental Guidance",
        ),
    ],
)
def test_label(rating, expected):
    assert rating.label == expected
