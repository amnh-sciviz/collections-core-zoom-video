# -*- coding: utf-8 -*-

import argparse
import os
from pprint import pprint
import subprocess
import sys

from lib import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-config', dest="CONFIG_FILE", default="config.json", help="Input config .json file")
parser.add_argument('-width', dest="WIDTH", default=1080, type=int, help="Width of video")
parser.add_argument('-height', dest="HEIGHT", default=1080, type=int, help="Height of video")
parser.add_argument('-fps', dest="FPS", default=30, type=int, help="Frames per second of video")
parser.add_argument('-overwrite', dest="OVERWRITE", action="store_true", help="Overwrite existing file")
parser.add_argument('-debug', dest="DEBUG", action="store_true", help="Just output an image of the data")
a = parser.parse_args()

config = readJSON(a.CONFIG_FILE)
py = sys.executable


if a.DEBUG:
    flattenedData = flattenTree(config['data'])
    ids = [d['id'] for d in flattenedData]
    arrayIds = []
    # print make sure parents exists
    for id, props in config['mediaArrays'].items():
        parent = props['parent']
        if parent not in ids:
            print(f'Could not find {parent} in ids')
        arrayIds.append(props['id'])
    # check for duplicates
    allIds = [{'id': id} for id in (ids + arrayIds)]
    groupedIds = groupBy(allIds, 'id')
    dupes = [group for group in groupedIds if group['count'] > 1]
    print(f'Found {len(dupes)} dupes')
    for dupe in dupes:
        print(f"- {dupe['id']}")
    print('---------------')

for array in config['mediaArrays']:
    fn = f'output/{array}.mp4'
    if not a.OVERWRITE and os.path.isfile(fn):
        print(f'Already created {fn}.')
        continue
    command = [
            py, 'run.py',
            '-array', array,
            '-width', str(a.WIDTH),
            '-height', str(a.HEIGHT),
            '-fps', str(a.FPS)]
    print(" ".join(command))
    if a.DEBUG:
        continue
    finished = subprocess.check_call(command)
print('Done.')