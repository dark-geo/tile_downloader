import os
import tempfile
import time
from pathlib import Path
from typing import Union, Tuple, Type, Optional

import cv2
import numpy as np
import rasterio as rio
import rasterio.mask
import rasterio.warp
import requests
from pygeotile.tile import Tile
from shapely.geometry import Polygon

import maps
from utils import ImageFormat, get_tile_gen, get_filename, get_bbox_in_tms, get_tiles_bbox, get_bbox_in_meters
import pyproj
from pyproj import Proj


def download_tiles(
        tiles_dir: Union[Path, str],
        bbox: Tuple[float, float, float, float],
        zoom: int,
        map_: Type[maps.Map],
        proxies: Optional[dict] = None
) -> None:
    # language=rst
    """
    Download tiles from `bbox` with `zoom` zoomlevel to `path_to_tiles` from `map_` using `proxies`.
    :param tiles_dir:
    :param bbox: area of the geo coordinates in the form of:
     `(min_lat, min_lon, max_lat, max_lon)`
    :param zoom:
    :param map_:
    :param proxies:
    :return:
    """
    session = requests.session()
    if proxies is not None:
        session.proxies = proxies

    for tile in get_tile_gen(bbox, zoom):
        path = get_filename(tile, map_.tiles_format, tiles_dir)

        if not path.exists():
            for url in map_.get_urls_gen(tile):
                response = session.get(url)
                time.sleep(map_.get_timeout())
                if response.ok:
                    with open(path, 'wb') as file:
                        file.write(response.content)
                    break

    session.close()


def _get_tiles_data(
        tiles_dir: Union[Path, str],
        tms_bbox: Tuple[int, int, int, int],
        zoom: int,
        tiles_format: ImageFormat  # unnecessary
) -> np.ndarray:
    # language=rst
    """
    Merge tiles from `tms_bbox` area from `path_to_tiles` with `zoom` zoomlevel and `tiles_format` image format
    in array
    :param tiles_dir:
    :param tms_bbox: area of the tms coordinates in the form of:
     `(min_x, min_y, max_x, max_y)`
    :param zoom:
    :param tiles_format:
    :return:
    """
    tiles_dir = Path(tiles_dir)
    min_x, min_y, max_x, max_y = tms_bbox

    filenames = [Path(name) for name in list(os.walk(tiles_dir))[0][2]]

    rows = list()
    for y in range(max_y, min_y - 1, -1):
        row = list()
        for x in range(min_x, max_x + 1):
            expected_filename = get_filename(Tile.from_tms(x, y, zoom), tiles_format)
            files_with_same_name = [name for name in filenames if name.stem == expected_filename.stem]
            if expected_filename in files_with_same_name:
                filename = expected_filename
            else:
                for name in files_with_same_name:
                    if ImageFormat.get_by(suffix=name.suffix):
                        filename = name
                        break
                else:
                    raise Exception(f"Can't reach tile {Tile.from_tms(x, y, zoom).quad_tree}")

            row.append(cv2.imread(str(tiles_dir.joinpath(filename))))

        row_img = cv2.hconcat(row)
        rows.append(row_img)

    return cv2.vconcat(rows)


def _merge_tiles_in_gtiff(
        path: Union[Path, str],
        tiles_dir: Union[Path, str],
        tms_bbox: Tuple[int, int, int, int],
        zoom: int,
        map_: Type[maps.Map],
        crs=None
) -> None:
    # language=rst
    """
    Merge tiles from `tms_bbox` area from `path_to_tiles` with `zoom` zoomlevel and `tiles_format` image format
    in GeoTiff file with `path`
    :param path:
    :param tiles_dir:
    :param tms_bbox: area of the tms coordinates in the form of:
     `(min_x, min_y, max_x, max_y)`
    :param zoom:
    :param map_:
    :param crs: coordinate reference system, that will be used for GeoTiff creation.
    If this parameter is None, `map_.crs` will be used instead.
    :return:
    """
    source_projection = map_.projection
    destination_projection = source_projection if crs is None else Proj(crs)

    tiles_data = _get_tiles_data(tiles_dir, tms_bbox, zoom, map_.tiles_format)
    min_lat, min_lon, max_lat, max_lon = get_tiles_bbox(tms_bbox, zoom)

    left, bottom = pyproj.transform(Proj(init='EPSG:4326'), map_.projection, min_lon, min_lat)
    right, top = pyproj.transform(Proj(init='EPSG:4326'), map_.projection, max_lon, max_lat)

    meta = dict(
        driver='GTiff',
        crs=destination_projection.srs,
        count=tiles_data.shape[2],
        dtype=tiles_data.dtype
    )

    meta['transform'], meta['width'], meta['height'] = rio.warp.calculate_default_transform(
        source_projection.srs, destination_projection.srs,
        tiles_data.shape[1], tiles_data.shape[0],
        left, bottom, right, top
    )

    src_transform = rio.transform.from_bounds(left, bottom, right, top, tiles_data.shape[1], tiles_data.shape[0])
    with rio.open(path, 'w', **meta) as dest_img:
        for i in range(meta['count']):
            rio.warp.reproject(
                tiles_data.take(i, 2),
                rio.band(dest_img, i + 1),
                src_transform=src_transform,
                src_crs=source_projection.srs
            )


def download_in_gtiff(
        path_to_tiff: Union[Path, str],
        bbox: Tuple[float, float, float, float],
        zoom: int,
        map_: Type[maps.Map],
        crs: str = '+init=EPSG:4326',
        path_to_tiles: Union[str, Path, None] = None,
        proxies: Optional[dict] = None
) -> None:
    # language=rst
    """
    Download tiles data in GeoTiff file to `path_to_tiff`
    from `bbox` area with zoomlevel `zoom` using `map_`
    :param path_to_tiff:
    :param bbox: area of the geo coordinates in the form of:
     `(min_lat, min_lon, max_lat, max_lon)`
    :param zoom:
    :param map_:
    :param crs:
    :param path_to_tiles:
    :param proxies:
    :return:
    """
    min_lat, min_lon, max_lat, max_lon = bbox
    with tempfile.NamedTemporaryFile(suffix='.tiff') as tmfile:
        with tempfile.TemporaryDirectory() as temp_dir:
            path_to_tiles = temp_dir if path_to_tiles is None else path_to_tiles

            download_tiles(path_to_tiles, bbox, zoom, map_, proxies)
            tms_bbox = get_bbox_in_tms(bbox, zoom)
            _merge_tiles_in_gtiff(tmfile.name, path_to_tiles, tms_bbox, zoom, map_, crs)

        img = rio.open(tmfile.name)
        meta = img.meta.copy()

        cropped_data, meta['transform'] = rio.mask.mask(
            img,
            [Polygon.from_bounds(min_lon, min_lat, max_lon, max_lat), ],
            crop=True
        )

    meta['height'], meta['width'] = cropped_data.shape[-2:]
    with rio.open(path_to_tiff, 'w', **meta) as file:
        for i in range(meta['count']):
            file.write(cropped_data[i], i + 1)
