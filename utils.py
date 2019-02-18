import mimetypes
from enum import Enum
from pathlib import Path
from random import randint
from typing import Union, Tuple, Generator, Optional

from pygeotile.tile import Tile


class ImageFormat(Enum):
    JPEG = JPG = ('image/jpeg', '.jpg')
    PNG = 'image/png'
    GIF = 'image/gif'

    def __init__(self, mimetype: str, default_suffix: Optional[str] = None) -> None:
        self.mimetype = mimetype

        self.possible_suffixes = [suf for suf, type_ in mimetypes.types_map.items() if type_ == mimetype]
        self.default_suffix = default_suffix
        self.set_suffix(self.possible_suffixes[0] if default_suffix is None else default_suffix)

    def set_suffix(self, suffix: str) -> None:
        if suffix not in self.possible_suffixes:
            raise Exception
        self.suffix = suffix


def get_random_tile() -> Tile:
    return Tile.for_latitude_longitude(
        latitude=randint(-90, 90),
        longitude=randint(0, 180),
        zoom=randint(1, 18)
    )


def get_filename(tile: Tile, img_format: ImageFormat, img_dir: Union[str, Path] = '') -> Path:
    # language=rst
    """
    :param tile:
    :param img_format:
    :param img_dir:
    :return: expected filename for tile if img_dir is '', else -- full path
    """
    return Path(img_dir).joinpath(tile.quad_tree).with_suffix(img_format.suffix)


def get_bbox_in_tms(bbox: Tuple[float, float, float, float], zoom: int) -> Tuple[int, int, int, int]:
    # language=rst
    """
    Returns tms coordinates of the tiles bbox
    :param bbox: area of the geo coordinates in the form of:
     `(min_lat, min_lon, max_lat, max_lon)`
    :param zoom:
    :return: bbox of tms tile coordinates in the form: `(min_x, min_y, max_x, max_y)`
    """
    tile1 = Tile.for_latitude_longitude(*bbox[:2], zoom)
    tile2 = Tile.for_latitude_longitude(*bbox[2:], zoom)

    min_x, max_x = sorted([tile1.tms_x, tile2.tms_x])
    min_y, max_y = sorted([tile1.tms_y, tile2.tms_y])

    return min_x, min_y, max_x, max_y


def get_tiles_bbox(tms_bbox: Tuple[int, int, int, int], zoom: int) -> Tuple[float, float, float, float]:
    # language=rst
    """
    Returns bbox of geo coordinates for tiles from tms_bbox area
    :param tms_bbox: area of the tms coordinates in the form of:
     `(min_x, min_y, max_x, max_y)`
    :param zoom:
    :return: bbox of geo coordinates in the form: `(min_lat, min_lon, max_lat, max_lon)`
    """
    points = Tile.from_tms(*tms_bbox[:2], zoom).bounds + Tile.from_tms(*tms_bbox[2:], zoom).bounds
    latitudes, longitudes = zip(*(p.latitude_longitude for p in points))
    return min(latitudes), min(longitudes), max(latitudes), max(longitudes)


def get_tile_gen(bbox: Tuple[float, float, float, float], zoom: int) -> Generator[Tile, None, None]:
    # language=rst
    """
    :param bbox: area of the geo coordinates in the form of:
     `(min_lat, min_lon, max_lat, max_lon)`
    :param zoom:
    :return: generator of tiles, which area intersects with bbox area
    """
    min_x, min_y, max_x, max_y = get_bbox_in_tms(bbox, zoom)

    for x in range(min_x, max_x + 1):
        for y in range(min_y, max_y + 1):
            yield Tile.from_tms(x, y, zoom)
