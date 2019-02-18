# Tile downloader
 - For common tile downloading use `tile_downloader.download_tiles`  
 
 - For downloading in GeoTiff (with georeference) use `tile_downloader.download_in_gtiff`
   
 - To use custom map service create `maps.Map` and set 
  `maps.Map.get_urls_gen` with url template,
  `maps.Map.tiles_format` by one of `utils.ImageFormat`
 (works properly for maps with images of spherical projection)
 