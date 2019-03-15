from abc import ABC, abstractmethod
from typing import Generator, Optional, Type, Tuple

from darkgeotile import BaseTile, get_Tile

from pyproj import Proj


class Map(ABC):
    Tile: Type[BaseTile]

    # Attributes for overwriting:
    projection: Proj
    projection_bounds: Optional[Tuple[float, float, float, float]] = None

    def __init__(self, *args, **kwargs):
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def get_urls_gen(tile) -> Generator[str, None, None]:
        raise NotImplementedError

    @staticmethod
    def get_timeout():
        return 0

    @classmethod
    def get_tile_gen(cls, bbox: Tuple[float, float, float, float], zoom: int) -> Generator[Type[BaseTile], None, None]:  # должен быть определен в maps, чтобы для некот карт можно было имитировать пользовательскую активность
        tms_x_s, tms_y_s = zip(*[tile.tms for tile in cls.get_corner_tiles(bbox, zoom)])

        for x in range(min(tms_x_s), max(tms_x_s) + 1):
            for y in range(min(tms_y_s), max(tms_y_s) + 1):
                yield cls.Tile.from_tms(x, y, zoom)

    @classmethod
    def get_corner_tiles(cls, bbox, zoom):  # используется несколько раз, в т. ч. в cls.get_tile_gen, поэтому определен тут
        return tuple(cls.Tile.for_xy(x, y, zoom) for x in bbox[::2] for y in bbox[1::2])

    def __init_subclass__(cls, **kwargs):
        if cls.projection is None:
            raise Exception('unknown coordinate reference system')
        elif not isinstance(cls.projection, Proj):
            cls.projection = Proj(cls.projection)

        cls.Tile = get_Tile(cls.projection, cls.projection_bounds)

        return super().__init_subclass__(**kwargs)


class BingRoad(Map):
    @staticmethod
    def get_urls_gen(tile):
        for i in range(4):
            yield (
                    f'http://ecn.dynamic.t{i}.tiles.virtualearth.net/comp/CompositionHandler/' +
                    f'r{tile.quad_tree}.jpeg?mkt=ru-ru&it=G,VE,BX,L,LA&shading=hill&g=94'
            )

    projection = Proj(init='EPSG:3857')


class BingSatellite(Map):
    @staticmethod
    def get_urls_gen(tile):
        for i in range(4):
            yield f'http://a{i}.ortho.tiles.virtualearth.net/tiles/a{tile.quad_tree}.jpeg?g=94'

    projection = Proj(init='EPSG:3857')


class OpenStreetMap(Map):
    @staticmethod
    def get_urls_gen(tile):
        yield f'https://c.tile.openstreetmap.org/{tile.zoom}/{tile.google[0]}/{tile.google[1]}.png'

    projection = Proj(init='EPSG:3857')


class GoogleHybrid(Map):
    @staticmethod
    def get_urls_gen(tile):
        for i in range(4):
            yield f'http://mt{i}.google.com/vt/lyrs=y&x={tile.google[0]}&y={tile.google[1]}&z={tile.zoom}'

    projection = Proj(init='EPSG:3857')


class GoogleRoad(Map):
    @staticmethod
    def get_urls_gen(tile):
        for i in range(4):
            yield f'http://mt{i}.google.com/vt/lyrs=m&x={tile.google[0]}&y={tile.google[1]}&z={tile.zoom}'

    projection = Proj(init='EPSG:3857')


class GoogleSatellite(Map):
    @staticmethod
    def get_urls_gen(tile):
        for i in range(4):
            yield f'http://mt{i}.google.com/vt/lyrs=s&x={tile.google[0]}&y={tile.google[1]}&z={tile.zoom}'

    projection = Proj(init='EPSG:3857')


class YandexRoad(Map):
    @staticmethod
    def get_urls_gen(tile):
        for i in range(1, 5):
            yield f'http://vec0{i}.maps.yandex.net/tiles?l=map&x={tile.google[0]}&y={tile.google[1]}&z={tile.zoom}'

    projection = Proj(init='EPSG:3395')
    projection_bounds = (-20037508.342789244, -20037508.342789244, 20037508.342789244, 20037508.342789244)


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

    projection = Proj(init='EPSG:4326')


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

    projection = Proj(init='EPSG:4326')


class ArcGISWorldLDarkGrayReference(Map):
    @staticmethod
    def get_urls_gen(tile):
        yield f'https://services.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile' \
            f'/{tile.zoom}/{tile.google[1]}/{tile.google[0]}'

    projection = Proj(init='EPSG:4326')


# other maps templates: http://bcdcspatial.blogspot.com/2012/01/onlineoffline-mapping-map-tiles-and.html
