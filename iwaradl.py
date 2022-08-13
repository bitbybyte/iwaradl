#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Download videos and other data from Iwara"""

import argparse
import getpass
import netrc
import sys

import models

__author__ = "bitbybyte"
__copyright__ = "Copyright 2019 bitbybyte"

__license__ = "MIT"
__version__ = "0.1"

BASE_HOST = "iwara.tv"

if __name__ == "__main__":
    cmdl_usage = "%(prog)s [options] url"
    cmdl_version = __version__
    cmdl_parser = argparse.ArgumentParser(usage=cmdl_usage, conflict_handler="resolve")

    cmdl_parser.add_argument("-q", "--quiet", action="store_true", dest="quiet", help="suppress output")
    cmdl_parser.add_argument("-v", "--version", action="version", version=cmdl_version)
    cmdl_parser.add_argument("-f", "--file", nargs="?", dest="txt_file", help="text file list")

    cmdl_parser.add_argument("url", action="store", nargs="*", help="video URL")

    dl_group = cmdl_parser.add_argument_group("download options")
    dl_group.add_argument("-q", "--quality", nargs="?", default="Source", dest="quality", help="video quality to download")
    dl_group.add_argument("-o", "--output-path", dest="output_path", help="custom filename template")
    dl_group.add_argument("-m", "--dump-metadata", action="store_true", dest="dump_metadata", help="store metadata to file")
    dl_group.add_argument("-t", "--save-thumbnail", action="store_true", dest="save_thumbnail", help="save thumbnail")


    cmdl_opts = cmdl_parser.parse_args()

    downloader = models.IwaraDownloader(dump_metadata=cmdl_opts.dump_metadata, save_thumbnail=cmdl_opts.save_thumbnail, filename_template=cmdl_opts.output_path, quiet=cmdl_opts.quiet)

    def process_url(url):
        url_groups = downloader.IWARA_URL_RE.match(url)
        if url_groups:
            if url_groups[2] == "videos":
                downloader.download_video(url_groups[3], quality=cmdl_opts.quality)
                return True
            elif url_groups[2] == "images":
                # downloader.download_image(url_groups[3])
                print("Not yet implemented")
                return False
            elif url_groups[3] == "playlist":
                # downloader.download_playlist(url_groups[3])
                print("Not yet implemented")
                return False
            elif url_groups[4] == "users":
                # downloader.download_user(url_groups[3])
                print("Not yet implemented")
                return False

    if cmdl_opts.txt_file:
        if cmdl_opts.url:
            print("Ignoring URL arguments and processing -f/--file.")
        with open(cmdl_opts.txt_file, encoding="utf-8") as txt_list:
            urls = txt_list.readlines()
            for url in urls:
                try:
                    processed = process_url(url)
                    if not processed:
                        print("URL is not fully qualified or invalid. Skipping...")
                except Exception:
                    print("Encountered an error. Skipping URL...")
                    continue
    elif cmdl_opts.url:
        for url in cmdl_opts.url:
            try:
                processed = process_url(url)
                if not processed:
                    print("URL is not fully qualified or invalid. Skipping...")
            except Exception:
                print("Encountered an error. Skipping URL...")
                continue
    else:
        sys.exit("Please provide a fully qualified Iwara URL")
