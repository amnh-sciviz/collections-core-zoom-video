# -*- coding: utf-8 -*-

import itertools
import json
from operator import itemgetter
import os

def addIndices(arr, keyName="index", startIndex=0):
    for i, item in enumerate(arr):
        arr[i][keyName] = startIndex + i
    return arr

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

def readJSON(filename):
    data = {}
    if os.path.isfile(filename):
        with open(filename, encoding="utf8") as f:
            data = json.load(f)
    return data

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
