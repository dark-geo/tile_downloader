import tempfile
import time
from pathlib import Path
from typing import Union, Tuple, Type, Optional

import cv2
import rasterio as rio
import rasterio.mask
import requests
from pygeotile.tile import Tile
from shapely.geometry import Polygon

import maps
from utils import ImageFormat, get_tile_gen, get_filename, get_bbox_in_tms, get_tiles_bbox

CRS = 'EPSG:4326'


def download_tiles(
        tiles_dir: Union[Path, str],
        bbox: Tuple[float, float, float, float],
        zoom: int,
        map_: Type[maps.Map],
        proxies: Optional[dict] = None
) -> None:
    # language=rst
    """
    download tiles from `bbox` with `zoom` zoomlevel to `tiles_dir` from `map_` using `proxies`
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


def _merge_tiles(
        path: Union[Path, str],
        tiles_dir: Union[Path, str],
        tms_bbox: Tuple[int, int, int, int],
        zoom: int,
        tiles_format: ImageFormat
) -> None:
    # language=rst
    """
    Merge tiles from `tms_bbox` area from `tiles_dir` with `zoom` zoomlevel and `tiles_format` image format
    in image file with `path` without georeference
    :param path:
    :param tiles_dir:
    :param tms_bbox: area of the tms coordinates in the form of:
     `(min_x, min_y, max_x, max_y)`
    :param zoom:
    :param tiles_format:
    :return:
    """
    min_x, min_y, max_x, max_y = tms_bbox

    rows = list()
    for y in range(max_y, min_y - 1, -1):
        row = list()
        for x in range(min_x, max_x + 1):
            tile_path = get_filename(Tile.from_tms(x, y, zoom), tiles_format, tiles_dir)
            row.append(cv2.imread(str(tile_path)))

        row_img = cv2.hconcat(row)
        rows.append(row_img)
    data = cv2.vconcat(rows)

    cv2.imwrite(path, data)


def _megre_tiles_in_gtiff(
        path: Union[Path, str],
        tiles_dir: Union[Path, str],
        tms_bbox: Tuple[int, int, int, int],
        zoom: int,
        tiles_format: ImageFormat
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
    :param tiles_format:
    :return:
    """
    with tempfile.NamedTemporaryFile(suffix='.tiff') as tmfile:
        _merge_tiles(tmfile.name, tiles_dir, tms_bbox, zoom, tiles_format)

        with rio.open(tmfile.name) as tiff_img:
            meta = tiff_img.meta.copy()
            data = tiff_img.read()

    meta['driver'] = 'GTiff'
    meta['crs'] = CRS

    tiles_bbox = get_tiles_bbox(tms_bbox=tms_bbox, zoom=zoom)
    meta['transform'] = rio.transform.from_bounds(
        tiles_bbox[1], tiles_bbox[0], tiles_bbox[3], tiles_bbox[2], tiff_img.width, tiff_img.height
    )

    with rio.open(path, 'w', **meta) as file:
        for i in range(meta['count']):
            file.write(data[i], i + 1)


def download_in_gtiff(
        path: Union[Path, str],
        bbox: Tuple[float, float, float, float],
        zoom: int,
        map_: Type[maps.Map]
) -> None:
    # language=rst
    """
    Download tiles data in GeoTiff file to `path`
    from `bbox` area with zoomlevel `zoom` using `map_`
    :param path:
    :param bbox: area of the tms coordinates in the form of:
     `(min_x, min_y, max_x, max_y)`
    :param zoom:
    :param map_:
    :return:
    """
    with tempfile.NamedTemporaryFile() as tmfile:
        with tempfile.TemporaryDirectory() as t_dir:
            download_tiles(t_dir, bbox, zoom, map_)
            tms_bbox = get_bbox_in_tms(bbox, zoom)
            _megre_tiles_in_gtiff(tmfile.name, t_dir, tms_bbox, zoom, map_.tiles_format)

        img = rio.open(tmfile.name)
        meta = img.meta.copy()

        cropped_data, meta['transform'] = rio.mask.mask(
            img,
            [Polygon.from_bounds(*bbox[1::-1], *bbox[:1:-1]), ],
            crop=True
        )

        meta['width'], meta['height'] = cropped_data.shape[:-3:-1]
    with rio.open(path, 'w', **meta) as file:
        for i in range(meta['count']):
            file.write(cropped_data[i], i + 1)
