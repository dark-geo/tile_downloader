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
from darkgeotile import BaseTile
from pyproj import transform, Proj
from shapely.geometry import Polygon

import maps
from utils import ImageFormat, get_expected_path


def download_tiles(
        map_: Type[maps.Map],
        bbox: Tuple[float, float, float, float],
        zoom: int,
        tiles_dir: Path,
        img_format: ImageFormat,
        session: requests.Session,
        *,
        overwriting=False,
) -> None:
    # language=rst
    """
    Download tiles from `bbox` with `zoom` zoom-level to `tiles_dir` from `map_`.
    :param map_: maps.Map subclass, which tiles will be downloaded
    :param bbox: bbox of area coordinates in `map_.projection` reference system in from
    `(min_x, min_y, max_x, max_y)`
    :param zoom: zoom-level for tiles
    :param tiles_dir: path to directory for downloading
    :param img_format: tiles images format
    :param session: object providing requests session
    :param overwriting: if `True`, will overwrite files with expected tiles names.
    if `False`, will skip existent files with expected tiles names.
    :return:
    """
    for tile in map_.get_tile_gen(bbox, zoom):
        path = get_expected_path(tile, tiles_dir, img_format)

        if not overwriting and path.exists():
            continue

        for url in map_.get_urls_gen(tile):
            response = session.get(url)
            if response.ok:
                with path.open('wb') as file:
                    file.write(response.content)

                time.sleep(map_.get_timeout())
                break

    session.close()


def get_tiles_data(
        map_: Type[maps.Map],
        corner_tiles: Tuple[BaseTile, BaseTile, BaseTile, BaseTile],
        tiles_dir: Path,
        img_format: ImageFormat
) -> np.ndarray:
    # language=rst
    """
    Merge tiles from area between `corner_tiles` from `tiles_dir` with `zoom` zoom-level and `tiles_format` image format
    in array
    :param map_: maps.Map subclass, which tiles will be downloaded
    :param corner_tiles: Four corner tiles for rectangle tiles area
    :param tiles_dir: path to directory that contains necessary tiles
    :param img_format: tiles images format
    :return: merged image data
    """
    zoom = corner_tiles[0].zoom

    _google_x_s, _google_y_s = zip(*(tile.google for tile in corner_tiles))
    min_x, min_y, max_x, max_y = min(_google_x_s), min(_google_y_s), max(_google_x_s), max(_google_y_s)

    rows = list()
    for google_y in range(min_y, max_y + 1):
        row = list()
        for google_x in range(min_x, max_x + 1):
            tile = map_.Tile.from_google(google_x, google_y, zoom)
            path = get_expected_path(tile, tiles_dir, img_format)

            if not path.exists():
                raise Exception(f"Can't reach tile {tile.quad_tree}")

            row.append(cv2.imread(str(path)))

        row_img = cv2.hconcat(row)
        rows.append(row_img)

    return cv2.vconcat(rows)


def merge_in_gtiff(
        map_: Type[maps.Map],
        corner_tiles: Tuple[BaseTile, BaseTile, BaseTile, BaseTile],
        path: Path,
        tiles_dir: Path,
        img_format: ImageFormat,
        projection: Optional[Proj] = None
) -> None:
    # language=rst
    """
    Merge tiles from area between `corner_tiles` from `tiles_dir` with `zoom` zoom-level in GeoTIFF file with `path`
    :param map_: maps.Map subclass, which tiles will be downloaded
    :param corner_tiles: Four corner tiles for rectangle tiles area
    :param path: path for output GeoTIFF
    :param tiles_dir: path to directory that contains necessary tiles
    :param img_format: tiles images format
    :param projection: projection for output GeoTIFF
    :return:
    """
    source_projection = map_.projection
    destination_projection = source_projection if projection is None else projection

    data = get_tiles_data(map_, corner_tiles, tiles_dir, img_format)

    _corner_tiles_bounds = sum((tile.bounds for tile in corner_tiles), tuple())
    _x_s, _y_s = zip(*_corner_tiles_bounds)
    left, right, bottom, top = min(_x_s), max(_x_s), min(_y_s), max(_y_s)

    meta = dict(
        driver='GTiff',
        crs=destination_projection.srs,
        count=data.shape[2],
        dtype=data.dtype
    )

    meta['transform'], meta['width'], meta['height'] = rio.warp.calculate_default_transform(
        source_projection.srs, destination_projection.srs,
        data.shape[1], data.shape[0],
        left, bottom, right, top
    )

    src_transform = rio.transform.from_bounds(left, bottom, right, top, data.shape[1], data.shape[0])
    with rio.open(path, 'w', **meta) as destination_img:
        for i in range(meta['count']):
            rio.warp.reproject(
                data.take(i, 2),
                rio.band(destination_img, i + 1),
                src_transform=src_transform,
                src_crs=source_projection.srs
            )


def construct_gtiff(
        map_: Type[maps.Map],
        bbox: Tuple[float, float, float, float],
        zoom: int,
        path: Path,
        tiles_dir: Path,
        img_format: ImageFormat,
        projection: Optional[Proj] = None
) -> None:
    # language=rst
    """
    Construct GeoTIFF file with `bbox` area for `map_` tiles from `tiles_dir` with `zoom` zoom-level
    :param map_: maps.Map subclass, which tiles will be downloaded
    :param bbox: bbox of area coordinates in `projection` reference system in from
    `(min_x, min_y, max_x, max_y)`
    :param zoom:  zoom-level for tiles
    :param path: path for output GeoTIFF
    :param tiles_dir: path to directory that contains necessary tiles
    :param img_format: tiles images format
    :param projection: projection for output GeoTIFF
    :return:
    """
    map_projection_bbox = bbox if projection is None else (
            transform(projection, map_.projection, *bbox[:2]) +
            transform(projection, map_.projection, *bbox[2:])
    )
    corner_tiles = map_.get_corner_tiles(map_projection_bbox, zoom)

    with tempfile.NamedTemporaryFile(suffix='.tiff') as uncut_file:
        merge_in_gtiff(map_, corner_tiles, uncut_file.name, tiles_dir, img_format, projection)

        with rio.open(uncut_file.name) as img:
            meta = img.meta.copy()

            cropped_data, meta['transform'] = rio.mask.mask(
                img, [Polygon.from_bounds(*bbox), ], crop=True
            )

    meta['height'], meta['width'] = cropped_data.shape[-2:]
    with rio.open(path, 'w', **meta) as file:
        for i in range(meta['count']):
            file.write(cropped_data[i], i + 1)


def download_in_gtiff(
        map_: Type[maps.Map],
        bbox: Tuple[float, float, float, float],
        zoom: int,
        path: Path,
        tiles_dir: Union[str, Path, None],
        img_format: ImageFormat,
        session: requests.Session,
        projection: Optional[Proj] = None,
        *,
        overwriting=False,
) -> None:
    # language=rst
    """
    Download `map_` image data of `bbox` area and `zoom` zoom-level as a GeoTIFF file.
    :param map_: maps.Map subclass, which tiles will be downloaded
    :param bbox:  bbox of area coordinates in `projection` reference system in from
    `(min_x, min_y, max_x, max_y)`
    :param zoom: zoom-level for tiles
    :param path: path for output GeoTIFF
    :param tiles_dir: path to directory that contains necessary tiles
    :param img_format: tiles images format
    :param session: object providing requests session
    :param projection: projection for output GeoTIFF
    :param overwriting:  if `True`, will overwrite files with expected tiles names.
    if `False`, will skip existent files with expected tiles names.
    :return:
    """
    map_bbox = bbox if projection is None else (
        transform(projection, map_.projection, *bbox[:2]) +
        transform(projection, map_.projection, *bbox[2:])
    )

    download_tiles(map_, map_bbox, zoom, tiles_dir, img_format, session, overwriting=overwriting)
    construct_gtiff(map_, bbox, zoom, path, tiles_dir, img_format, projection)
