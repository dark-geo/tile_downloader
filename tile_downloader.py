from typing import Union, Tuple, Type, Optional
from pathlib import Path
from utils import ImageFormat
import maps

from _tile_downloader import download_in_gtiff as _download_in_gtiff, download_tiles as _download_tiles


def download_in_gtiff(
        path_to_tiff: Union[Path, str],
        bbox: Tuple[float, float, float, float],
        zoom: int,
        map_: Type[maps.Map],
        crs: str = '+init=EPSG:4326',
        tiles_format = ImageFormat.PNG,
        path_to_tiles: Union[str, Path, None] = None,
        proxies: Optional[dict] = None
) -> None:
    # language=rst
    """
    Download tiles data in GeoTiff file to `path_to_tiff`
    from `bbox` area with zoomlevel `zoom` using `map_`
    """
    return _download_in_gtiff(
        path_to_tiff,
        bbox,
        zoom,
        map_,
        crs,
        tiles_format,
        path_to_tiles=None,
        proxies=None
    )


def download_tiles(
        tiles_dir: Union[Path, str],
        map_bbox: Tuple[float, float, float, float],
        zoom: int,
        map_: Type[maps.Map],
        tiles_format=ImageFormat.PNG,
        proxies: Optional[dict] = None
) -> None:
    # language=rst
    """
    Download tiles from `bbox` with `zoom` zoomlevel to `path_to_tiles` from `map_` using `proxies`.
    """
    return _download_tiles(
        tiles_dir,
        map_bbox,
        zoom,
        map_,
        tiles_format,
        proxies
    )
