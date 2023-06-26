import os
from inspect import getsourcefile


this_path = os.path.abspath(getsourcefile(lambda:0))
this_folder = os.path.dirname(this_path)
repo_folder = os.path.dirname(os.path.dirname(this_folder))
SOURCE_FOLDER = os.path.dirname(this_folder)

ALL_CHANNELS = [
     x.strip(" \n") for x in open(os.path.join(this_folder, "channels.txt"), "r").readlines() if x.strip(" \n")
]