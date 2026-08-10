import asyncio
import glob
import json
import os
import random
import re
from typing import Union

import requests
import yt_dlp
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from ytSearch import Playlist, VideosSearch

from AnonXMusic import LOGGER
from AnonXMusic.utils.formatters import time_to_seconds
from config import YT_API_KEY, YTPROXY_URL as YTPROXY

logger = LOGGER(__name__)

# Ensure downloads directory exists on startup
os.makedirs("downloads", exist_ok=True)


def cookie_txt_file():
    try:
        folder_path = os.path.join(os.getcwd(), "cookies")
        if not os.path.exists(folder_path):
            return None
        filename = os.path.join(folder_path, "logs.csv")
        txt_files = glob.glob(os.path.join(folder_path, "*.txt"))
        if not txt_files:
            return None
        cookie_file = random.choice(txt_files)
        with open(filename, "a", encoding="utf-8") as file:
            file.write(f"Chosen File : {cookie_file}\n")
        return cookie_file
    except Exception as e:
        logger.error(f"Error selecting cookie file: {e}")
        return None


class YouTubeAPI:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = r"(?:youtube\.com|youtu\.be)"
        self.status = "https://www.youtube.com/oembed?url="
        self.listbase = "https://youtube.com/playlist?list="
        self.reg = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

    def _clean_link(self, link: str) -> str:
        if "&" in link:
            link = link.split("&")[0]
        if "?si=" in link:
            link = link.split("?si=")[0]
        elif "&si=" in link:
            link = link.split("&si=")[0]
        return link

    async def exists(self, link: str, videoid: Union[bool, str] = None) -> bool:
        if videoid:
            link = self.base + str(link)
        return bool(re.search(self.regex, link))

    async def url(self, message_1: Message) -> Union[str, None]:
        messages = [message_1]
        if message_1.reply_to_message:
            messages.append(message_1.reply_to_message)
        for message in messages:
            if message.entities:
                for entity in message.entities:
                    if entity.type == MessageEntityType.URL:
                        text = message.text or message.caption
                        return text[entity.offset : entity.offset + entity.length]
            elif message.caption_entities:
                for entity in message.caption_entities:
                    if entity.type == MessageEntityType.TEXT_LINK:
                        return entity.url
        return None

    async def details(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + str(link)
        link = self._clean_link(link)

        results = VideosSearch(link, limit=1)
        res = (await results.next()).get("result", [])
        if not res:
            raise ValueError("Video not found")
        
        result = res[0]
        title = result.get("title", "Unknown")
        duration_min = result.get("duration", "00:00")
        thumbnail = result.get("thumbnails", [{}])[0].get("url", "").split("?")[0]
        vidid = result.get("id")
        duration_sec = int(time_to_seconds(duration_min)) if duration_min and duration_min != "None" else 0
        
        return title, duration_min, duration_sec, thumbnail, vidid

    async def title(self, link: str, videoid: Union[bool, str] = None) -> str:
        if videoid:
            link = self.base + str(link)
        link = self._clean_link(link)

        results = VideosSearch(link, limit=1)
        res = (await results.next()).get("result", [])
        return res[0].get("title", "Unknown") if res else "Unknown"

    async def duration(self, link: str, videoid: Union[bool, str] = None) -> str:
        if videoid:
            link = self.base + str(link)
        link = self._clean_link(link)

        results = VideosSearch(link, limit=1)
        res = (await results.next()).get("result", [])
        return res[0].get("duration", "00:00") if res else "00:00"

    async def thumbnail(self, link: str, videoid: Union[bool, str] = None) -> str:
        if videoid:
            link = self.base + str(link)
        link = self._clean_link(link)

        results = VideosSearch(link, limit=1)
        res = (await results.next()).get("result", [])
        if res and res[0].get("thumbnails"):
            return res[0]["thumbnails"][0]["url"].split("?")[0]
        return ""

    async def video(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + str(link)
        link = self._clean_link(link)

        cookie = cookie_txt_file()
        cmd = ["yt-dlp", "-g", "-f", "best[height<=?720][width<=?1280]"]
        if cookie:
            cmd.extend(["--cookies", cookie])
        cmd.append(link)

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if stdout:
            return 1, stdout.decode().split("\n")[0]
        else:
            return 0, stderr.decode()

    async def playlist(self, link, limit, user_id, videoid: Union[bool, str] = None):
        if videoid:
            link = self.listbase + str(link)
        link = self._clean_link(link)

        playlist = await Playlist.get(link)
        if playlist and "videos" in playlist:
            videos = []
            for video in playlist["videos"][:limit]:
                try:
                    duration = video.get("duration")
                    duration_sec = int(time_to_seconds(duration)) if duration else 0
                    videos.append({
                        "vidid": video["id"],
                        "title": video.get("title", "Unknown"),
                        "duration_min": duration,
                        "duration_sec": duration_sec,
                        "thumbnail": video.get("thumbnails", [{}])[0].get("url", "").split("?")[0] if video.get("thumbnails") else "",
                    })
                except Exception:
                    continue
            return videos
        return None

    async def track(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + str(link)
        link = self._clean_link(link)

        results = VideosSearch(link, limit=1)
        res = (await results.next()).get("result", [])
        if not res:
            raise ValueError("Track not found")
        
        result = res[0]
        track_details = {
            "title": result.get("title", "Unknown"),
            "link": result.get("link"),
            "vidid": result.get("id"),
            "duration_min": result.get("duration"),
            "thumb": result.get("thumbnails", [{}])[0].get("url", "").split("?")[0] if result.get("thumbnails") else "",
        }
        return track_details, result.get("id")

    async def formats(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + str(link)
        link = self._clean_link(link)

        loop = asyncio.get_running_loop()

        def _extract():
            ytdl_opts = {"quiet": True}
            cookie = cookie_txt_file()
            if cookie:
                ytdl_opts["cookiefile"] = cookie

            ydl = yt_dlp.YoutubeDL(ytdl_opts)
            formats_available = []
            r = ydl.extract_info(link, download=False)
            for fmt in r.get("formats", []):
                if "dash" not in str(fmt.get("format", "")).lower():
                    if all(k in fmt for k in ("format", "filesize", "format_id", "ext", "format_note")):
                        formats_available.append({
                            "format": fmt["format"],
                            "filesize": fmt["filesize"],
                            "format_id": fmt["format_id"],
                            "ext": fmt["ext"],
                            "format_note": fmt["format_note"],
                            "yturl": link,
                        })
            return formats_available

        formats_available = await loop.run_in_executor(None, _extract)
        return formats_available, link

    async def slider(self, link: str, query_type: int, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + str(link)
        link = self._clean_link(link)

        try:
            results = []
            search = VideosSearch(link, limit=10)
            search_results = (await search.next()).get("result", [])

            for result in search_results:
                duration_str = result.get("duration", "0:00")
                try:
                    parts = duration_str.split(":")
                    duration_secs = 0
                    if len(parts) == 3:
                        duration_secs = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                    elif len(parts) == 2:
                        duration_secs = int(parts[0]) * 60 + int(parts[1])

                    if duration_secs <= 3600:
                        results.append(result)
                except (ValueError, IndexError):
                    continue

            if not results or query_type >= len(results):
                raise ValueError("No suitable videos found within duration limit")

            selected = results[query_type]
            return (
                selected["title"],
                selected["duration"],
                selected["thumbnails"][0]["url"].split("?")[0],
                selected["id"],
            )

        except Exception as e:
            logger.error(f"Error in slider: {str(e)}")
            raise ValueError("Failed to fetch video details")

    async def download(
        self,
        link: str,
        mystic,
        video: Union[bool, str] = None,
        videoid: Union[bool, str] = None,
        songaudio: Union[bool, str] = None,
        songvideo: Union[bool, str] = None,
        format_id: Union[bool, str] = None,
        title: Union[bool, str] = None,
    ) -> Union[str, tuple]:
        vid_id = link if videoid else link.split("v=")[-1]
        link = self.base + vid_id if videoid else link
        loop = asyncio.get_running_loop()

        def create_session():
            session = requests.Session()
            retries = Retry(total=3, backoff_factor=0.1)
            session.mount("http://", HTTPAdapter(max_retries=retries))
            session.mount("https://", HTTPAdapter(max_retries=retries))
            return session

        async def download_with_requests(url, filepath, headers=None):
            try:
                session = create_session()
                response = session.get(url, headers=headers, stream=True, timeout=60, allow_redirects=True)
                response.raise_for_status()
                
                chunk_size = 1024 * 1024  # 1MB
                with open(filepath, "wb") as file:
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if chunk:
                            file.write(chunk)
                return filepath
            except Exception as e:
                logger.error(f"Requests download failed: {str(e)}")
                if os.path.exists(filepath):
                    os.remove(filepath)
                return None
            finally:
                session.close()

        # Local yt-dlp fallback if API proxy is down/unconfigured
        def ytdl_fallback_download(target_file, is_video=False):
            try:
                ydl_opts = {
                    "outtmpl": target_file.replace(".mp3", ".%(ext)s").replace(".mp4", ".%(ext)s"),
                    "quiet": True,
                    "no_warnings": True,
                }
                cookie = cookie_txt_file()
                if cookie:
                    ydl_opts["cookiefile"] = cookie

                if is_video:
                    ydl_opts["format"] = "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
                else:
                    ydl_opts["format"] = "bestaudio/best"
                    ydl_opts["postprocessors"] = [{
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }]

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([link])
                
                if os.path.exists(target_file):
                    return target_file
                # Check created files
                base_path = target_file.rsplit(".", 1)[0]
                for ext in [".mp3", ".m4a", ".webm", ".mp4"]:
                    if os.path.exists(base_path + ext):
                        return base_path + ext
                return None
            except Exception as e:
                logger.error(f"Fallback yt-dlp failed: {e}")
                return None

        async def audio_dl(vid_id):
            filepath = os.path.join("downloads", f"{vid_id}.mp3")
            if os.path.exists(filepath):
                return filepath

            if YT_API_KEY and YTPROXY:
                headers = {
                    "x-api-key": f"{YT_API_KEY}",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                }
                session = create_session()
                try:
                    getAudio = session.get(f"{YTPROXY}/info/{vid_id}", headers=headers, timeout=60)
                    songData = getAudio.json()
                    if songData.get("status") == "success":
                        result = await download_with_requests(songData["audio_url"], filepath, headers)
                        if result:
                            return result
                except Exception as e:
                    logger.error(f"Proxy audio download failed: {e}")
                finally:
                    session.close()

            # Fallback to direct yt-dlp if proxy fails or not set
            return await loop.run_in_executor(None, ytdl_fallback_download, filepath, False)

        async def video_dl(vid_id):
            filepath = os.path.join("downloads", f"{vid_id}.mp4")
            if os.path.exists(filepath):
                return filepath

            if YT_API_KEY and YTPROXY:
                headers = {
                    "x-api-key": f"{YT_API_KEY}",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                }
                session = create_session()
                try:
                    getVideo = session.get(f"{YTPROXY}/info/{vid_id}", headers=headers, timeout=60)
                    videoData = getVideo.json()
                    if videoData.get("status") == "success":
                        result = await download_with_requests(videoData["video_url"], filepath, headers)
                        if result:
                            return result
                except Exception as e:
                    logger.error(f"Proxy video download failed: {e}")
                finally:
                    session.close()

            # Fallback to direct yt-dlp if proxy fails or not set
            return await loop.run_in_executor(None, ytdl_fallback_download, filepath, True)

        if songvideo:
            title_clean = re.sub(r'[\\/*?:"<>|]', "", str(title)) if title else vid_id
            filepath = os.path.join("downloads", f"{title_clean}.mp4")
            return await video_dl(vid_id)
        elif songaudio:
            title_clean = re.sub(r'[\\/*?:"<>|]', "", str(title)) if title else vid_id
            filepath = os.path.join("downloads", f"{title_clean}.mp3")
            return await audio_dl(vid_id)
        elif video:
            downloaded_file = await video_dl(vid_id)
            return downloaded_file, True
        else:
            downloaded_file = await audio_dl(vid_id)
            return downloaded_file, True
