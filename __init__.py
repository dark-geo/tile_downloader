import maps
from tile_downloader import download_in_gtiff

if __name__ == "__main__":
    bbox = (59.866539, 29.658204, 60, 30.505907)  # spb
    # bbox = (47, 30.33, 60, 30.34)  # long stripe
    # bbox = (59.99, 30.33, 60, 45)  # long lat stripe
    # bbox=(47.3760346, -60.1171875, 50.0571388, -52.5036621)
    # bbox=(48.8701349, -56.1346436, 49.6213871, -54.7174072)
    # bbox=(48.87, -56.13, 49.00, -55.77)
    # bbox = (48.87, -56.13, 49.00, -55.77)

    zoom = 14
    map_ = maps.GoogleSatellite
    path = r'/Users/konstantin/Desktop/tiffka.tiff'
    tiles_dir = r'/Users/konstantin/Desktop/tily'
    # path = r'/home/konstantin/Рабочий стол/tiffka.tiff'
    # tiles_dir = r'/home/konstantin/Рабочий стол/tily'
    # path = "./tiles/Newfoundland_and_labrador.tiff"

    download_in_gtiff(path, bbox, zoom, map_, tiles_dir=tiles_dir)
