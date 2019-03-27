import mimetypes
from enum import Enum
from pathlib import Path
from typing import Union, Optional, Type

from darkgeotile import BaseTile
import humanize
import tqdm
import math


class ImageFormat(Enum):
    JPEG = JPG = ('image/jpeg', '.jpg')
    PNG = 'image/png'
    GIF = 'image/gif'

    def __init__(self, mimetype: str, default_suffix: Optional[str] = None) -> None:
        self.mimetype = mimetype

        self.possible_suffixes = [suf for suf, type_ in mimetypes.types_map.items() if type_ == mimetype]
        self.default_suffix = default_suffix
        self.set_suffix(self.possible_suffixes[0] if default_suffix is None else default_suffix)

    def set_suffix(self, suffix: str) -> None:
        if suffix not in self.possible_suffixes:
            raise Exception
        self.suffix = suffix

    @classmethod
    def get_by(cls, *, suffix, asserting=False):
        for img_format in cls:
            if suffix in img_format.possible_suffixes:
                return img_format

        if asserting:
            raise Exception('unknown image format')


class TileDownloadingProgressbar(tqdm.tqdm):
    def __init__(self, *args, **kwargs):
        self.avg_bytes_in_img = 0
        self.sample_len = 0

        super().__init__(*args, **kwargs)

        self.ascii = " 123456789▪"
        if self.bar_format is None:
            self.bar_format = '{desc}: {percentage:3.0f}% [{bar}]  {n_fmt}/{total_fmt} tiles, about {rest_size} left'

    @property
    def format_dict(self):
        format_dict = super().format_dict
        format_dict.update({'rest_size': humanize.naturalsize((self.total - self.n) * self.avg_bytes_in_img)})
        return format_dict

    def update_avg_bytes_in_img(self, bytes_in_new_img):
        self.avg_bytes_in_img = (self.avg_bytes_in_img * self.sample_len + bytes_in_new_img) // (self.sample_len + 1)
        self.sample_len += 1


def get_expected_path(tile: Type[BaseTile], img_dir: Union[str, Path], img_format: ImageFormat) -> Path:
    # language=rst
    """
    :param tile:
    :param img_format:
    :param img_dir:
    :return: expected path for tile
    """
    dir_ = Path(img_dir).joinpath(f'zoomlevel_{tile.zoom}')
    return dir_.joinpath(f'tms_{tile.tms_x}_{tile.tms_y}').with_suffix(img_format.suffix)
