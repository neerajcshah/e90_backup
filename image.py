from PIL import Image
from optparse import OptionParser

import sys
import math
import json
import time
import utm
import numpy as np

'''
MIN_LAT = 39.902725 
MAX_LAT = 39.908450
MAX_LON = -75.349260
MIN_LON = -75.35727
'''

# Large dataset bounds

MIN_LAT = 39.902541
MAX_LAT = 39.909508
MAX_LON = -75.351278
MIN_LON = -75.357601


MIN_EAST, MAX_NORTH, _, _ = utm.from_latlon(MIN_LAT, MIN_LON)
MAX_EAST, MIN_NORTH, _, _ = utm.from_latlon(MAX_LAT, MAX_LON)

EAST_LEN = MAX_EAST - MIN_EAST
NORTH_LEN = MAX_NORTH - MIN_NORTH

DRAW_DOTS=False

MAX_X = 1000
MAX_Y = 1000


def main():

  parser = OptionParser()
  parser.add_option('-f', '--fnames', help='JSON Files')
  parser.add_option('-o', '--outfile', type='string', help='Name of output image')
  parser.add_option('-m', '--mac', type='string', help='Single MAC Address')

  (options, args) = parser.parse_args()

  if(len(options.fnames) < 1):
    print("ERROR: At least one JSON file requred.")
    exit(0)
  else:
    createLayer([options.fnames] + args, options.outfile, options.mac)

# Build the map
def createLayer(fnames, dest, mac):

  x = []
  y = []
  f = []

  for name in fnames:
    points = process(name, mac)

    # Convert dbm to magnitude
    points = [[dbmToScale(dbm), SSID, float(lat), float(lon)] for (dbm, SSID, lat, lon) in points if lat != 'n/a'] 
    for i in range(len(points)):
      e,n,_,_ = utm.from_latlon(points[i][2],points[i][3])
      points[i][2] = e
      points[i][3] = n
      if points[i][0] > 0:
          x.append(points[i][2]) #EAS
          y.append(points[i][3]) #NOR
          f.append(points[i][0]) #DBM

  std_dev = 1  

  xyrng = np.arange(MAX_X)
  xgrid, ygrid = np.meshgrid(xyrng, xyrng)

  xgrid = (xgrid/MAX_X)*EAST_LEN + MIN_EAST
  ygrid = (ygrid/MAX_X)*NORTH_LEN + MIN_NORTH

  dnm = np.zeros_like(xgrid)
  num = np.zeros_like(xgrid)

  # Expand in z-dim
  xgrid = xgrid[:,None,:]
  ygrid = ygrid[:,None,:]
  x_y_f = np.array([x, y, f])

  # Create weight with Gaussian PDF
  x = np.array(x_y_f[0])[None,:,None]
  y = np.array(x_y_f[1])[None,:,None]
  f = np.array(x_y_f[2])[None,:,None]
  x_y_f = None

  # Write image in chunks in conserve memory
  chunk = len(xgrid)//8
  pixels = None
  for i in range(8):
    weight = np.exp(-(np.square((xgrid[chunk*i:chunk*(i+1),] - x)) + \
             np.square((ygrid[chunk*i:chunk*(i+1),] - y))) / (2.0*std_dev**2))

    # Build num from weight and sample f 
    dnm = np.sum(weight,axis=1)
    num = np.sum(weight * f, axis=1)
    pixels1 = np.where(dnm < 1e-20, None, num/dnm) 
    if i != 0:
      pixels = np.concatenate((pixels, pixels1))
    else:
      pixels = pixels1

  # Create Image
  I = Image.new('RGBA', (MAX_X, MAX_Y), (255,0,0,0))
  # I.putalpha(32)
  IM = I.load()
  for x in range(MAX_X):
      for y in range(MAX_Y):
          IM[y,x] = color(pixels[x,y])
  if DRAW_DOTS:
      for _, _, e, n in points:
          x, y = en_to_pixel(e, n)
          if 0 <= x < MAX_X and 0 <= y < MAX_Y:
              IM[x,y] = (0,0,0)

  if dest:
    I.save("new-public/images/" + dest + ".png", "PNG")
    print("Image written to : new-public/images/" + dest + ".png !")
  else:
    I.save("new-public/images/output.png", "PNG")
    print("Image written to : new-public/images/output.png !")


### Read points and build a 'points' array of quadruples
def process(fname, mac):
  points = []
  with open(fname) as f:
    data = json.load(f)
    for item in data['JsonData']:
      min_dbm = float('-inf')
      for wifi in item['wifi']:

        # f0:5c:19:ad:5a:60
        if mac:
          if wifi['MAC'] == mac:
            min_dbm = float(wifi['DBM'])
        else:
          if (wifi['SSID'] == 'eduroam' and float(wifi['DBM']) > min_dbm):
            min_dbm = float(wifi['DBM'])

      points.append((min_dbm, 'eduroam', item['Latitude'], item['Longitude']))
    
  return points

def color(val):
    stride = 2.5

    if val is None:
        return (255,0,0,0)

    blue = int(math.cos(val*math.pi/2) * 255)
    green = int(math.sin(val*math.pi) * 255)
    red = int(math.cos((val-1)*(math.pi/2)) * 255)

    '''
    blue = sinusoid(.5,.5,1,0, val)
    green = sinusoid(.5,.5,1,.33, val)
    red = sinusoid(.5,.5,1,.67, val)
    return (int(255*red), int(255*green), int(255*blue))
    '''
    return (red, green, blue)


def sinusoid(a,b,c,d,val):
    
    return (a + b*math.cos(2*math.pi*(c*val + d)))

def pixel_to_en(x,y):

    east = (float(x)/MAX_X)*EAST_LEN + MIN_EAST
    north = (float(y)/MAX_Y)*NORTH_LEN + MIN_NORTH
    
    return east, north

def en_to_pixel(east,north):

    x = int(((east-MIN_EAST)/EAST_LEN)*MAX_X)
    y = int(((north-MIN_NORTH)/NORTH_LEN)*MAX_Y)
    return x,y

def distance_squared(x1,y1,x2,y2):
    return (x1-x2)**2 + (y1-y2)**2

def distance(x1,y1,x2,y2):
    return math.sqrt(distance_squared(x1,y1,x2,y2))

def dbmToScale(dbm):
  # Scales dbm so that it is real/positive
  if dbm < -90:
    return 0.0
  elif dbm > -50:
    return 1.0
  else:
    return (dbm + 90)/(40.0)


main()
