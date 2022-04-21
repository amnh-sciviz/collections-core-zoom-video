# Collections Core Zoom Video Generator

Generates videos for collections core arrays that zoom in and out of the Museum's full collection context

## Requirements

1. [Python 3+](https://www.python.org/downloads/) - For generating frames
2. [ffmpeg](https://www.ffmpeg.org/download.html) - For compiling frames into videos
3. Install Python modules:

    ```
    pip install -r requirements.txt
    ```

## Configuration

All content configuration can be found in the [config.json](/amnh-sciviz/collections-core-zoom-video/blob/main/config.json) file. Config properties should be relatively self-explanatory. The most important entries are the `mediaArrays` and `data` which control the visualization.

### mediaArrays

Each media array should have an entry in the `mediaArrays` object. Each of these entries correspond to a unique video that will be embedded in that particular media array. For example, the `trilobites` entry will generate a video that will zoom out from the Trilobite collection to the Fossil Invertebrates collection to the Paleontology department then finally to the total Museum collection and then loop back.

### data

The visualization is almost entirely generated via the `data` entry in the configuration. The data is in a "tree" format where each node of the tree has a parent and children (except for the root node which has no parent, and the leaf nodes which have no children). Each node needs at least an `id` (which will also serve as the node's label) and a `datum` which is the number of objects in that collection. Nodes with children do not need to define `datum` since it is assumed that number is the sum of its children. Nodes can optionally have an `image` which will be placed in the background of that node; otherwise, it will use the colors defined in the `colorPalette` config entry.

## Running the script

To generate a video for a particular media array, it must have an entry in the `mediaArrays` entry in the configuration file. You can then generate a video based on that key. For example, to generate a video for the Trilobite array, you can run:

```
python run.py -array trilobites
```

Which will create a video at `output/trilobites.mp4`.  You can also define a custom path and filename like:

```
python run.py -array trilobites -out "custom/path/trilobites_test.mp4"
```

By default, the video will be at 30 fps and a square video at 1080 x 1080. But you can customize this like so:

```
python run.py -array trilobites -fps 15 -width 720 -height 720 -out "output/trilobites_lores.mp4"
```
