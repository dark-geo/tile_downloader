import maps
from tile_downloader import download_in_gtiff

if __name__ == "__main__":
    # download_tiles("./tiles",
    #                bbox=(47.3760346, -60.1171875, 50.0571388, -52.5036621),
    #                zoom=7,
    #                map_=maps.ThunderforestLandscape)

    download_in_gtiff("./tiles/Newfoundland_and_labrador.tiff",
                      # bbox=(47.3760346, -60.1171875, 50.0571388, -52.5036621),
                      # bbox=(48.8701349, -56.1346436, 49.6213871, -54.7174072),
                      bbox=(48.87, -56.13, 49.00, -55.77),
                      zoom=14,
                      map_=maps.ArcGISWorldLDarkGrayReference)
