# -*- coding: utf-8 -*-

import argparse
import circlify as circ
import os
from PIL import Image, ImageColor, ImageDraw, ImageFilter, ImageFont
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

RESOLUTION = 2

# testData = [
#     {"id": "A", "datum": 100, "children": [
#         {"id": "AA", "datum": 50, "children": [
#             {"id": "AAA", "datum": 25},
#             {"id": "AAB", "datum": 25}
#         ]},
#         {"id": "AB", "datum": 50, "children": []}
#     ]}
# ]
# circles = circ.circlify(testData)
# pprint(circles)
# sys.exit()

config = readJSON(a.CONFIG_FILE)

data = config['data']
flattenedData = flattenTree(data)

# add here
if a.HERE_KEY not in config['mediaArrays']:
    print(f'Could not find {a.HERE_KEY} in mediaArrays')
    sys.exit()
here = config['mediaArrays'][a.HERE_KEY]
here['isHere'] = True
for i, d in enumerate(flattenedData):
    if d['id'] == here['parent']:
        here['level'] = d['level'] + 1
        children = [here]
        leftover = d['datum'] - here['datum']
        otherCount = 1
        leftoverPerOther = roundInt(1.0 * leftover / otherCount)
        for j in range(otherCount):
            value = leftoverPerOther
            if j == otherCount-1:
                value = leftover - (otherCount-1) * leftoverPerOther
            placeholder = {
                'id': f'Placeholder {j+1}',
                'level': d['level'] + 1,
                'isPlaceholder': True,
                'parent': d['id'],
                'datum': value
            }
            children.append(placeholder)
        flattenedData[i]['children'] = children
        break

# add datums where they don't exist
flattenedData = sorted(flattenedData, key=lambda d: -d['level'])
for i, d in enumerate(flattenedData):
    if 'datum' not in d:
        flattenedData[i]['datum'] = sum([dd['datum'] for dd in flattenedData if 'parent' in dd and dd['parent']==d['id'] and 'datum' in dd])
dataLookup = createLookup(flattenedData, 'id')
# flattenedData = sorted(flattenedData, key=lambda d: d['level'])
# pprint(flattenedData)

data = unflattenData(flattenedData)
# pprint(data)

circles = circ.circlify(data)
circles = sorted(circles, key=lambda c: c.level)
# add indices for easier references later
for i, c in enumerate(circles):
    circles[i].ex['index'] = i
circleLookup = dict([(c.ex['id'], c) for c in circles])
for i, c in enumerate(circles):
    if 'parent' in c.ex and c.ex['parent'] in circleLookup:
        circles[i].ex['parentIndex'] = circleLookup[c.ex['parent']].ex['index']

# circ.bubbles(circles)

def drawCircles(circles, filename, config, w, h, offset, resolution, font, subfont):
    packPadding = 1.0 * config['packPadding'] / w
    w, h = (w*resolution, h*resolution)
    bgColor = config['bgColor']
    baseIm = Image.new(mode="RGBA", size=(w, h), color=bgColor)
    draw = ImageDraw.Draw(baseIm)
    x0, y0, windowWidth = offset
    x1 = x0 + windowWidth
    y1 = y0 + windowWidth

    # Draw circles
    for i, c in enumerate(circles):
        cdata = c.ex
        cx = cdata['cx']
        cy = cdata['cy']
        cr = cdata['cr']
        isHere = 'isHere' in cdata
        isPlaceholder = 'isPlaceholder' in cdata
        if isPlaceholder:
            circles[i].ex['isVisible'] = False
            continue
        text = cdata['id']
        level = cdata['level']
        colorIndex = wrapNumber(level - 1, (0, len(config['colorPalette'])-1))
        fillColor = config['colorPalette'][colorIndex]
        # normalize the circle data
        cx = norm(cx, (-1, 1))
        cy = norm(cy, (1, -1))
        circles[i].ex['nxy'] = (cx, cy)
        # cr = cr * 0.5
        if level > 1:
            cr = max(cr - packPadding, 0.0000001)
        # check bounds
        cx0 = cx - cr
        cx1 = cx + cr
        cy0 = cy - cr
        cy1 = cy + cr
        if not (isBetween(cx0, (x0, x1)) and isBetween(cy0, (y0, y1)) or isBetween(cx0, (x0, x1)) and isBetween(cy1, (y0, y1)) or isBetween(cx1, (x0, x1)) and isBetween(cy0, (y0, y1)) or isBetween(cx1, (x0, x1)) and isBetween(cy1, (y0, y1))):
            circles[i].ex['isVisible'] = False
            continue
        circles[i].ex['isVisible'] = True

        # convert to true x, y
        cx0 = norm(cx0, (x0, x1)) * w
        cx1 = norm(cx1, (x0, x1)) * w
        cy0 = norm(cy0, (y0, y1)) * h
        cy1 = norm(cy1, (y0, y1)) * h

        # draw shadow
        shadowIm = Image.new(mode="RGBA", size=(w, h), color=(0,0,0,0))
        shadowDraw = ImageDraw.Draw(shadowIm)
        shadowWidth = config["shadowWidth"]
        shadowBlurRadius = config["shadowBlurRadius"]
        shadowOpacity = roundInt(config["shadowOpacity"] * 255)
        shadowDraw.ellipse([cx0, cy0, cx1+shadowWidth, cy1+shadowWidth], fill=(0,0,0,shadowOpacity))
        shadowIm = shadowIm.filter(ImageFilter.GaussianBlur(shadowBlurRadius))
        baseIm.alpha_composite(shadowIm, (0, 0))

        # draw circle with image
        if 'image' in cdata:
            loadedImage = cdata['image'].copy()
            imw = roundInt(abs(cx1-cx0))
            imh = roundInt(abs(cy1-cy0))
            if imw <= 0 or imh <= 0:
                continue
            resizedImage = loadedImage.resize((imw, imh), resample=Image.LANCZOS)
            mask = Image.new(mode="L", size=(imw, imh), color=0)
            maskDraw = ImageDraw.Draw(mask)
            maskDraw.ellipse([0, 0, imw, imh], fill=255)
            compositeImage = alphaMask(resizedImage, mask)
            baseIm.alpha_composite(compositeImage, (roundInt(cx0), roundInt(cy0)))

        # draw circle with no image
        else:
            draw.ellipse([cx0, cy0, cx1, cy1], fill=fillColor)

        # draw outline around here
        if isHere:
            draw.ellipse([cx0, cy0, cx1, cy1], fill=None, outline=tuple(cdata['labelColor'] + [255]), width=4)


        # pprint([text, cx0, cy0, cx1, cy1, fillColor])

    # Draw labels
    for c in circles:
        cdata = c.ex
        cx = cdata['cx']
        cy = cdata['cy']
        if cdata['labelOpacity'] <= 0 or not cdata['isVisible']:
            continue
        isHere = 'isHere' in cdata
        labelColor = cdata['labelColor']
        labelColor = tuple(labelColor + [cdata['labelOpacity']])
        cx, cy = cdata['nxy']
        labelLines = cdata['label']
        labelWidth = cdata['labelWidth']
        labelHeight = cdata['labelHeight']
        cx = norm(cx, (x0, x1)) * w
        cy = norm(cy, (y0, y1)) * h
        ly = cy - labelHeight * 0.5
        if isHere:
            ly = cy + labelHeight * 0.5
        for i, line in enumerate(labelLines):
            lw, lh = line['size']
            lx = cx - labelWidth * 0.5 + (labelWidth - lw) * 0.5
            tfont = subfont if line['isLastLine'] else font
            draw.text((lx, ly), line['text'], font=tfont, fill=labelColor)
            ly += lh + cdata['labelSpacing']

    if resolution > 1:
        baseIm = baseIm.resize((roundInt(w/resolution), roundInt(h/resolution)), resample=Image.LANCZOS)

    makeDirectories(filename)
    baseIm.save(filename)

# load font
font = ImageFont.truetype(font=config["font"], size=roundInt(config["fontSize"]*RESOLUTION))
subfont = ImageFont.truetype(font=config["subheadingFont"], size=roundInt(config["subheadingFontSize"]*RESOLUTION))
lineSpacing = config["lineSpacing"] * RESOLUTION
imageCache = {}

for i, c in enumerate(circles):
    cx, cy, cr, cdata = (c.x, c.y, c.r, c.ex)
    isHere = 'isHere' in cdata
    isPlaceholder = 'isPlaceholder' in cdata

    # manually adjust position of here, otherwise it's more or less random
    if isHere:
        hereDx = 0.75 if 'dx' not in cdata else cdata['dx']
        hereDy = -0.75 if 'dy' not in cdata else cdata['dy']
        parent = circles[cdata['parentIndex']]
        px, py, pr = (parent.ex['cx'], parent.ex['cy'], parent.ex['cr'])
        cx = px + hereDx * pr
        cy = py + hereDy * pr

    circles[i].ex['cx'] = cx
    circles[i].ex['cy'] = cy
    circles[i].ex['cr'] = cr * 0.5

    # add labels
    collectionName = cdata['id']
    unit = cdata['unit'] if 'unit' in cdata else 'objects'
    countFormatted = formatNumber(cdata['datum'])
    lines = []
    lines.append(collectionName)
    lines.append(f'{countFormatted} {unit}')
    if isHere:
        lines = ['You are here']
    lineCount = len(lines)
    for j, line in enumerate(lines):
        label = {}
        label['text'] = line
        label['isLastLine'] = (j == lineCount-1 and not isHere)
        lw, lh = font.getsize(line)
        if label['isLastLine']:
            lw, lh = subfont.getsize(line)
        label['size'] = (lw, lh)
        lines[j] = label
    circles[i].ex['label'] = lines
    circles[i].ex['labelWidth'] = max(l['size'][0] for l in lines)
    circles[i].ex['labelHeight'] = sum(l['size'][1] for l in lines) + (lineCount-1) * lineSpacing
    opacity = 255 if cdata['level'] == 2 else 0
    circles[i].ex['labelOpacity'] = opacity
    if isHere:
        circles[i].ex['labelColor'] = list(ImageColor.getrgb(config['hereColor']))
        circles[i].ex['labelOpacity'] = 255
    else:
        circles[i].ex['labelColor'] = list(ImageColor.getrgb(config['labelColor']))
    circles[i].ex['labelSpacing'] = lineSpacing

    # load images
    if 'image' in cdata:
        loadedImage = None
        if cdata['image'] in imageCache:
            loadedImage = imageCache[cdata['image']]
        else:
            loadedImage = Image.open(cdata['image'])
            imageCache[cdata['image']] = loadedImage
        circles[i].ex['image'] = loadedImage
drawCircles(circles, "output/test.png", config, a.WIDTH, a.HEIGHT, (0, 0, 1.0), RESOLUTION, font, subfont)
