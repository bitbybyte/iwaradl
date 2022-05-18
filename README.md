# IwaraDL
Download media and other data from Iwara.

```
usage: iwaradl.py [options] url

positional arguments:
  url                   video URL

options:
  -h, --help            show this help message and exit
  --quiet               suppress output
  -v, --version         show program's version number and exit

download options:
  -q [QUALITY], --quality [QUALITY]
                        video quality to download
  -o OUTPUT_PATH, --output-path OUTPUT_PATH
                        custom filename template
  -m, --dump-metadata   store metadata to file
  -t, --save-thumbnail  save thumbnail
```


## Build Requirements
 - Python 3.x
 - requests
 - beautifulsoup4

## Roadmap
 - Enumerate available video qualities
 - Enumerate available template parameters
 - Image downloads
 - Playlist downloads
 - Lists from text files
 - Support logins
 - Support private content
 - Better download resuming