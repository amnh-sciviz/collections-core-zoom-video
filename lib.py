# -*- coding: utf-8 -*-

import json
import os

def createLookup(arr, key):
    return dict([(str(item[key]), item) for item in arr])

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

def readJSON(filename):
    data = {}
    if os.path.isfile(filename):
        with open(filename, encoding="utf8") as f:
            data = json.load(f)
    return data
