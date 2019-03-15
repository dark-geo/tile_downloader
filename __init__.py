import maps
from tile_downloader import download_in_gtiff
from pathlib import Path

if __name__ == "__main__":
    # bbox = (-60.1171875, 47.3760346, -52.5036621, 50.0571388)  # Newfoundland_and_labrador
    # bbox = (-56.1346436, 48.8701349, -54.7174072, 49.6213871)  # Newfoundland_and_labrador
    # bbox = (-56.13, 48.87, -55.77, 49.00)  # Newfoundland_and_labrador
    # bbox = (30.33, 59.99, 45, 60)  # long lat stripe
    # bbox = (30.33, 47, 30.34, 60)  # long stripe
    bbox = (29.658204, 59.866539, 30.505907, 60)  # spb

    zoom = 14
    map = maps.BingSatellite

    path_to_home = Path.home()  # path to home dir
    path_to_tiff = path_to_home / 'Desktop' / 'tiffka1.tiff'
    path_to_tiles = Path.home() / 'Desktop' / 'tily/'

    # path = r'/home/konstantin/Рабочий стол/tiffka.tiff'
    # path_to_tiles = r'/home/konstantin/Рабочий стол/tily2'
    # path = "./tiles/Newfoundland_and_labrador.tiff"

    # path_to_tiles.mkdir(exist_ok=True, parents=True)

    download_in_gtiff(path_to_tiff, bbox, zoom, map, path_to_tiles=path_to_tiles)
