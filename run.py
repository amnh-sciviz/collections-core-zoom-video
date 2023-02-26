# -*- coding: utf-8 -*-

import argparse
import circlify as circ
import os
from PIL import Image, ImageColor, ImageDraw, ImageFilter, ImageFont
from pprint import pprint
import random
import shutil
import sys

from lib import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-config', dest="CONFIG_FILE", default="config.json", help="Input config .json file")
parser.add_argument('-array', dest="HERE_KEY", default="trilobites", help="Which media array this video is embedded in; it should map to a key in 'mediaArrays' in config file")
parser.add_argument('-width', dest="WIDTH", default=1080, type=int, help="Width of video")
parser.add_argument('-height', dest="HEIGHT", default=1080, type=int, help="Height of video")
parser.add_argument('-fps', dest="FPS", default=30, type=int, help="Frames per second of video")
parser.add_argument('-out', dest="OUTPUT_FILE", default="", help="Name of the output file; leave blank and it will be output/{HERE_KEY}.mp4")
parser.add_argument('-debug', dest="DEBUG", action="store_true", help="Just output an image of the data")
# parser.add_argument('-nonumbers', dest="NO_NUMBERS", action="store_true", help="Omit number labels?")
# parser.add_argument('-equal', dest="EQUAL_SIZE", action="store_true", help="All sibling circles equal size?")
a = parser.parse_args()
# Parse arguments

# Allow large images
Image.MAX_IMAGE_PIXELS = None

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

# add datums where they don't exist
flattenedData = sorted(flattenedData, key=lambda d: -d['level'])
def trueDatum(dd):
    # if 'displayNumber' in dd and isNumber(dd['displayNumber']):
    #     return dd['displayNumber']
    return dd['datum']
for i, d in enumerate(flattenedData):
    if 'datum' not in d:
        flattenedData[i]['datum'] = sum([trueDatum(dd) for dd in flattenedData if 'parent' in dd and dd['parent']==d['id'] and 'datum' in dd])

# add here
if a.HERE_KEY not in config['mediaArrays']:
    print(f'Could not find {a.HERE_KEY} in mediaArrays')
    sys.exit()
here = config['mediaArrays'][a.HERE_KEY]
here['isHere'] = True
here['neverRendered'] = False
hereImage = Image.open(config['hereImage'])
hereW, hereH = hereImage.size
hereImageRatio = hereW / hereH
hereImageWidth = roundInt(a.WIDTH * RESOLUTION * 0.075)
hereImageHeight = roundInt(hereImageWidth / hereImageRatio)
hereImage = hereImage.resize((hereImageWidth, hereImageHeight), resample=Image.LANCZOS)
hereLevel = None
maxCircleWidth = config['maxCircleWidth']
if 'maxCircleWidth' in here:
    maxCircleWidth = here['maxCircleWidth']
# remove existing children of here parent
flattenedData = [node for node in flattenedData if not ('parent' in node and node['parent'] == here['parent'])]
for i, d in enumerate(flattenedData):
    if d['id'] == here['parent']:
        hereLevel = d['level'] + 1
        here['level'] = hereLevel
        if 'datum' not in here:
            here['datum'] = roundInt(d['datum'] * 0.04)
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
                'level': hereLevel,
                'isPlaceholder': True,
                'parent': d['id'],
                'datum': value
            }
            children.append(placeholder)
        flattenedData[i]['children'] = children
        flattenedData[i]['hereParent'] = True
        break
# PACK_PADDING = 4 if hereLevel <= 4 else 2
PACK_PADDING = 0

# add color palette if they don't exist
flattenedData = sorted(flattenedData, key=lambda d: d['level'])
minLevel = flattenedData[0]['level']
maxLevel = flattenedData[-1]['level']
for i, d in enumerate(flattenedData):
    if 'colorPalette' not in d and 'parent' in d:
        for j, dd in enumerate(flattenedData):
            if dd['id'] == d['parent']:
                flattenedData[i]['colorPalette'] = dd['colorPalette']
                break

# adjust data if all are equal size
# if a.EQUAL_SIZE:
#     flattenedData = sorted(flattenedData, key=lambda d: d['level'])
#     for i, d in enumerate(flattenedData):
#         children = [dd for dd in flattenedData if 'parent' in dd and dd['parent'] == d['id']]
#         count = len(children)
#         if count <= 0:
#             continue
#         total = d['datum']
#         per = 1.0 * total / count
#         for j, dd in enumerate(flattenedData):
#             if 'parent' in dd and dd['parent'] == d['id']:
#                 flattenedData[j]['datum'] = per

# add index
for i, d in enumerate(flattenedData):
    flattenedData[i]['index'] = i

dataLookup = createLookup(flattenedData, 'id')
# flattenedData = sorted(flattenedData, key=lambda d: d['level'])
# pprint(flattenedData)

# mark circles that never get rendered;
# first mark all level 2+ as never rendered
startNode = None
for i, d in enumerate(flattenedData):
    if d['level'] > 2:
        flattenedData[i]['neverRendered'] = True
    else:
        flattenedData[i]['neverRendered'] = False
    if 'hereParent' in d:
        startNode = d
# now we only render the nodes related to here node
node = startNode
while node['level'] >= 2:
    flattenedData[node['index']]['neverRendered'] = False
    for i, d in enumerate(flattenedData):
        if 'parent' in d and d['parent'] == node['id']:
            flattenedData[i]['neverRendered'] = False
    node = dataLookup[node['parent']]

data = unflattenData(flattenedData)
# pprint(data)

circles = circ.circlify(data)
circles = sorted(circles, key=lambda c: c.level)
# add positions and indices for easier references later
for i, c in enumerate(circles):
    cx, cy, cr = (c.x, c.y, c.r)
    circles[i].ex['cx'] = cx
    circles[i].ex['cy'] = cy
    circles[i].ex['cr'] = cr * 0.5
    circles[i].ex['index'] = i
circleLookup = dict([(c.ex['id'], c) for c in circles])
for i, c in enumerate(circles):
    if 'parent' in c.ex and c.ex['parent'] in circleLookup:
        circles[i].ex['parentIndex'] = circleLookup[c.ex['parent']].ex['index']
    else:
        circles[i].ex['parentIndex'] = -1

# circ.bubbles(circles)

def getCropCoords(x, y):
    pasteX = roundInt(x)
    pasteY = roundInt(y)
    cropX = 0
    cropY = 0
    if pasteX < 0:
        cropX = -pasteX
        pasteX = 0
    if pasteY < 0:
        cropY = -pasteY
        pasteY = 0
    return pasteX, pasteY, cropX, cropY

def drawCircles(circles, filename, config, w, h, offset, resolution, font, subfont, titleFont, fromNode, toNode, theta):
    packPadding = 1.0 * PACK_PADDING / w
    w, h = (roundInt(w*resolution), roundInt(h*resolution))
    bgColor = config['bgColor']
    baseIm = Image.new(mode="RGBA", size=(w, h), color=bgColor)
    txtIm = Image.new(mode="RGBA", size=(w, h), color=(255, 255, 255, 0))
    draw = ImageDraw.Draw(baseIm)
    drawTxt = ImageDraw.Draw(txtIm)
    x0, y0, windowWidth = offset
    # print(offset)
    x1 = x0 + windowWidth
    y1 = y0 + windowWidth
    fromLevel = fromNode.ex['level']
    toLevel = toNode.ex['level']

    # Draw circles
    for i, c in enumerate(circles):
        cdata = c.ex
        cx = cdata['cx']
        cy = cdata['cy']
        cr = cdata['cr']
        isHere = 'isHere' in cdata
        if isHere:
            fromPositionIndex = fromLevel - 1
            toPositionIndex = toLevel - 1
            fromCx, fromCy = cdata['positions'][fromPositionIndex]
            toCx, toCy = cdata['positions'][toPositionIndex]
            cx = lerp((fromCx, toCx), theta)
            cy = lerp((fromCy, toCy), theta)
        isPlaceholder = 'isPlaceholder' in cdata
        isNeverRendered = 'neverRendered' in cdata and cdata['neverRendered']
        circleOpacity = cdata['circleOpacity']
        if isPlaceholder or circleOpacity <= 0 or isNeverRendered:
            circles[i].ex['isVisible'] = False
            continue
        text = cdata['id'].replace('_', '')
        level = cdata['level']
        # # don't try to draw anything greater than grandparent
        # deltaLevel = min(fromLevel - level, toLevel - level)
        # if deltaLevel > 1:
        #     circles[i].ex['isVisible'] = False
        #     continue
        fillColor = cdata['fillColor']
        # normalize the circle data
        cx = norm(cx, (-1, 1))
        cy = norm(cy, (1, -1))

        # cr = cr * 0.5
        if level > 1 and cr > packPadding:
            cr = cr - packPadding

        circle = {'x': cx, 'y': cy, 'r': cr}
        rect = {'x': (x1 - x0) * 0.5 + x0, 'y': (y1 - y0) * 0.5 + y0, 'w': (x1 - x0), 'h': (y1 - y0)}
        if not circleRectIntersects(circle, rect):
            circles[i].ex['isVisible'] = False
            continue
        circles[i].ex['isVisible'] = True
        circles[i].ex['nxy'] = (cx, cy)

        # get bounds
        cx0 = cx - cr
        cx1 = cx + cr
        cy0 = cy - cr
        cy1 = cy + cr

        # check inner bounds to see if it's full bleed
        innerCr = cr / (math.sqrt(2))
        innerCx0 = cx - innerCr
        innerCx1 = cx + innerCr
        innerCy0 = cy - innerCr
        innerCy1 = cy + innerCr

        # convert to true x, y
        cx0 = norm(cx0, (x0, x1)) * w
        cx1 = norm(cx1, (x0, x1)) * w
        cy0 = norm(cy0, (y0, y1)) * h
        cy1 = norm(cy1, (y0, y1)) * h
        circles[i].ex['trueRadius'] = (cx1 - cx0) * 0.5

        innerCx0 = norm(innerCx0, (x0, x1)) * w
        innerCx1 = norm(innerCx1, (x0, x1)) * w
        innerCy0 = norm(innerCy0, (y0, y1)) * h
        innerCy1 = norm(innerCy1, (y0, y1)) * h
        isFullBleed = innerCx0 < 0 and innerCy0 < 0 and innerCx1 > w and innerCy1 > h

        if isHere:
            circles[i].ex['bounds'] = (cx0, cy0, cx1, cy1)
            if 'image' in cdata:
                # multiplier = 1.333
                multiplier = 1.0
                imw = roundInt(abs(cx1-cx0))
                imh = roundInt(abs(cy1-cy0))
                imw1 = roundInt(imw * multiplier)
                imh1 = roundInt(imh * multiplier)
                deltaX = (imw1 - imw) * 0.5
                deltaY = (imh1 - imh) * 0.5
                cx0 = cx0 - deltaX
                cy0 = cy0 - deltaY
                cx1 = cx1 + deltaX
                cy1 = cy1 + deltaY
                # draw circle
                draw.ellipse([cx0, cy0, cx1, cy1], fill=config['hereColor'])
            # draw graphics later
            continue

        imw = roundInt(abs(cx1-cx0))
        imh = roundInt(abs(cy1-cy0))
        tooLarge = imw >= maxCircleWidth

        # draw shadow
        if not isFullBleed and not tooLarge:
            shadowIm = Image.new(mode="RGBA", size=(w, h), color=(0,0,0,0))
            shadowDraw = ImageDraw.Draw(shadowIm)
            shadowWidth = config["shadowWidth"]
            shadowBlurRadius = config["shadowBlurRadius"]
            shadowOpacity = roundInt(config["shadowOpacity"] * circleOpacity * 255)
            shadowDraw.ellipse([cx0, cy0, cx1+shadowWidth, cy1+shadowWidth], fill=(0,0,0,shadowOpacity))
            shadowIm = shadowIm.filter(ImageFilter.GaussianBlur(shadowBlurRadius))
            baseIm.alpha_composite(shadowIm, (0, 0))

        # draw circle with image
        if 'image' in cdata:
            imageOpacity = cdata['imageOpacity']
            imageBlend = config['imageBlend']
            if 'imageBlend' in cdata:
                imageBlend = cdata['imageBlend']
            imageBlend = imageBlend * imageOpacity
            backgroundImage = cdata['bgImage'].copy()
            loadedImage = cdata['image'].copy()
            if imw <= 0 or imh <= 0:
                continue
            blendedImage = backgroundImage
            if imageBlend > 0:
                blendedImage = Image.blend(backgroundImage, loadedImage, imageBlend)
                blendedImage = blendedImage.convert("RGBA")
            if not isFullBleed and tooLarge:
                draw.ellipse([cx0, cy0, cx1, cy1], fill=fillColor)
                
            elif isFullBleed or tooLarge:
                imw0, imh0 = blendedImage.size
                scale = imw / imw0
                pasteX, pasteY, cropX, cropY = getCropCoords(cx0, cy0)
                nx = 1.0 * cropX / imw
                ny = 1.0 * cropY / imh
                cropX = max(roundInt(nx * imw0), 0)
                cropY = max(roundInt(ny * imh0), 0)
                cropW = w / scale
                cropH = h / scale
                cropX1 = roundInt(cropX + cropW)
                cropY1 = roundInt(cropY + cropH)
                croppedImage = blendedImage.crop((cropX, cropY, cropX1, cropY1))
                resizedImage = croppedImage.resize((w, h), resample=Image.LANCZOS)
                baseIm.alpha_composite(resizedImage, (0, 0))
                
            else:
                resizedImage = blendedImage.resize((imw, imh), resample=Image.LANCZOS)
                mask = Image.new(mode="L", size=(imw, imh), color=0)
                maskDraw = ImageDraw.Draw(mask)
                maskDraw.ellipse([0, 0, imw, imh], fill=255)
                compositeImage = alphaMask(resizedImage, mask)
                # https://github.com/python-pillow/Pillow/issues/4687#issuecomment-643567573
                # change the transparency without affecting transparent background
                tempImage = compositeImage.copy()
                tempImage.putalpha(roundInt(circleOpacity * 255))
                compositeImage.paste(tempImage, compositeImage)
                pasteX, pasteY, cropX, cropY = getCropCoords(cx0, cy0)
                baseIm.alpha_composite(compositeImage, (pasteX, pasteY), (cropX, cropY))

        # draw circle with no image
        else:
            if isFullBleed:
                draw.rectangle([0, 0, w, h], fill=fillColor)

            else:
                draw.ellipse([cx0, cy0, cx1, cy1], fill=fillColor)


        # pprint([text, cx0, cy0, cx1, cy1, fillColor])

    # Draw labels
    for c in circles:
        cdata = c.ex
        if not cdata['isVisible']:
            continue

        isHere = 'isHere' in cdata
        isHereParent = 'hereParent' in cdata
        isLabelHeader = cdata['isLabelHeader']
        if isHere and not isLabelHeader:
            continue
        isUpperCase = isLabelHeader and not isHereParent
        labelWidth = cdata['labelWidth']
        labelHeight = cdata['labelHeight']
        labelColor = cdata['labelColor']
        if isUpperCase:
            labelWidth = cdata['labelWidthUpper']
            labelHeight = cdata['labelHeightUpper']
        cx, cy = cdata['nxy']
        cx = norm(cx, (x0, x1)) * w
        cy = norm(cy, (y0, y1)) * h
        labelLines = cdata['label']

        labelColor = tuple(labelColor + [cdata['labelOpacity']])

        ly = cy - labelHeight * 0.5
        if isUpperCase:
            ly = cy - cdata['trueRadius'] * 0.95 + cdata['labelSpacing']
        if isHere:
            ly = cy - cdata['trueRadius'] * 0.9 + cdata['labelSpacing']
            labelColor = tuple([0, 0, 0] + [cdata['labelOpacity']])

        deltaX = 0
        deltaY = 0
        padEdge = 20
        for i, line in enumerate(labelLines):
            lw, lh = line['size']
            if isUpperCase and not line['isSubtitle']:
                lw, lh = line['sizeUpper']
            lx = cx - labelWidth * 0.5 + (labelWidth - lw) * 0.5
            tfont = subfont if line['isSubtitle'] else font
            if line['isTitle']:
                tfont = font if line['isSubtitle'] else titleFont
            if i == 0 and ly < padEdge:
                deltaY = padEdge - ly
            if lx < padEdge:
                deltaX = padEdge - lx
            elif (lx + lw) > (w - padEdge):
                deltaX = (w - padEdge) - (lx + lw)
            lineText = line['text']
            if isUpperCase and not line['isSubtitle']:
                lineText = line['textUpper']
            drawTxt.text((lx + deltaX, ly + deltaY), lineText, font=tfont, fill=labelColor)
            ly += lh + cdata['labelSpacing']

    baseIm = Image.alpha_composite(baseIm, txtIm)

    # draw here on top
    for c in circles:
        cdata = c.ex
        isHere = 'isHere' in cdata
        if not isHere:
            continue
        cx0, cy0, cx1, cy1 = cdata['bounds']
        deltaX = 0
        deltaY = 0
        if 'image' in cdata:
            imageResizeRatio = 0.7
            # paste array image
            imw0, imh0 = cdata['image'].size
            imRatio = imw0 / imh0
            loadedImage = cdata['image'].copy()
            imw = abs(cx1-cx0)
            imh = abs(cy1-cy0)
            resizedImw = imw * imageResizeRatio
            resizedImh = imh * imageResizeRatio
            resizedCx0 = roundInt(cx0 + (imw - resizedImw) * 0.5)
            resizedCxy = roundInt(cy0 + (imh - resizedImh) * 0.5)
            if imRatio >= 1: # landscape image
                resizedImh = roundInt(resizedImw / imRatio)
                resizedImw = roundInt(resizedImw)
                deltaY = (resizedImw - resizedImh) * 0.5
            else: # portrait image
                resizedImw = roundInt(resizedImh / imRatio)
                resizedImh = roundInt(resizedImh)
                deltaX = (resizedImh - resizedImw) * 0.5
            if resizedImw <= 0 or resizedImh <= 0:
                continue
            resizedImage = loadedImage.resize((resizedImw, resizedImh), resample=Image.LANCZOS)
            pasteX, pasteY, cropX, cropY = getCropCoords(resizedCx0+deltaX, resizedCxy+deltaY)
            baseIm.alpha_composite(resizedImage, (pasteX, pasteY), (cropX, cropY))
        # paste here label
        imw = roundInt(abs(cx1-cx0))
        imh = roundInt(abs(cy1-cy0))
        deltaX2 = (imw - hereImageWidth) * 0.5
        pasteX, pasteY, cropX, cropY = getCropCoords(cx0+deltaX2, cy0+deltaY-hereImageHeight+hereImageHeight*0.05)
        baseIm.alpha_composite(hereImage, (pasteX, pasteY), (cropX, cropY))
        break

    if resolution > 1:
        baseIm = baseIm.resize((roundInt(w/resolution), roundInt(h/resolution)), resample=Image.LANCZOS)

    makeDirectories(filename)
    baseIm.save(filename)

def tweenNodes(circles, filename, fromNode, toNode, t, config, w, h, resolution, font, subfont, titleFont):

    fromId = fromNode.ex['id']
    toId = toNode.ex['id']
    fromLevel = fromNode.ex['level']
    toLevel = toNode.ex['level']

    cr0 = fromNode.ex['cr']
    cw0 = cr0 * 2
    cx0 = norm(fromNode.ex['cx'], (-1, 1)) - cr0
    cy0 = norm(fromNode.ex['cy'], (1, -1)) - cr0

    cr1 = toNode.ex['cr']
    cw1 = cr1 * 2
    cx1 = norm(toNode.ex['cx'], (-1, 1)) - cr1
    cy1 = norm(toNode.ex['cy'], (1, -1)) - cr1

    t = ease(t)
    offsetX = lerp((cx0, cx1), t)
    offsetY = lerp((cy0, cy1), t)
    offsetW = lerp((cw0, cw1), t)

    threshold = 0.667
    zoomingIn = (toLevel > fromLevel)
    zoomingOut = (not zoomingIn)
    for i, circle in enumerate(circles):
        cdata = circle.ex
        level = cdata['level']
        hasParent = 'parent' in cdata
        isHere = 'isHere' in cdata
        isHereParent = 'hereParent' in cdata
        isLabelHeader = False
        circleOpacity = 1
        imageOpacity = 0
        labelOpacity = 0
        if t < threshold and hasParent and cdata['parent'] == fromId:
            theta = ease(1.0 - t / threshold)
            labelOpacity = roundInt(theta * 255.0)
            imageOpacity = theta

        elif t > (1.0 - threshold) and hasParent and cdata['parent'] == toId:
            theta = ease(norm(t, (1.0 - threshold, 1.0)))
            labelOpacity = roundInt(theta * 255.0)
            imageOpacity = theta

        elif t < threshold and cdata['id'] == fromId:
            labelOpacity = roundInt(ease(1.0 - t / threshold) * 255.0)
            isLabelHeader = True

        elif t > (1.0 - threshold) and cdata['id'] == toId:
            labelOpacity = roundInt(ease(norm(t, (1.0 - threshold, 1.0))) * 255.0)
            isLabelHeader = True

        # don't fade in/out here parent since position does not move
        if (cdata['id'] == fromId and isHereParent and zoomingOut) or (cdata['id'] == toId and isHereParent and zoomingIn):
            labelOpacity = 255

        maxLevel = max(fromLevel, toLevel)
        deltaLevel = level - maxLevel
        if deltaLevel == 1:
            circleOpacity = imageOpacity
        elif deltaLevel > 1:
            circleOpacity = 0.0
        if isHere:
            circleOpacity = 1.0

        if isHereParent and circleOpacity > 0:
            imageOpacity = 1.0

        # set texture opacity to within a range
        imageOpacity = lerp((config['imageBlendBackground'], 1.0), imageOpacity)

        circles[i].ex['circleOpacity'] = circleOpacity
        circles[i].ex['imageOpacity'] = imageOpacity
        circles[i].ex['labelOpacity'] = labelOpacity
        circles[i].ex['isLabelHeader'] = isLabelHeader

    drawCircles(circles, filename, config, w, h, (offsetX, offsetY, offsetW), resolution, font, subfont, titleFont, fromNode, toNode, t)

# load font
titleFont = ImageFont.truetype(font=config["titleFont"], size=roundInt(config["titleFontSize"]*RESOLUTION))
font = ImageFont.truetype(font=config["font"], size=roundInt(config["fontSize"]*RESOLUTION))
subfont = ImageFont.truetype(font=config["subheadingFont"], size=roundInt(config["subheadingFontSize"]*RESOLUTION))
lineSpacing = config["lineSpacing"] * RESOLUTION
imageCache = {}

# check to see if circles need to be rotated
for i, c in enumerate(circles):
    cdata = c.ex
    originX, originY = (cdata['cx'], cdata['cy'])
    if 'rotate' not in cdata:
        continue
    degrees = cdata['rotate']
    children = flattenTree(cdata['children'][:], modify=False)
    
    for node in children:
        id = node['id']
        circle = circleLookup[id]
        cx, cy = (circle.ex['cx'], circle.ex['cy'])
        cindex = circle.ex['index']
        rotatedX, rotatedY = rotate((originX, originY), (cx, cy), degrees)
        circles[cindex].ex['cx'] = rotatedX
        circles[cindex].ex['cy'] = rotatedY

for i, c in enumerate(circles):
    cdata = c.ex
    cx, cy, cr = (cdata['cx'], cdata['cy'], cdata['cr'])
    isHere = 'isHere' in cdata
    isPlaceholder = 'isPlaceholder' in cdata

    # add labels
    collectionName = cdata['id'].replace('_', '')
    prefix = cdata['prefix'] if 'prefix' in cdata else config['defaultPrefix']
    suffix = cdata['suffix'] if 'suffix' in cdata else config['defaultSuffix']
    unit = cdata['unit'] if 'unit' in cdata else config['defaultUnit']
    roundedDatum = smartRound(cdata['datum'])
    roundedDatum = roundInt(roundedDatum)
    countFormatted = formatNumber(roundedDatum)
    lines = []
    lines += collectionName.split('\n')
    subtitleLines = 0
    if cdata['level'] <= 2:
        if 'displayNumber' in cdata and isNumber(cdata['displayNumber']):
            countFormatted = formatNumber(cdata['displayNumber'])
            lines.append(f'{prefix}{countFormatted}{suffix}')
            lines.append(unit)
            subtitleLines = 2
        elif 'displayNumber' in cdata:
            lines += cdata['displayNumber'].split('\n')
            subtitleLines = len(cdata['displayNumber'].split('\n'))
        else:
            lines.append(f'{prefix}{countFormatted}{suffix}')
            lines.append(unit)
            subtitleLines = 2
    lineCount = len(lines)
    hfont = titleFont if cdata['level'] <= 0 else font
    h2font = font if cdata['level'] <= 0 else subfont
    for j, line in enumerate(lines):
        label = {}
        label['text'] = line
        label['textUpper'] = line.upper()
        label['isSubtitle'] = (subtitleLines > 0 and j > 0 and j >= lineCount-subtitleLines)
        label['isTitle'] = cdata['level'] <= 0
        if label['isSubtitle']:
            label['size'] = getLineDimensions(h2font, line)
        else:
            label['size'] = getLineDimensions(hfont, line)
        label['sizeUpper'] = getLineDimensions(hfont, line.upper())
        lines[j] = label
    circles[i].ex['label'] = lines
    circles[i].ex['labelWidth'] = max(l['size'][0] for l in lines)
    circles[i].ex['labelHeight'] = sum(l['size'][1] for l in lines) + (lineCount-1) * lineSpacing
    circles[i].ex['labelWidthUpper'] = max(l['sizeUpper'][0] for l in lines)
    circles[i].ex['labelHeightUpper'] = sum(l['sizeUpper'][1] for l in lines) + (lineCount-1) * lineSpacing
    circles[i].ex['labelOpacity'] = 0
    circles[i].ex['labelColor'] = list(ImageColor.getrgb(config['labelColor']))
    circles[i].ex['labelSpacing'] = lineSpacing

    fillColor = "#000000"
    if 'colorPalette' in cdata:   
        colorIndex = wrapNumber(cdata['level'] - 1, (0, len(cdata['colorPalette'])-1))
        fillColor = cdata['colorPalette'][colorIndex]
    circles[i].ex['fillColor'] = fillColor

    # load images
    if 'image' in cdata:
        loadedImage = None
        if cdata['image'] in imageCache:
            loadedImage = imageCache[cdata['image']]
        else:
            loadedImage = Image.open(cdata['image'])
            # ensure the image is a square
            imw, imh = loadedImage.size
            if imw != imh:
                newW = max(imw, imh)
                transparentImg = Image.new(mode="RGBA", size=(newW, newW), color=(0, 0, 0, 0))
                pasteX = 0
                pasteY = 0
                if imw > imh:
                    pasteY = roundInt((newW - imh) * 0.5)
                else:
                    pasteX = roundInt((newW - imw) * 0.5)
                transparentImg.paste(loadedImage, (pasteX, pasteY))
                loadedImage = transparentImg
            imageCache[cdata['image']] = loadedImage
        circles[i].ex['bgImage'] = Image.new(loadedImage.mode, loadedImage.size, color=fillColor)
        circles[i].ex['image'] = loadedImage

for i, c in enumerate(circles):
    cdata = c.ex
    cx, cy, cr = (cdata['cx'], cdata['cy'], cdata['cr'])
    isHere = 'isHere' in cdata
     # manually adjust position of here, otherwise it's more or less random
    if isHere:
        hereDx = config['hereDx'] if 'dx' not in cdata else cdata['dx']
        hereDy = config['hereDy'] if 'dy' not in cdata else cdata['dy']
        parent = circles[cdata['parentIndex']]
        # create a list of fixed positions at each level
        # this mitigates here label from overlapping with other labels
        herePositions = []
        while parent is not None and parent.ex['level'] > 1:
            px, py, pr = (parent.ex['cx'], parent.ex['cy'], parent.ex['cr'])
            hereX = px + hereDx * pr
            hereY = py + hereDy * pr
            herePositions = [(hereX, hereY)] + herePositions
            if 'parentIndex' in parent.ex:
                parent = circles[parent.ex['parentIndex']]
            else:
                parent = None
        herePosition = herePositions[-1]
        circles[i].ex['positions'] = herePositions + [herePosition] + [herePosition]
        cx, cy = herePosition
        circles[i].ex['cx'] = cx
        circles[i].ex['cy'] = cy

        # print(cdata['level'])
        # pprint(circles[i].ex['positions'])
        # sys.exit()
        break

# generate a path that zooms out from HERE then zooms back into HERE
path = []
hereNode = circleLookup[here['id']]
node = circles[hereNode.ex['index']]
# node = circles[node.ex['parentIndex']] # uncomment this to not zoom all the way in
while True:
    path.append(node)
    parentIndex = node.ex['parentIndex']
    if parentIndex < 0:
        break
    node = circles[parentIndex]
# pathReversed = list(reversed(path[:-1]))
# path += pathReversed

# if a.DEBUG:
#     drawCircles(circles, "output/test.png", config, a.WIDTH, a.HEIGHT, (0, 0, 1.0), RESOLUTION, font, subfont, titleFont, 0)

outputFramePattern = f'output/frames/{a.HERE_KEY}/frame.%s.png'
if not a.DEBUG:
    makeDirectories(outputFramePattern)
    removeFiles(outputFramePattern % '*')

zoomDurationMin = config['zoomDurationMin']
zoomDurationMax = config['zoomDurationMax']
restDurationMin = config['restDurationMin']
restDurationMax = config['restDurationMax']
zoomFrames = msToFrame(zoomDurationMax, a.FPS)
restFrames = msToFrame(restDurationMax, a.FPS)
totalFrames = (len(path)-1) * (zoomFrames + restFrames) * 2
currentFrame = 1
frameFilenames = []
if not a.DEBUG:
    print(f'Rendering frames to {(outputFramePattern % "*")}...')
deltas = [(1.0 * path[i+1].ex['datum'] / path[i].ex['datum']) for i in range(len(path)-1)]
minDelta = min(deltas)
maxDelta = max(deltas)
for i in range(len(path)-1):
    fromNode = path[i]
    toNode = path[i+1]
    delta = 1.0 * path[i+1].ex['datum'] / path[i].ex['datum']
    print(f'Rendering frames from node {fromNode.ex["id"]} to {toNode.ex["id"]} ({i+1} of {len(path)})')
    if a.DEBUG:
        tweenNodes(circles, f'output/tween_test_{i}.png', fromNode, toNode, 0.0, config, a.WIDTH, a.HEIGHT, RESOLUTION, font, subfont, titleFont)
        if i >= (len(path)-2):
            tweenNodes(circles, f'output/tween_test_{i+1}.png', fromNode, toNode, 1.0, config, a.WIDTH, a.HEIGHT, RESOLUTION, font, subfont, titleFont)
    else:
        nFrom = norm(fromNode.ex['level'], (minLevel, maxLevel))
        restDurationFrom = lerp((restDurationMin, restDurationMax), 1.0 - nFrom)
        if 'isHere' in fromNode.ex:
            restDurationFrom = restDurationMax * 0.5
        restDurationFrom = roundInt(restDurationFrom * 0.5)
        restFramesFrom = msToFrame(restDurationFrom, a.FPS)
        nTo = norm(fromNode.ex['level'], (minLevel, maxLevel))
        restDurationTo = lerp((restDurationMin, restDurationMax), 1.0 - nTo)
        if 'isHere' in toNode.ex:
            restDurationTo = restDurationMax * 0.5
        restDurationTo = roundInt(restDurationTo * 0.5)
        restFramesTo = msToFrame(restDurationTo, a.FPS)
        nZoom = norm(delta, (minDelta, maxDelta))
        zoomDurationTo = roundInt(lerp((zoomDurationMin, zoomDurationMax), nZoom))
        zoomFramesTo = msToFrame(zoomDurationTo, a.FPS)
        totalPathFrames = restFramesFrom + restFramesTo + zoomFramesTo
        currentPathFrame = 1

        referenceFrame = None
        for i in range(restFramesFrom):
            frameFilename = outputFramePattern % zeroPad(currentFrame, totalFrames)
            if i == 0:
                tweenNodes(circles, frameFilename, fromNode, toNode, 0.0, config, a.WIDTH, a.HEIGHT, RESOLUTION, font, subfont, titleFont)
                referenceFrame = frameFilename
            else:
                shutil.copyfile(referenceFrame, frameFilename)
            printProgress(currentPathFrame, totalPathFrames)
            frameFilenames.append(frameFilename)
            currentPathFrame += 1
            currentFrame += 1

        for i in range(zoomFramesTo):
            frameFilename = outputFramePattern % zeroPad(currentFrame, totalFrames)
            t = 1.0 * i / (zoomFramesTo-1)
            tweenNodes(circles, frameFilename, fromNode, toNode, t, config, a.WIDTH, a.HEIGHT, RESOLUTION, font, subfont, titleFont)
            printProgress(currentPathFrame, totalPathFrames)
            referenceFrame = frameFilename
            frameFilenames.append(frameFilename)
            currentPathFrame += 1
            currentFrame += 1

        for i in range(restFramesTo):
            frameFilename = outputFramePattern % zeroPad(currentFrame, totalFrames)
            shutil.copyfile(referenceFrame, frameFilename)
            printProgress(currentPathFrame, totalPathFrames)
            frameFilenames.append(frameFilename)
            currentPathFrame += 1
            currentFrame += 1

print('Reversing frames...')
framesReversed = list(reversed(frameFilenames[:]))
for fn in framesReversed:
    frameFilename = outputFramePattern % zeroPad(currentFrame, totalFrames)
    shutil.copyfile(fn, frameFilename)
    currentFrame += 1

if not a.DEBUG:
    outfile = a.OUTPUT_FILE if a.OUTPUT_FILE != "" else f'output/{a.HERE_KEY}.mp4'
    padZeros = len(str(totalFrames))
    compileFrames(outputFramePattern, a.FPS, outfile, padZeros)

print('Rendered video')
print('Removing frames...')
removeFiles(outputFramePattern % '*')
print('Done.')
print('===============================')