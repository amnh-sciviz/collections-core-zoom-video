# -*- coding: utf-8 -*-

import glob
import itertools
import json
import math
from operator import itemgetter
import os
from PIL import Image
import random
import subprocess
import sys

def addIndices(arr, keyName="index", startIndex=0):
    for i, item in enumerate(arr):
        arr[i][keyName] = startIndex + i
    return arr

def alphaMask(im, mask):
    w, h = im.size
    transparentImg = Image.new(mode="RGBA", size=(w, h), color=(0, 0, 0, 0))
    mw, mh = mask.size
    if mw != w or mh != h:
        mask = mask.resize((w, h), PIL.Image.BICUBIC)
    return Image.composite(im, transparentImg, mask)

# https://stackoverflow.com/questions/401847/circle-rectangle-collision-detection-intersection
def circleRectIntersects(circle, rect):
    circleDistanceX = abs(circle['x'] - rect['x'])
    circleDistanceY = abs(circle['y'] - rect['y'])

    if circleDistanceX > (rect['w']/2.0 + circle['r']):
        return False

    if circleDistanceY > (rect['h']/2.0 + circle['r']):
        return False

    if circleDistanceX <= (rect['w']/2.0):
        return True

    if circleDistanceY <= (rect['h']/2.0):
        return True

    cornerDistance_sq = (circleDistanceX - rect['w']/2.0) ** 2 + (circleDistanceY - rect['h']/2.0) ** 2;

    return (cornerDistance_sq <= (circle['r'] ** 2))

def compileFrames(infile, fps, outfile, padZeros, quality="high"):
    print("Compiling frames...")
    padStr = '%0'+str(padZeros)+'d'

    # https://trac.ffmpeg.org/wiki/Encode/H.264
    # presets: veryfast, faster, fast, medium, slow, slower, veryslow
    #   slower = better quality
    # crf: 0 is lossless, 23 is the default, and 51 is worst possible quality
    #   17 or 18 to be visually lossless or nearly so
    preset = "veryslow"
    crf = "18"
    if quality=="medium":
        preset = "medium"
        crf = "23"
    elif quality=="low":
        preset = "medium"
        crf = "28"

    command = ['ffmpeg','-y',
                '-framerate',str(fps)+'/1',
                '-i',infile % padStr,
                '-c:v','libx264',
                '-preset', preset,
                '-crf', crf,
                '-r',str(fps),
                '-pix_fmt','yuv420p',
                # '-q:v','1',
                outfile]

    print(" ".join(command))
    finished = subprocess.check_call(command)
    print("Done.")

def createLookup(arr, key):
    return dict([(str(item[key]), item) for item in arr])

def ease(n):
    return (math.sin((n+1.5)*math.pi)+1.0) / 2.0

def flattenTree(nodes):
    results = []
    level = 1
    while 1:
        newNodes = []
        if len(nodes) == 0:
            break
        for node in nodes:
            if 'children' in node and len(node['children']) > 0:
                for child in node['children']:
                    child['parent'] = node['id']
                    newNodes.append(child)
            node['level'] = level
            node.pop('children', None)
            results.append(node)
        nodes = newNodes
        level += 1
    return results

def formatNumber(n):
    return "{:,}".format(n)

def groupBy(arr, groupBy):
    groups = []
    arr = sorted(arr, key=itemgetter(groupBy))
    for key, items in itertools.groupby(arr, key=itemgetter(groupBy)):
        group = {}
        litems = list(items)
        count = len(litems)
        group[groupBy] = key
        group["items"] = litems
        group["count"] = count
        groups.append(group)
    return groups

def isBetween(value, ab, inclusive=True):
    a, b = ab
    if inclusive:
        return a <= value <= b
    else:
        return a < value < b

def isNumber(n):
    try:
        float(n)
    except ValueError:
        return False
    return True

def lerp(ab, amount):
    a, b = ab
    return (b-a) * amount + a

def makeDirectories(filenames):
    if not isinstance(filenames, list):
        filenames = [filenames]
    for filename in filenames:
        dirname = os.path.dirname(filename)
        if len(dirname) > 0 and not os.path.exists(dirname):
            os.makedirs(dirname)

def msToFrame(ms, fps):
    return roundInt((ms / 1000.0) * fps)

def norm(value, ab):
    a, b = ab
    n = 0.0
    if (b - a) != 0:
        n = 1.0 * (value - a) / (b - a)
    return n

def printProgress(step, total, prepend=""):
    sys.stdout.write('\r')
    sys.stdout.write("%s%s%%" % (prepend, round(1.0*step/total*100,2)))
    sys.stdout.flush()

def readJSON(filename):
    data = {}
    if os.path.isfile(filename):
        with open(filename, encoding="utf8") as f:
            data = json.load(f)
    return data

def removeFiles(listOrString):
    filenames = listOrString
    if not isinstance(listOrString, list) and "*" in listOrString:
        filenames = glob.glob(listOrString)
    elif not isinstance(listOrString, list):
        filenames = [listOrString]
    print("Removing %s files" % len(filenames))
    for fn in filenames:
        if os.path.isfile(fn):
            os.remove(fn)

def roundInt(n):
    return int(round(n))

def floorToNearest(n, nearest):
    return 1.0 * math.floor(1.0*n/nearest) * nearest

def smartRound(n):
    if n < 1000:
        return n
    if n < 1000000:
        return floorToNearest(n, 1000)
    if n < 10000000:
        return floorToNearest(n, 10000)
    return floorToNearest(n, 100000)

def unflattenData(nodes):
    nodeLookup = createLookup(nodes, 'id')
    nodes = sorted(nodes, key=lambda d: -d['level'])
    nodes = addIndices(nodes)
    for i, node in enumerate(nodes):
        if 'parent' in node and node['parent'] in nodeLookup:
            parent = nodeLookup[node['parent']]
            children = []
            if 'children' in parent:
                children = parent['children'][:]
            children.append(node)
            nodes[parent['index']]['children'] = children
    roots = [node for node in nodes if 'parent' not in node or not node['parent']]
    return roots

def wrapNumber(value, ab):
    a, b = ab
    if isBetween(value, ab):
        return value
    return (value - a) % (b - a + 1) + a

def zeroPad(value, total):
    padding = len(str(total))
    return str(value).zfill(padding)
