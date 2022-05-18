#!/usr/bin/env python
# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup
import requests

import collections
import json
import mimetypes
import os
import re
import sys


class IwaraDownloader:
    IWARA_URL_RE = re.compile(r"(?:https?://(?:(ecchi\.)?(?:iwara\.tv/(videos|images|playlist|users)/)))([\%\-\w]+)")

    VIDEO_URL = "https://ecchi.iwara.tv/videos/{}"
    IMAGE_URL = "https://ecchi.iwara.tv/images/{}"
    PLAYLIST_URL = "https://ecchi.iwara.tv/playlist/{}"
    USER_URL = "https://ecchi.iwara.tv/users/{}"

    VIDEO_API = "https://www.iwara.tv/api/video/{}"

    STATS_RE = re.compile(r"[\d,]+")
    DATE_RE = re.compile(r"\d+-\d{2}-\d{2} \d{2}:\d{2}")

    def __init__(self, chunk_size=1024, dump_metadata=False, save_thumbnail=False, filename_template=None, quiet=True):
        self.chunk_size = chunk_size
        self.dump_metadata = dump_metadata
        self.save_thumbnail = save_thumbnail
        self.filename_template = filename_template or ""
        self.quiet = quiet
        self.session = requests.session()

    class IwaraVideo:
        def __init__(self, downloader, video_id):
            self.downloader = downloader
            self.id = video_id
            self.collect_parameters()
            self.downloader.output("Downloading {0} - {1}...\n".format(self.id, self.title))

        def collect_parameters(self):
            self.url = self.downloader.VIDEO_URL.format(self.id)
            video_response = self.downloader.session.get(self.url)
            video_html = BeautifulSoup(video_response.text, "html.parser")

            self.title = video_html.title.text.rstrip(" | Iwara")
            self.uploader = video_html.select("div.content div.submitted a.username")[0].text
            self.uploader_id = video_html.select("div.content div.submitted a.username")[0]["href"].lstrip("/users/")

            self.upload_date = IwaraDownloader.DATE_RE.search(video_html.select("div.content div.submitted")[0].getText())[0]

            node_views = video_html.select("div.node-views")[0].getText() if len(video_html.select("div.node-views")) > 0 else "0 0"
            stats_matches = IwaraDownloader.STATS_RE.findall(node_views)
            self.likes_count = stats_matches[0].replace(",", "") if stats_matches else None
            self.views_count = stats_matches[1].replace(",", "") if stats_matches else None

            comments_header = video_html.select("#comments h2")[0].getText() if len(video_html.select("#comments h2")) > 0 else "0"
            comments_match = IwaraDownloader.STATS_RE.search(comments_header)
            self.comments_count = comments_match[0] if comments_match else None

            self.thumbnail_url = absolute_url(video_html.select("#video-player")[0]["poster"])

        def get_download_params(self, quality):
            formats_json = json.loads(self.downloader.session.get(self.downloader.VIDEO_API.format(self.id)).text)

            format_requested = None
            for format in formats_json:
                if format["resolution"] == quality:
                    format_requested = format
            if not format_requested:
                self.downloader.output("Quality '{}' is not available. Please check and try again.\n".format(quality))
                return
            self.download_url = absolute_url(format_requested["uri"])
            self.mimetype = format_requested["mime"]
            self.ext = mimetypes.guess_extension(self.mimetype).lstrip(".")
            return self.download_url

    class IwaraImage:
        def __init__(self, downloader, image_slug):
            self.downloader = downloader
            self.id = image_slug
            self.collect_parameters()

        def collect_parameters(self):
            image_html = self.downloader.session.get(self.downloader.IMAGE_URL.format(self.id))
            self.url = ""

    class IwaraPlaylist:
        def __init__(self, downloader, playlist_slug):
            self.downloader = downloader
            self.playlist_slug = playlist_slug
            self.items = ""

    class IwaraUser:
        def __init__(self, downloader, username):
            self.downloader = downloader
            self.username = username
            self.items = ""


    def output(self, output):
        if not self.quiet:
            sys.stdout.write(output)
            sys.stdout.flush()

    def perform_download(self, url, filename):
        request = self.session.get(url, stream=True)
        request.raise_for_status()

        file_size = int(request.headers["Content-Length"])
        tmp_filename = replace_extension(filename, "part")
        self.output("File: {}\n".format(filename))

        if os.path.exists(filename):
            existing_file_size = os.path.getsize(filename)
            if file_size >= existing_file_size:
                self.output("File exists and appears complete. Skipping...\n")
                return
            else:
                self.output("File exists, but is smaller than file to be downloaded. Overwriting...\n")
                os.remove(filename)

        downloaded = 0
        with open(tmp_filename, "wb") as file:
            for chunk in request.iter_content(self.chunk_size):
                downloaded += len(chunk)
                file.write(chunk)
                done = int(25 * downloaded / file_size)
                percent = int(100 * downloaded / file_size)
                self.output("\r|{0}{1}| {2}% ".format("\u2588" * done, " " * (25 - done), percent))
        self.output("\n")
        os.rename(tmp_filename, filename)

    def download_playlist(self, playlist_slug):
        playlist = self.IwaraPlaylist(self, playlist_slug)
        for item in playlist.items:
            filename = self.create_filename(item.parameters)
            self.perform_download(filename, item.url)

    def download_user(self, username):
        user = self.IwaraUser(self, username)
        for item in user.items:
            filename = self.create_filename(item.parameters)
            self.perform_download(filename, item.url)

    def download_video(self, video_id, quality):
        video = self.IwaraVideo(self, video_id)
        download_url = video.get_download_params(quality)
        if not download_url:
            self.output("Failed to collect download URL.\n")
            return
        filename = self.create_filename(video.__dict__)
        self.perform_download(download_url, filename)
        if self.dump_metadata:
            self.save_metadata(video, filename)
        if self.save_thumbnail:
            self.get_thumbnail(video, filename)

    def download_image(self, image_slug):
        image = self.IwaraImage(self, image_slug)
        filename = self.create_filename(image.parameters)
        self.perform_download(filename, image.url)

    def create_filename(self, template_params):
        if self.filename_template:
            template_dict = dict(template_params)
            template_dict = dict((k, sanitize_for_path(str(v))) for k, v in template_dict.items() if v)
            template_dict = collections.defaultdict(lambda: "__NONE__", template_dict)

            filename = self.filename_template.format_map(template_dict)
            if (os.path.dirname(filename) and not os.path.exists(os.path.dirname(filename))) or os.path.exists(os.path.dirname(filename)):
                os.makedirs(os.path.dirname(filename), exist_ok=True)

            return filename
        else:
            filename = "{0} - {1}.{2}".format(template_params["id"], template_params["title"], template_params["ext"])
            return sanitize_for_path(filename)

    def save_metadata(self, object, filename):
        self.output("Dumping metadata...\n")
        filename = replace_extension(filename, "json")
        object_dict = object.__dict__
        object_dict.pop("downloader") # Downloader reference
        with open(filename, "w") as file:
            json.dump(object_dict, file, sort_keys=True)

    def get_thumbnail(self, object, filename):
        self.output("Saving thumbnail...\n")
        filename = replace_extension(filename, "jpg")
        thumbnail_request = self.session.get(object.thumbnail_url)
        thumbnail_request.raise_for_status()

        with open(filename, "wb") as file:
            for block in thumbnail_request.iter_content(self.chunk_size):
                file.write(block)


#  Utility functions
def sanitize_for_path(value, replace=' '):
    """Remove potentially illegal characters from a path."""
    sanitized = re.sub(r'[<>\"\?\\\/\*:|]', replace, value)
    return re.sub(r'[\s.]+$', '', sanitized)

def replace_extension(filename, new_extension):
    """Replace the extension in a file path."""

    base_path, _ = os.path.splitext(filename)
    return "{0}.{1}".format(base_path, new_extension)

def absolute_url(url):
    if url.startswith("//"):
        url = "https:" + url
        return url