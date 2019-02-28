from pathlib import Path

import maps
from tile_downloader import download_in_gtiff

if __name__ == "__main__":
    bbox = (59.866539, 29.658204, 60, 30.505907)  # spb
    # bbox = (47, 30.33, 60, 30.34)  # long stripe
    bbox = (59.99, 30.33, 60, 45)  # long lat stripe
    # bbox = (47.3760346, -60.1171875, 50.0571388, -52.5036621)  # Newfoundland_and_labrador
    # bbox = (48.8701349, -56.1346436, 49.6213871, -54.7174072)  # Newfoundland_and_labrador
    # bbox = (48.87, -56.13, 49.00, -55.77)  # Newfoundland_and_labrador
    # bbox = (48.87, -56.13, 49.00, -55.77)  # Newfoundland_and_labrador

    zoom = 14
    map = maps.GoogleRoad

    path_to_home = Path.home()  # path to home dir
    # path_to_tiff = path_to_home / 'Desktop' / 'tiffka1.tiff'
    # path_to_tiles = Path.home() / 'Desktop' / 'tily/'

    path = r'/home/konstantin/Рабочий стол/tiffka.tiff'
    path_to_tiles = r'/home/konstantin/Рабочий стол/tily2'
    # path = "./tiles/Newfoundland_and_labrador.tiff"

    # path_to_tiles.mkdir(exist_ok=True, parents=True)

    download_in_gtiff(path, bbox, zoom, map, path_to_tiles=path_to_tiles)
