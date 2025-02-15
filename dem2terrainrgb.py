import argparse
import subprocess
import os
import shutil
import glob
from PIL import Image
from tqdm import tqdm


class Dem2TerrainRgb(object):
  """
  Class for converting DEM file to terrain RGB raster tilesets.
  This source code was inspired from the below repository.

  https://github.com/syncpoint/terrain-rgb
  """

  def __init__(self, dem, dist, tmp, zoom="5-15") -> None:
    """Constructor

    Args:
        dem (str): DEM file path. The DEM file must be reprojected to EPSG:3857 before converting.
        dist (str): Output directory for terrain RGB tiles
        tmp (str): Temporary directory for work
        zoom (str): Min and Max zoom levels for tiles. Default is 5-15.
    """
    self.dem = dem
    self.dist = dist
    self.tmp = tmp
    self.zoom = zoom

  def fill_nodata(self):
    """
    Fill NO DATA value. Before we rgbify, all of NO DATA values need to be filled.

    After this process, you may validate the converted tiff by following command.

    $ rio info --indent 2 ./data/rwanda_dem_EPSG3857_10m_without_nodata.tif

    Returns:
        str: Filled DEM file path
    """
    if not os.path.exists(self.tmp):
      os.makedirs(self.tmp)
    filename = os.path.splitext(os.path.basename(self.dem))[0]
    filled_file = f"{self.tmp}/{filename}_without_nodata.tif"

    if os.path.exists(filled_file):
      os.remove(filled_file)

    cmd = f"gdalwarp \
          -t_srs EPSG:3857 \
          -dstnodata None \
          -co TILED=YES \
          -co COMPRESS=DEFLATE \
          -co BIGTIFF=IF_NEEDED \
          {self.dem} \
          {filled_file}"
    subprocess.check_output(cmd, shell=True)
    print(f"filled NODATA value successfully: {filled_file}")
    return filled_file

  def rgbify(self, filled_dem):
    """
    transform the greyscale data into the RGB data. The formula used to calculate the elevation is

    height = -10000 + ((R * 256 * 256 + G * 256 + B) * 0.1)
    So the base value is -10000 and the interval (precision of the output) is 0.1.

    After rgbfying, you can validate by following command.
    
    $ gdallocationinfo -wgs84 ./data/rwanda_dem_EPSG3857_10m_RGB.tif 29.7363 -2.2313
    Report:
      Location: (8617P,13218L)
      Band 1:
        Value: 1
      Band 2:
        Value: 199
      Band 3:
        Value: 250
    (rwanda_terrain)

    Args:
        filled_dem ([type]): [description]

    Returns:
        [type]: [description]
    """
    filename = os.path.splitext(os.path.basename(self.dem))[0]
    rgbified_dem = f"{self.tmp}/{filename}_RGB.tif"

    if os.path.exists(rgbified_dem):
      os.remove(rgbified_dem)

    cmd = f"rio rgbify \
          -b -10000 \
          -i 0.1 \
          {filled_dem} \
          {rgbified_dem}"

    subprocess.check_output(cmd, shell=True)
    print(f"rgbified successfully: {rgbified_dem}")
    return rgbified_dem

  def gdal2tiles(self, rgbified_dem):
    """Generate tiles as PNG format.
    see about gdal2tiles:
    https://gdal.org/programs/gdal2tiles.html
    Args:
        rgbified_dem (str): Rgbified DEM file path

    Returns:
        str: Output directory path
    """
    if os.path.exists(self.dist):
      shutil.rmtree(self.dist)

    cmd = f"gdal2tiles.py \
          --zoom={self.zoom} \
          --resampling=near \
          --tilesize=512 \
          --processes=8 \
          --xyz {rgbified_dem} \
          {self.dist}"

    subprocess.check_output(cmd, shell=True)
    print(f"created tileset successfully: {self.dist}")
    return self.dist

  def png2webp(self, removePNG=False):
    files = glob.glob(self.dist + '/**/*.png', recursive=True)
    for file in tqdm(files):
      img = Image.open(file)
      img.save(file.replace('.png','.webp'), "WEBP", lossless=True)
      if removePNG:
        os.remove(file)


def get_parser():
  prog = "dem2terrainrgb.py"
  parser = argparse.ArgumentParser(
      prog=prog,
      usage="%(prog)s --dem {dem file path} --dist {output directory path} --tmp {temporary directory path} --webp --remove_png --zoom {min-max zoom}",
      description="This module is to convert DEM to terrain RGB raster tiles."
  )

  parser.add_argument("--dem", dest="dem", required=True, help="Original DEM file. It must be already reprojected to EPSG:3857 before converting.")
  parser.add_argument("--dist", dest="dist", required=True, help="Output directory for tiles")
  parser.add_argument("--tmp", dest="tmp", required=False, default="./tmp", help="Temporary work directory")
  parser.add_argument('--webp', action='store_true', help="Use this option if you want to convert PNG to webp tiles")
  parser.add_argument('--remove_png', action='store_true', help="Use '--webp' option together. If this option is used, it will remove all of original PNG tiles.")
  parser.add_argument("--zoom", dest="zoom", required=False, default="5-15", help="Specify min-max zoom level for tiles. Default is 5-15.")

  return parser


if __name__ == "__main__":
  parser = get_parser()
  args = parser.parse_args()
  dem2terrain = Dem2TerrainRgb(args.dem, args.dist, args.tmp, args.zoom)
  filled_dem = dem2terrain.fill_nodata()
  rgbified_dem = dem2terrain.rgbify(filled_dem)
  dem2terrain.gdal2tiles(rgbified_dem)
  if args.webp:
    dem2terrain.png2webp(args.remove_png)
