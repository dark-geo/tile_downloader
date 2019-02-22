import maps
from tile_downloader import download_in_gtiff

if __name__ == "__main__":
    # download_tiles("./tiles",
    #                bbox=(47.3760346, -60.1171875, 50.0571388, -52.5036621),
    #                zoom=7,
    #                map_=maps.ThunderforestLandscape)

    download_in_gtiff("./tiles/Newfoundland_and_labrador.tiff",
                      bbox=(47.3760346, -60.1171875, 50.0571388, -52.5036621),
                      zoom=19,
                      map_=maps.ThunderforestLandscape)
