import os
import tempfile
import time
from pathlib import Path
from typing import Union, Tuple, Type, Optional

import cv2
import rasterio as rio
import rasterio.mask
import requests
from pygeotile.tile import Tile
from pygeotile.point import Point
from shapely.geometry import Polygon

import maps
from utils import ImageFormat, get_tile_gen, get_filename, get_bbox_in_tms, get_tiles_bbox


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
    data = cv2.vconcat(rows)

    cv2.imwrite(path, data)


def _merge_tiles_in_gtiff(
        path: Union[Path, str],
        tiles_dir: Union[Path, str],
        tms_bbox: Tuple[int, int, int, int],
        zoom: int,
        map_: Type[maps.Map]
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
    :return:
    """
    with tempfile.NamedTemporaryFile(suffix='.tiff') as tmfile:
        _merge_tiles(tmfile.name, tiles_dir, tms_bbox, zoom, map_.tiles_format)

        bbox = get_tiles_bbox(tms_bbox, zoom)
        ul_point = Point.from_latitude_longitude(bbox[2], bbox[1])
        lr_point = Point.from_latitude_longitude(bbox[0], bbox[3])

        os.system(' '.join([
            'gdal_translate -of GTiff -co BIGTIFF=YES -co NUM_THREADS=8',
            '-a_ullr {} {} {} {}'.format(*ul_point.meters, *lr_point.meters),
            f'-a_srs {map_.crs} {tmfile.name} {path}'
        ]))


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
    ul_point = Point.from_latitude_longitude(bbox[2], bbox[1])
    lr_point = Point.from_latitude_longitude(bbox[3], bbox[0])
    min_x_meters, max_x_meters = sorted([ul_point.meters[0], lr_point.meters[0]])
    min_y_meters, max_y_meters = sorted([ul_point.meters[1], lr_point.meters[1]])

    min_lat, min_lon, max_lat, max_lon = bbox


    with tempfile.NamedTemporaryFile() as tmfile1:
        with tempfile.NamedTemporaryFile() as tmfile2:
            with tempfile.TemporaryDirectory() as temp_dir:
                tiles_dir = temp_dir if tiles_dir is None else tiles_dir

                download_tiles(tiles_dir, bbox, zoom, map_, proxies)
                tms_bbox = get_bbox_in_tms(bbox, zoom)
                _merge_tiles_in_gtiff(tmfile2.name, tiles_dir, tms_bbox, zoom, map_)

            os.system(' '.join([
                'gdalwarp -dstalpha -srcnodata 0 -dstnodata 0 -overwrite -wo NUM_THREADS=8',
                f'-co COMPRESS=PACKBITS -co BIGTIFF=YES -s_srs {map_.crs} -t_srs {crs}',
                f'{tmfile2.name} {tmfile1.name}'
            ]))

        img = rio.open(tmfile1.name)
        meta = img.meta.copy()


        cropped_data, meta['transform'] = rio.mask.mask(
            img,
            # [Polygon.from_bounds(min_x_meters, min_y_meters, max_x_meters, max_y_meters), ],
            [Polygon.from_bounds(min_lon, min_lat, max_lon, max_lat), ],
            crop=True
        )

        meta['height'], meta['width'] = cropped_data.shape[-2:]
    with rio.open(path, 'w', **meta) as file:
        for i in range(meta['count']):
            file.write(cropped_data[i], i + 1)
