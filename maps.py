from abc import ABC, abstractmethod
from pathlib import Path
from typing import Generator, Optional
from urllib.parse import urlparse

from pygeotile.tile import Tile

from utils import ImageFormat
from utils import get_random_tile


class Map(ABC):
    def __init__(self, *args, **kwargs):
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def get_urls_gen(tile: Tile) -> Generator[str, None, None]:
        raise NotImplementedError

    @staticmethod
    def get_timeout():
        return 0

    tiles_format = None  # should be overridden
    crs = None  # should be overridden

    @classmethod
    def guess_tiles_format(cls) -> Optional[ImageFormat]:
        # language=rst
        """
        Guessing tiles format of :py:class:`Map` subclass by random tile url
        (method called if subclass doesn't override `cls.tiles_format` attribute)
        """
        for random_tile_url in cls.get_urls_gen(get_random_tile()):
            suffix = Path(urlparse(random_tile_url)[2]).suffix
            proper_formats = [img_f for img_f in ImageFormat if suffix in img_f.possible_suffixes]
            if proper_formats:
                return proper_formats[0]

    def __init_subclass__(cls, **kwargs):
        if cls.tiles_format is None:
            expected_tiles_format = cls.guess_tiles_format()
            if expected_tiles_format:
                cls.tiles_format = expected_tiles_format
            else:
                raise Exception("can't guess tiles format")

        if cls.crs is None:
            raise Exception('unknown coordinate reference system')

        return super().__init_subclass__(**kwargs)


class BingRoad(Map):
    @staticmethod
    def get_urls_gen(tile):
        for i in range(4):
            yield (
                    f'http://ecn.dynamic.t{i}.tiles.virtualearth.net/comp/CompositionHandler/' +
                    f'r{tile.quad_tree}.jpeg?mkt=ru-ru&it=G,VE,BX,L,LA&shading=hill&g=94'
            )

    crs = 'EPSG:3857'


class BingSatellite(Map):
    @staticmethod
    def get_urls_gen(tile):
        for i in range(4):
            yield f'http://a{i}.ortho.tiles.virtualearth.net/tiles/a{tile.quad_tree}.jpeg?g=94'

    crs = 'EPSG:3857'


class OpenStreetMap(Map):
    @staticmethod
    def get_urls_gen(tile):
        yield f'https://c.tile.openstreetmap.org/{tile.zoom}/{tile.google[0]}/{tile.google[1]}.png'

    crs = 'EPSG:3857'


class GoogleHybrid(Map):
    @staticmethod
    def get_urls_gen(tile):
        for i in range(4):
            yield f'http://mt{i}.google.com/vt/lyrs=y&x={tile.google[0]}&y={tile.google[1]}&z={tile.zoom}'

    tiles_format = ImageFormat.PNG
    crs = 'EPSG:3857'


class GoogleRoad(Map):
    @staticmethod
    def get_urls_gen(tile):
        for i in range(4):
            yield f'http://mt{i}.google.com/vt/lyrs=m&x={tile.google[0]}&y={tile.google[1]}&z={tile.zoom}'

    tiles_format = ImageFormat.PNG
    crs = 'EPSG:3857'


class GoogleSatellite(Map):
    @staticmethod
    def get_urls_gen(tile):
        for i in range(4):
            yield f'http://mt{i}.google.com/vt/lyrs=s&x={tile.google[0]}&y={tile.google[1]}&z={tile.zoom}'

    tiles_format = ImageFormat.PNG
    crs = 'EPSG:3857'


class ThunderforestLandscape(Map):
    """
    Thunderforest Landscape Map.
    If maps won't download get new apikey from:
    https://www.thunderforest.com/maps/landscape/
    """

    @staticmethod
    def get_urls_gen(tile):
        for i in ['a', 'b', 'c']:
            yield f'https://{i}.tile.thunderforest.com/landscape/{tile.zoom}/{tile.google[0]}/{tile.google[1]}' \
                f'.png?apikey=7c352c8ff1244dd8b732e349e0b0fe8d'

    tiles_format = ImageFormat.PNG
    crs = 'EPSG:4326'


class ThunderforestMobileAtlas(Map):
    """
    Thunderforest Mobile Atlas Map.
    If maps won't download get new apikey from:
    https://www.thunderforest.com/maps/mobile-atlas/
    """

    @staticmethod
    def get_urls_gen(tile):
        for i in ['a', 'b', 'c']:
            yield f'https://{i}.tile.thunderforest.com/mobile-atlas/{tile.zoom}/{tile.google[0]}/{tile.google[1]}' \
                f'.png?apikey=7c352c8ff1244dd8b732e349e0b0fe8d'

    tiles_format = ImageFormat.PNG
    crs = 'EPSG:4326'


class ArcGISWorldLDarkGrayReference(Map):
    """
    Thunderforest Mobile Atlas Map.
    If maps won't download get new apikey from:
    https://www.thunderforest.com/maps/mobile-atlas/
    """

    @staticmethod
    def get_urls_gen(tile):
        yield f'https://services.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile' \
            f'/{tile.zoom}/{tile.google[1]}/{tile.google[0]}'

    tiles_format = ImageFormat.PNG
    crs = 'EPSG:4326'

# TODO: WRONG YA
# Yandex uses another cs standard (https://stackoverflow.com/questions/26742738/yandex-tiles-wrong)
# So yandex tiles usage differs from others
# template:
# f'http://vec0{randint(1, 4)}.maps.yandex.net/tiles?l=map&x={tile.google[0]}&y={tile.google[1]}&z={tile.zoom}'

# other maps templates: http://bcdcspatial.blogspot.com/2012/01/onlineoffline-mapping-map-tiles-and.html
