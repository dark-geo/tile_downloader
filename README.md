# Tile downloader

Small package for downloading maps services tiled image data, 
and for constructing GeoTIFF files containing these data.

 - For common tile downloading use `tile_downloader.download_tiles`
 
 - For constructing GeoTIFF (image with geo-reference) from downloaded tiles 
 use `tile_downloader.construct_gtiff`
 
 - For downloading data in GeoTiff use `tile_downloader.download_in_gtiff`. 
 You can use downloaded tiles by defining those directory in this function.
   
 - To use custom map service create `maps.Map` and set 
  `maps.Map.get_urls_gen` with url template,
  `maps.Map.projection` with right map images projection.
 
 For example, if you want your own image of Australia in GeoTIFF, 
run this:
 ```python
from tile_downloader import download_in_gtiff

download_in_gtiff(
    'BingSatellite',
    'my/path/to/my/australia.tiff',
    min_lat=-38.349326,
    max_lat=-10.550982,
    min_lon=111.905820,
    max_lon=155.047867,
    zoom=4
)
```
 