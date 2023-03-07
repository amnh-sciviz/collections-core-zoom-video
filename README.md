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

All content configuration can be found in the [config.json](https://github.com/amnh-sciviz/collections-core-zoom-video/blob/main/config.json) file. Config properties should be relatively self-explanatory. The most important entries are the `mediaArrays` and `data` which control the visualization.

### mediaArrays

Each media array should have an entry in the `mediaArrays` object. Each of these entries correspond to a unique video that will be embedded in that particular media array. For example, the `trilobite-fossils` entry will generate a video that will zoom out from the Trilobite collection to the Fossil Invertebrates collection to the Paleontology department then finally to the total Museum collection and then loop back. Each mediaArray has properties:

- `id`: A unique string which will also be the text that will be displayed at the beginning of the loop
- `parent`: The parent id that this array should be placed under (see section `data`)
- `image`: Path to the image; this should be a png with a transparent background
- `dx` and `dy` _(optional)_: placement of the "here" circle within the parent circle, e.g. `dx: 0, dy: 0` is the center; `dx: -2, dy: 0` is on the left

### data

The visualization is almost entirely generated via the `data` entry in the configuration. The data is in a "tree" format where each node of the tree has a parent and children (except for the root node which has no parent, and the leaf nodes which have no children). Each node needs at least an `id` (which will also serve as the node's label) and a `datum` which is the number of objects in that collection, which determine the circle's size. If `displayNumber` is present, that is what will be displayed; this can be a string or a number. If `displayNumber` is not present, the `datum` will be displayed.

Nodes with children do not need to define `datum` since it is assumed that number is the sum of its children. Nodes can optionally have an `image` which will be placed in the background of that node; otherwise, it will use the colors defined in the `colorPalette` config entry.

## Running the script

To generate a video for a particular media array, it must have an entry in the `mediaArrays` entry in the configuration file. You can then generate a video based on that key. For example, to generate a video for the Trilobite array, you can run:

```
python run.py -array "trilobite-fossils"
```

Which will create a video at `output/trilobite-fossils.mp4`.  You can also define a custom path and filename like:

```
python run.py -array "trilobite-fossils" -out "custom/path/trilobite-fossils_test.mp4"
```

By default, the video will be at 30 fps and a square video at 1080 x 1080. But you can customize this like so:

```
python run.py -array "trilobite-fossils" -fps 15 -width 720 -height 720 -out "output/trilobite-fossils_lores.mp4"
```

To generate a list of videos, you can run:

```
python batch.py -ids "trilobite-fossils,ammonites-fossils,collecting-fossils"
```

Or you can just generate _all_ the videos like this:

```
python batch.py
```

The above script will generate all the videos in the list that don't exist. You can run this if you want to overwrite existing videos:

```
python batch.py -overwrite
```
