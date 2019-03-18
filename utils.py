import mimetypes
from enum import Enum
from pathlib import Path
from typing import Union, Optional, Type

from darkgeotile import BaseTile


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


def get_expected_path(tile: Type[BaseTile], img_dir: Union[str, Path], img_format: ImageFormat) -> Path:
    # language=rst
    """
    :param tile:
    :param img_format:
    :param img_dir:
    :return: expected path for tile
    """
    return Path(img_dir).joinpath(tile.quad_tree).with_suffix(img_format.suffix)
