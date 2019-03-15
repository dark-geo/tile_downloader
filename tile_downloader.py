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
from shapely.geometry import Polygon

import maps
from utils import ImageFormat, get_filename
import pyproj


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
    session = requests.session()
    if proxies is not None:
        session.proxies = proxies

    for tile in map_.get_tile_gen(map_bbox, zoom):
        path = get_filename(tile, tiles_format, tiles_dir)

        if not path.exists():
            for url in map_.get_urls_gen(tile):
                response = session.get(url)
                time.sleep(map_.get_timeout())
                if response.ok:
                    with path.open('wb') as file:
                        file.write(response.content)
                    break

    session.close()


def _get_tiles_data(
        tiles_dir: Union[Path, str],
        tiles_rect_nodes,
        zoom: int,
        map_,
        tiles_format
) -> np.ndarray:
    # language=rst
    """
    Merge tiles from `tms_bbox` area from `path_to_tiles` with `zoom` zoomlevel and `tiles_format` image format
    in array
    """
    tiles_dir = Path(tiles_dir)

    tms_x_s, tms_y_s = zip(*(tile.tms for tile in tiles_rect_nodes))
    min_x, min_y, max_x, max_y = min(tms_x_s), min(tms_y_s), max(tms_x_s), max(tms_y_s)

    rows = list()
    for y in range(max_y, min_y - 1, -1):
        row = list()
        for x in range(min_x, max_x + 1):
            tile = map_.Tile.from_tms(x, y, zoom)
            tile_path = get_filename(tile, tiles_format, tiles_dir)

            if not tile_path.exists():
                raise Exception(f"Can't reach tile {tile.quad_tree}")

            row.append(cv2.imread(str(tile_path)))

        row_img = cv2.hconcat(row)
        rows.append(row_img)

    return cv2.vconcat(rows)


def _merge_tiles_in_gtiff(
        path: Union[Path, str],
        tiles_dir: Union[Path, str],
        tiles_rect_nodes,
        zoom: int,
        map_: Type[maps.Map],
        tiles_format,
        proj=None
) -> None:
    # language=rst
    """
    Merge tiles from `tms_bbox` area from `path_to_tiles` with `zoom` zoomlevel and `tiles_format` image format
    in GeoTiff file with `path`
    """
    source_projection = map_.projection
    destination_projection = source_projection if proj is None else proj

    tiles_data = _get_tiles_data(tiles_dir, tiles_rect_nodes, zoom, map_, tiles_format)

    tiles_bounds = sum((tile.bounds for tile in tiles_rect_nodes), tuple())
    x_s, y_s = zip(*tiles_bounds)
    left, right = min(x_s), max(x_s)
    bottom, top = min(y_s), max(y_s)

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
        tiles_format = ImageFormat.PNG,
        path_to_tiles: Union[str, Path, None] = None,
        proxies: Optional[dict] = None
) -> None:
    # language=rst
    """
    Download tiles data in GeoTiff file to `path_to_tiff`
    from `bbox` area with zoomlevel `zoom` using `map_`
    """
    custom_proj = pyproj.Proj(crs)
    map_bbox = (
        pyproj.transform(custom_proj, map_.projection, *bbox[:2]) +
        pyproj.transform(custom_proj, map_.projection, *bbox[2:])
    )

    with tempfile.NamedTemporaryFile(suffix='.tiff') as tmfile:
        with tempfile.TemporaryDirectory() as temp_dir:
            path_to_tiles = temp_dir if path_to_tiles is None else path_to_tiles

            download_tiles(path_to_tiles, map_bbox, zoom, map_, tiles_format, proxies)

            tiles_rectangle_vertices = map_.get_corner_tiles(map_bbox, zoom)
            _merge_tiles_in_gtiff(tmfile.name, path_to_tiles, tiles_rectangle_vertices, zoom, map_, tiles_format, custom_proj)

        img = rio.open(tmfile.name)
        meta = img.meta.copy()

        cropped_data, meta['transform'] = rio.mask.mask(
            img,
            [Polygon.from_bounds(*bbox), ],
            crop=True
        )

    meta['height'], meta['width'] = cropped_data.shape[-2:]
    with rio.open(path_to_tiff, 'w', **meta) as file:
        for i in range(meta['count']):
            file.write(cropped_data[i], i + 1)
