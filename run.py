# -*- coding: utf-8 -*-

import argparse
import circlify as circ
import os
from pprint import pprint
import sys

from lib import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-config', dest="CONFIG_FILE", default="config.json", help="Input config .json file")
parser.add_argument('-here', dest="HERE_KEY", default="trilobites", help="Which media array this video is embedded in; it should map to a key in 'mediaArrays' in config file")
parser.add_argument('-width', dest="WIDTH", default=1080, type=int, help="Width of video")
parser.add_argument('-height', dest="HEIGHT", default=1080, type=float, help="Height of video")
parser.add_argument('-out', dest="OUTPUT_FILE", default="", help="Name of the output file; leave blank and it will be output/{HERE_KEY}.mp4")
parser.add_argument('-debug', dest="DEBUG", action="store_true", help="Just output an image of the data")
a = parser.parse_args()
# Parse arguments

config = readJSON(a.CONFIG_FILE)

collectionsData = config['data']
flattenedData = flattenTree(collectionsData)

# add datums where they don't exist
flattenedData = sorted(flattenedData, key=lambda d: -d['level'])
for i, d in enumerate(flattenedData):
    if 'datum' not in d:
        flattenedData[i]['datum'] = sum([dd['datum'] for dd in flattenedData if 'parent' in dd and dd['parent']==d['id'] and 'datum' in dd])
dataLookup = createLookup(flattenedData)

# flattenedData = sorted(flattenedData, key=lambda d: d['level'])
# pprint(flattenedData)
