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
parser.add_argument('-height', dest="HEIGHT", default=1080, type=float, help="Height of video")
parser.add_argument('-fps', dest="FPS", default=30, type=int, help="Frames per second of video")
parser.add_argument('-out', dest="OUTPUT_FILE", default="", help="Name of the output file; leave blank and it will be output/{HERE_KEY}.mp4")
parser.add_argument('-debug', dest="DEBUG", action="store_true", help="Just output an image of the data")
parser.add_argument('-nonumbers', dest="NO_NUMBERS", action="store_true", help="Omit number labels?")
parser.add_argument('-equal', dest="EQUAL_SIZE", action="store_true", help="All sibling circles equal size?")
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

# add color palette if they don't exist
flattenedData = sorted(flattenedData, key=lambda d: d['level'])
for i, d in enumerate(flattenedData):
    if 'colorPalette' not in d and 'parent' in d:
        for j, dd in enumerate(flattenedData):
            if dd['id'] == d['parent']:
                flattenedData[i]['colorPalette'] = dd['colorPalette']
                break

# adjust data if all are equal size
if a.EQUAL_SIZE:
    flattenedData = sorted(flattenedData, key=lambda d: d['level'])
    for i, d in enumerate(flattenedData):
        children = [dd for dd in flattenedData if 'parent' in dd and dd['parent'] == d['id']]
        count = len(children)
        if count <= 0:
            continue
        total = d['datum']
        per = 1.0 * total / count
        for j, dd in enumerate(flattenedData):
            if 'parent' in dd and dd['parent'] == d['id']:
                flattenedData[j]['datum'] = per

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
    else:
        circles[i].ex['parentIndex'] = -1

# circ.bubbles(circles)

def drawCircles(circles, filename, config, w, h, offset, resolution, font, subfont):
    packPadding = 1.0 * config['packPadding'] / w
    w, h = (roundInt(w*resolution), roundInt(h*resolution))
    bgColor = config['bgColor']
    baseIm = Image.new(mode="RGBA", size=(w, h), color=bgColor)
    txtIm = Image.new(mode="RGBA", size=(w, h), color=(255, 255, 255, 0))
    draw = ImageDraw.Draw(baseIm)
    drawTxt = ImageDraw.Draw(txtIm)
    x0, y0, windowWidth = offset
    # pprint(offset)
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
        circleOpacity = cdata['circleOpacity']
        if isPlaceholder or circleOpacity <= 0:
            circles[i].ex['isVisible'] = False
            continue
        text = cdata['id']
        level = cdata['level']
        fillColor = cdata['fillColor']
        # normalize the circle data
        cx = norm(cx, (-1, 1))
        cy = norm(cy, (1, -1))

        # cr = cr * 0.5
        if level > 1:
            cr = max(cr - packPadding, 0.0000001)

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

        # draw shadow
        if not isFullBleed:
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
            imageOpacity = cdata['imageOpacity']
            imageBlend = config['imageBlend']
            if 'imageBlend' in cdata:
                imageBlend = cdata['imageBlend']
            imageBlend = imageBlend * imageOpacity
            backgroundImage = cdata['bgImage'].copy()
            loadedImage = cdata['image'].copy()
            imw = roundInt(abs(cx1-cx0))
            imh = roundInt(abs(cy1-cy0))
            if imw <= 0 or imh <= 0:
                continue
            blendedImage = backgroundImage
            if imageBlend > 0:
                blendedImage = Image.blend(backgroundImage, loadedImage, imageBlend)
                blendedImage = blendedImage.convert("RGB")
            resizedImage = blendedImage.resize((imw, imh), resample=Image.Resampling.LANCZOS)
            mask = Image.new(mode="L", size=(imw, imh), color=0)
            maskDraw = ImageDraw.Draw(mask)
            maskDraw.ellipse([0, 0, imw, imh], fill=255)
            compositeImage = alphaMask(resizedImage, mask)
            if circleOpacity < 1:
                compositeImage.putalpha(roundInt(circleOpacity * 255))
            pasteX = roundInt(cx0)
            pasteY = roundInt(cy0)
            cropX = 0
            cropY = 0
            if pasteX < 0:
                cropX = -pasteX
                pasteX = 0
            if pasteY < 0:
                cropY = -pasteY
                pasteY = 0
            baseIm.alpha_composite(compositeImage, (pasteX, pasteY), (cropX, cropY))

        # draw circle with no image
        else:
            if isFullBleed:
                draw.rectangle([0, 0, w, h], fill=fillColor)

            else:
                draw.ellipse([cx0, cy0, cx1, cy1], fill=fillColor)

        # draw outline around here
        if isHere:
            draw.ellipse([cx0, cy0, cx1, cy1], fill=None, outline=config['hereColor'], width=4)


        # pprint([text, cx0, cy0, cx1, cy1, fillColor])

    # Draw labels
    for c in circles:
        cdata = c.ex
        if not cdata['isVisible']:
            continue

        isHere = 'isHere' in cdata
        labelWidth = cdata['labelWidth']
        labelHeight = cdata['labelHeight']
        labelColor = cdata['labelColor']
        isLabelHeader = cdata['isLabelHeader']
        cx, cy = cdata['nxy']
        cx = norm(cx, (x0, x1)) * w
        cy = norm(cy, (y0, y1)) * h
        labelLines = cdata['label']

        # if isHere:
        #     text = 'You are here'
        #     lw, lh = font.getsize(text)
        #     ly = cy + cdata['trueRadius'] + cdata['labelSpacing']
        #     lx = cx - labelWidth * 0.5 + (labelWidth - lw) * 0.5
        #     if lx < 0:
        #         lx = 0
        #     drawTxt.text((lx, ly), text, font=font, fill=config['hereColor'])
        #     continue

        if not isHere and cdata['labelOpacity'] <= 0:
            continue

        labelColor = tuple(labelColor + [cdata['labelOpacity']])
        if isHere:
            labelColor = config['hereColor']

        ly = cy - labelHeight * 0.5
        if isLabelHeader:
            ly = cy - cdata['trueRadius'] * 0.95 + cdata['labelSpacing']
        if isHere:
            ly = cy + cdata['trueRadius'] + cdata['labelSpacing']

        for i, line in enumerate(labelLines):
            lw, lh = line['size']
            lx = cx - labelWidth * 0.5 + (labelWidth - lw) * 0.5
            if lx < 0 and isHere:
                lx = 0
            tfont = subfont if line['isLastLine'] else font
            drawTxt.text((lx, ly), line['text'], font=tfont, fill=labelColor)
            ly += lh + cdata['labelSpacing']

    baseIm = Image.alpha_composite(baseIm, txtIm)

    if resolution > 1:
        baseIm = baseIm.resize((roundInt(w/resolution), roundInt(h/resolution)), resample=Image.Resampling.LANCZOS)

    makeDirectories(filename)
    baseIm.save(filename)

def tweenNodes(circles, filename, fromNode, toNode, t, config, w, h, resolution, font, subfont):

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

        maxLevel = max(fromLevel, toLevel)
        deltaLevel = level - maxLevel
        if deltaLevel == 1:
            circleOpacity = imageOpacity
        elif deltaLevel > 1:
            circleOpacity = 0
        if isHere:
            circleOpacity = 1

        circles[i].ex['circleOpacity'] = circleOpacity
        circles[i].ex['imageOpacity'] = imageOpacity
        circles[i].ex['labelOpacity'] = labelOpacity
        circles[i].ex['isLabelHeader'] = isLabelHeader

    drawCircles(circles, filename, config, w, h, (offsetX, offsetY, offsetW), resolution, font, subfont)

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
    prefix = cdata['prefix'] if 'prefix' in cdata else config['defaultPrefix']
    unit = cdata['unit'] if 'unit' in cdata else config['defaultUnit']
    countFormatted = formatNumber(cdata['datum'])
    lines = []
    lines.append(collectionName)
    if not a.NO_NUMBERS:
        lines.append(f'{prefix}{countFormatted} {unit}')
    if isHere:
        lines = ['You are here']
        lines.append('('+collectionName+')')
    lineCount = len(lines)
    for j, line in enumerate(lines):
        label = {}
        label['text'] = line
        label['isLastLine'] = j == lineCount-1
        # lw, lh = font.getsize(line)
        left, top, right, bottom = font.getbbox(line)
        if label['isLastLine']:
             left, top, right, bottom = subfont.getbbox(line)
        lw = right - left
        lh = bottom - top
        label['size'] = (lw, lh)
        lines[j] = label
    circles[i].ex['label'] = lines
    circles[i].ex['labelWidth'] = max(l['size'][0] for l in lines)
    circles[i].ex['labelHeight'] = sum(l['size'][1] for l in lines) + (lineCount-1) * lineSpacing
    circles[i].ex['labelOpacity'] = 0
    circles[i].ex['labelColor'] = list(ImageColor.getrgb(config['labelColor']))
    circles[i].ex['labelSpacing'] = lineSpacing

    fillColor = "#000000"
    if 'colorPalette' in cdata:   
        colorIndex = wrapNumber(cdata['level'] - 1, (0, len(cdata['colorPalette'])-1))
        fillColor = cdata['colorPalette'][colorIndex]
    if isHere:
        fillColor = config['hereColor']
    circles[i].ex['fillColor'] = fillColor

    # load images
    if 'image' in cdata:
        loadedImage = None
        if cdata['image'] in imageCache:
            loadedImage = imageCache[cdata['image']]
        else:
            loadedImage = Image.open(cdata['image'])
            imageCache[cdata['image']] = loadedImage
        circles[i].ex['bgImage'] = Image.new(loadedImage.mode, loadedImage.size, color=fillColor)
        circles[i].ex['image'] = loadedImage

# generate a path that zooms out from HERE then zooms back into HERE
path = []
hereNode = circleLookup[here['id']]
node = circles[hereNode.ex['index']]
node = circles[node.ex['parentIndex']]
while True:
    path.append(node)
    parentIndex = node.ex['parentIndex']
    if parentIndex < 0:
        break
    node = circles[parentIndex]
# pathReversed = list(reversed(path[:-1]))
# path += pathReversed

# if a.DEBUG:
#     drawCircles(circles, "output/test.png", config, a.WIDTH, a.HEIGHT, (0, 0, 1.0), RESOLUTION, font, subfont)

outputFramePattern = f'output/frames/{a.HERE_KEY}/frame.%s.png'
if not a.DEBUG:
    makeDirectories(outputFramePattern)
    removeFiles(outputFramePattern % '*')

zoomDuration = config['zoomDuration']
restDuration = config['restDuration']
zoomFrames = msToFrame(zoomDuration, a.FPS)
restFrames = msToFrame(restDuration, a.FPS)
halfRestFrames = roundInt(restFrames / 2)
totalPathFrames = (len(path)-1) * (zoomFrames + restFrames)
totalFrames = totalPathFrames * 2
currentFrame = 1
frameFilenames = []
if not a.DEBUG:
    print(f'Rendering frames to {(outputFramePattern % "*")}...')
for i in range(len(path)-1):
    fromNode = path[i]
    toNode = path[i+1]
    if a.DEBUG:
        tweenNodes(circles, f'output/tween_test_{i}.png', fromNode, toNode, 0.0, config, a.WIDTH, a.HEIGHT, RESOLUTION, font, subfont)
        if i >= (len(path)-2):
            tweenNodes(circles, f'output/tween_test_{i+1}.png', fromNode, toNode, 1.0, config, a.WIDTH, a.HEIGHT, RESOLUTION, font, subfont)
    else:
        referenceFrame = None
        for i in range(halfRestFrames):
            frameFilename = outputFramePattern % zeroPad(currentFrame, totalFrames)
            if i == 0:
                tweenNodes(circles, frameFilename, fromNode, toNode, 0.0, config, a.WIDTH, a.HEIGHT, RESOLUTION, font, subfont)
                referenceFrame = frameFilename
            else:
                shutil.copyfile(referenceFrame, frameFilename)
            printProgress(currentFrame, totalPathFrames)
            frameFilenames.append(frameFilename)
            currentFrame += 1

        for i in range(zoomFrames):
            frameFilename = outputFramePattern % zeroPad(currentFrame, totalFrames)
            t = 1.0 * i / (zoomFrames-1)
            tweenNodes(circles, frameFilename, fromNode, toNode, t, config, a.WIDTH, a.HEIGHT, RESOLUTION, font, subfont)
            printProgress(currentFrame, totalPathFrames)
            referenceFrame = frameFilename
            frameFilenames.append(frameFilename)
            currentFrame += 1

        for i in range(halfRestFrames):
            frameFilename = outputFramePattern % zeroPad(currentFrame, totalFrames)
            shutil.copyfile(referenceFrame, frameFilename)
            printProgress(currentFrame, totalPathFrames)
            frameFilenames.append(frameFilename)
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
