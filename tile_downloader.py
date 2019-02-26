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


def download_tiles(
        tiles_dir: Union[Path, str],
        bbox: Tuple[float, float, float, float],
        zoom: int,
        map_: Type[maps.Map],
        proxies: Optional[dict] = None
) -> None:
    # language=rst
    """
    Download tiles from `bbox` with `zoom` zoomlevel to `tiles_dir` from `map_` using `proxies`.
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
    Merge tiles from `tms_bbox` area from `tiles_dir` with `zoom` zoomlevel and `tiles_format` image format
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
    Merge tiles from `tms_bbox` area from `tiles_dir` with `zoom` zoomlevel and `tiles_format` image format
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
    tiles_data = _get_tiles_data(tiles_dir, tms_bbox, zoom, map_.tiles_format)
    left, bottom, right, top = get_bbox_in_meters(get_tiles_bbox(tms_bbox, zoom))

    meta = dict(
        driver='GTiff',
        crs=map_.crs if crs is None else crs,
        height=tiles_data.shape[0],
        width=tiles_data.shape[1],
        count=tiles_data.shape[2],
        dtype=tiles_data.dtype
    )

    meta['transform'], meta['width'], meta['height'] = rio.warp.calculate_default_transform(
        map_.crs, meta['crs'], tiles_data.shape[1], tiles_data.shape[0], left, bottom, right, top
    )

    src_transform = rio.transform.from_bounds(left, bottom, right, top, tiles_data.shape[1], tiles_data.shape[0])
    with rio.open(path, 'w', **meta) as dest_img:
        for i in range(meta['count']):
            rio.warp.reproject(
                tiles_data.take(i, 2),
                rio.band(dest_img, i + 1),
                src_transform=src_transform,
                src_crs=map_.crs
            )


def download_in_gtiff(
        path: Union[Path, str],
        bbox: Tuple[float, float, float, float],
        zoom: int,
        map_: Type[maps.Map],
        crs: str = 'EPSG:4326',
        tiles_dir: Union[str, Path, None] = None,
        proxies: Optional[dict] = None
) -> None:
    # language=rst
    """
    Download tiles data in GeoTiff file to `path`
    from `bbox` area with zoomlevel `zoom` using `map_`
    :param path:
    :param bbox: area of the geo coordinates in the form of:
     `(min_lat, min_lon, max_lat, max_lon)`
    :param zoom:
    :param map_:
    :param crs:
    :param tiles_dir:
    :param proxies:
    :return:
    """
    min_lat, min_lon, max_lat, max_lon = bbox
    with tempfile.NamedTemporaryFile(suffix='.tiff') as tmfile:
        with tempfile.TemporaryDirectory() as temp_dir:
            tiles_dir = temp_dir if tiles_dir is None else tiles_dir

            download_tiles(tiles_dir, bbox, zoom, map_, proxies)
            tms_bbox = get_bbox_in_tms(bbox, zoom)
            _merge_tiles_in_gtiff(tmfile.name, tiles_dir, tms_bbox, zoom, map_, crs)

        img = rio.open(tmfile.name)
        meta = img.meta.copy()

        cropped_data, meta['transform'] = rio.mask.mask(
            img,
            [Polygon.from_bounds(min_lon, min_lat, max_lon, max_lat), ],
            crop=True
        )

    meta['height'], meta['width'] = cropped_data.shape[-2:]
    with rio.open(path, 'w', **meta) as file:
        for i in range(meta['count']):
            file.write(cropped_data[i], i + 1)
