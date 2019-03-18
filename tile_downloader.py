from inspect import isclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Union, Type, Optional

import requests
from pyproj import transform, Proj

import maps
from _tile_downloader import download_in_gtiff as _download_in_gtiff, download_tiles as _download_tiles, \
    construct_gtiff as _construct_gtiff
from utils import ImageFormat


def _get_projection(**kwargs):
    proj = kwargs.get('projection')

    if 'crs' in kwargs:
        if proj is not None:
            raise TypeError

        proj = Proj(kwargs['crs'])

    if 'srs' in kwargs:
        if proj is not None:
            raise TypeError

        proj = Proj(kwargs['srs'])

    return Proj(init='EPSG:4326') if proj is None else proj


def _get_area_args_as_bbox(**kwargs):
    bbox = kwargs.get('bbox')

    if {'min_x', 'min_y', 'max_x', 'max_y'} & kwargs.keys():
        if bbox is not None:
            raise TypeError

        bbox = kwargs['min_x'], kwargs['min_y'], kwargs['max_x'], kwargs['max_y']

    if {'left', 'right', 'bottom', 'top'} & kwargs.keys():
        if bbox is not None:
            raise TypeError

        bbox = kwargs['left'], kwargs['bottom'], kwargs['right'], kwargs['top']

    if {'min_lat', 'min_lon', 'max_lat', 'max_lon'} & kwargs.keys():
        if bbox is not None:
            raise TypeError

        proj = _get_projection(**kwargs)
        bbox = (
            transform(Proj(proj='latlong'), proj, kwargs['min_lon'], kwargs['min_lat']) +
            transform(Proj(proj='latlong'), proj, kwargs['max_lon'], kwargs['max_lat'])
        )

    if bbox is None:
        raise TypeError

    return bbox


def _get_zoom(**kwargs):
    zoom = kwargs.get('zoom')

    if 'zoomlevel' in kwargs:
        if zoom is not None:
            raise TypeError

        zoom = kwargs['zoomlevel']

    if zoom is None:
        raise TypeError

    return zoom


def download_tiles(
        map_: Union[Type[maps.Map], str],
        tiles_dir: Union[Path, str],
        img_format: Union[ImageFormat, str] = ImageFormat.PNG,
        *,
        proxies: Optional[dict] = None,
        overwriting: bool = False,
        **kwargs
) -> None:
    # language=rst
    """
    Download `map_` tiles from given area with certain zoom-level to `tiles_dir` from `map_`.
    :param map_: maps.Map subclass, which tiles will be downloaded, or name of that subclass from maps.py
    :param tiles_dir: path to directory for downloading
    :param img_format: tiles images format
    :param proxies: dict with protocol standart names as keys and proxies addresses as values
    :param overwriting: if `True`, will overwrite files with expected tiles names.
    if `False`, will skip existent files with expected tiles names.
    :param kwargs:
    ###
    Optional projection keyword
    ###
    As one of the next keywords:
    * `projection` -- py:class:`pyproj.Proj` projection object
    * `crs` of `srs` -- coordinate reference system as PROJ.4 string
    If projection wasn't defined, then will used WGS 84 latitude longitude reference system

    ###
    Area keywords
    ###
    Area bounds should given for given projection in one of the following form:
    * `bbox` of area coordinates in from `(min_x, min_y, max_x, max_y)`
    * `min_x`, `min_y`, `max_x`, `max_y`
    * `left`, `bottom`, `right`, `top`
    * `min_lon`, `min_lat`, `max_lon`, `max_lat` for latitudes and
    longitudes even for non-geographic coordinate systems.

    ###
    Zoom-level keyword
    ###
    Should given as `zoom` or `zoomlevel` keyword

    :return:

    """
    map_ = map_ if isclass(map_) and issubclass(map_, maps.Map) else getattr(maps, map_)
    projection = _get_projection(**kwargs)

    bbox_in_source_projection = _get_area_args_as_bbox(**kwargs)
    bbox_in_map_projection = (
        transform(projection, map_.projection, *bbox_in_source_projection[:2]) +
        transform(projection, map_.projection, *bbox_in_source_projection[2:])
    )

    if not isinstance(img_format, ImageFormat):
        img_format = ImageFormat.get_by(suffix=img_format, asserting=True)

    session = requests.session()
    if proxies is not None:
        session.proxies = proxies

    _download_tiles(
        map_,
        bbox_in_map_projection,
        _get_zoom(**kwargs),
        Path(tiles_dir),
        img_format,
        session,
        overwriting=overwriting
    )


def construct_gtiff(
        map_: Union[Type[maps.Map], str],
        path: Union[Path, str],
        tiles_dir: Union[Path, str],
        img_format: Union[ImageFormat, str] = ImageFormat.PNG,
        **kwargs
) -> None:
    # language=rst
    """
    Construct GeoTIFF file for area if given projection for `map_` tiles from `tiles_dir` with specified zoom-level
    :param map_: maps.Map subclass, which tiles will be used, or name of that subclass from maps.py
    :param path: path for output GeoTIFF
    :param tiles_dir: path to directory that contains necessary tiles
    :param img_format: tiles images format
    :param kwargs:
    ###
    Optional projection keyword
    ###
    As one of the next keywords:
    * `projection` -- py:class:`pyproj.Proj` projection object
    * `crs` of `srs` -- coordinate reference system as PROJ.4 string
    If projection wasn't defined, then will used WGS 84 latitude longitude reference system

    ###
    Area keywords
    ###
    Area bounds should given for given projection in one of the following form:
    * `bbox` of area coordinates in from `(min_x, min_y, max_x, max_y)`
    * `min_x`, `min_y`, `max_x`, `max_y`
    * `left`, `bottom`, `right`, `top`
    * `min_lon`, `min_lat`, `max_lon`, `max_lat` for latitudes and
    longitudes even for non-geographic coordinate systems.

    ###
    Zoom-level keyword
    ###
    Should given as `zoom` or `zoomlevel` keyword

    :return:
    """
    if not isinstance(img_format, ImageFormat):
        img_format = ImageFormat.get_by(suffix=img_format, asserting=True)

    _construct_gtiff(
        map_ if isclass(map_) and issubclass(map_, maps.Map) else getattr(maps, map_),
        _get_area_args_as_bbox(**kwargs),
        _get_zoom(**kwargs),
        Path(path),
        Path(tiles_dir),
        img_format,
        _get_projection(**kwargs)
    )


def download_in_gtiff(
        map_: Union[Type[maps.Map], str],
        path: Union[Path, str],
        tiles_dir: Union[str, Path, None] = None,
        img_format: ImageFormat = ImageFormat.PNG,
        *,
        proxies: Optional[dict] = None,
        overwriting: bool = False,
        **kwargs
) -> None:
    # language=rst
    """
    Download `map_` image data of area if given projection for specified zoom-level as a GeoTIFF file.
    :param map_: maps.Map subclass, which tiles will be downloaded, or name of that subclass from maps.py
    :param path: path for output GeoTIFF
    :param tiles_dir: optional path to for tiles directory. If `None`, then tiles will be downloaded
    in temporary directory, and will be deleted after creation of a GeoTIFF file.
    :param img_format: tiles images format
    :param proxies: dict with protocol standart names as keys and proxies addresses as values
    :param overwriting: if `True`, during downloading tiles, it will overwrite files with expected tiles names.
    if `False`, will skip existent files with expected tiles names.
    :param kwargs:
    ###
    Optional projection keyword
    ###
    As one of the next keywords:
    * `projection` -- py:class:`pyproj.Proj` projection object
    * `crs` of `srs` -- coordinate reference system as PROJ.4 string
    If projection wasn't defined, then will used WGS 84 latitude longitude reference system

    ###
    Area keywords
    ###
    Area bounds should given for given projection in one of the following form:
    * `bbox` of area coordinates in from `(min_x, min_y, max_x, max_y)`
    * `min_x`, `min_y`, `max_x`, `max_y`
    * `left`, `bottom`, `right`, `top`
    * `min_lon`, `min_lat`, `max_lon`, `max_lat` for latitudes and
    longitudes even for non-geographic coordinate systems.

    ###
    Zoom-level keyword
    ###
    Should given as `zoom` or `zoomlevel` keyword

    :return:
    """
    if not isinstance(img_format, ImageFormat):
        img_format = ImageFormat.get_by(suffix=img_format, asserting=True)

    session = requests.session()
    if proxies is not None:
        session.proxies = proxies

    temp_dir = TemporaryDirectory() if tiles_dir is None else None

    _download_in_gtiff(
        map_ if isclass(map_) and issubclass(map_, maps.Map) else getattr(maps, map_),
        _get_area_args_as_bbox(**kwargs),
        _get_zoom(**kwargs),
        Path(path),
        Path(temp_dir.name if tiles_dir is None else tiles_dir),
        img_format,
        session,
        projection=_get_projection(**kwargs),
        overwriting=overwriting
    )

    if temp_dir is not None:
        temp_dir.cleanup()
