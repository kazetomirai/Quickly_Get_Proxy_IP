# -*- coding: utf-8 -*-
"""YouTube监控模块，用于获取博主最新视频和字幕."""

import logging
import os
import tempfile
from dataclasses import dataclass
from typing import List, Optional

import yt_dlp

import config

# 配置日志
logger = logging.getLogger(__name__)


@dataclass
class VideoInfo:
    """视频信息数据类."""
    video_id: str
    title: str
    description: str
    published_at: str
    url: str
    subtitle_languages: List[str]


class YouTubeMonitor:
    """YouTube监控类，用于获取视频信息和字幕."""

    def __init__(self, channel_identifier: str):
        """初始化YouTube监控器.

        Args:
            channel_identifier: 频道标识符，可以是频道ID、用户名或URL
        """
        self.channel_identifier = channel_identifier
        self.channel_url = self._normalize_channel_url(channel_identifier)
        self.ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }

    def _normalize_channel_url(self, identifier: str) -> str:
        """将各种格式的频道标识符标准化为URL.

        Args:
            identifier: 频道标识符

        Returns:
            标准化的频道URL
        """
        if identifier.startswith('http'):
            return identifier
        elif identifier.startswith('UC') and len(identifier) == 24:
            # 频道ID格式
            return f'https://www.youtube.com/channel/{identifier}'
        elif identifier.startswith('@'):
            # 用户名格式
            return f'https://www.youtube.com/{identifier}'
        else:
            # 默认作为用户名处理
            return f'https://www.youtube.com/@{identifier}'

    def get_latest_videos(self, limit: int = 5) -> List[VideoInfo]:
        """获取博主最新的视频列表.

        Args:
            limit: 获取视频数量限制

        Returns:
            VideoInfo对象列表
        """
        videos = []
        extract_opts = {
            **self.ydl_opts,
            'playlistend': limit,
            'extract_flat': True,
        }

        try:
            with yt_dlp.YoutubeDL(extract_opts) as ydl:
                playlist_info = ydl.extract_info(self.channel_url, download=False)

                if not playlist_info or 'entries' not in playlist_info:
                    logger.warning('未找到视频列表')
                    return videos

                entries = playlist_info['entries']
                logger.info(f'找到 {len(entries)} 个视频')

                # 获取每个视频的详细信息
                for entry in entries:
                    if not entry:
                        continue

                    video_id = entry.get('id')
                    if not video_id:
                        continue

                    video_info = self._get_video_details(video_id)
                    if video_info:
                        videos.append(video_info)

        except Exception as e:
            logger.error(f'获取视频列表失败: {e}')

        return videos

    def _get_video_details(self, video_id: str) -> Optional[VideoInfo]:
        """获取单个视频的详细信息.

        Args:
            video_id: 视频ID

        Returns:
            VideoInfo对象，如果获取失败则返回None
        """
        video_url = f'https://www.youtube.com/watch?v={video_id}'
        detail_opts = {
            **self.ydl_opts,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': config.SUBTITLE_LANGUAGES,
            'skip_download': True,
        }

        try:
            with yt_dlp.YoutubeDL(detail_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)

                if not info:
                    return None

                # 获取可用的字幕语言
                subtitle_languages = []
                subtitles = info.get('subtitles', {})
                automatic_captions = info.get('automatic_captions', {})

                # 检查手动上传的字幕
                for lang in config.SUBTITLE_LANGUAGES:
                    if lang in subtitles:
                        subtitle_languages.append(lang)
                    elif lang in automatic_captions:
                        subtitle_languages.append(f'{lang}(auto)')

                return VideoInfo(
                    video_id=video_id,
                    title=info.get('title', ''),
                    description=info.get('description', ''),
                    published_at=info.get('upload_date', ''),
                    url=video_url,
                    subtitle_languages=subtitle_languages,
                )

        except Exception as e:
            logger.error(f'获取视频详情失败 {video_id}: {e}')
            return None

    def download_subtitle(self, video_id: str, language: str = 'zh-CN') -> Optional[str]:
        """下载视频字幕.

        Args:
            video_id: 视频ID
            language: 字幕语言代码

        Returns:
            字幕内容字符串，如果下载失败则返回None
        """
        video_url = f'https://www.youtube.com/watch?v={video_id}'

        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            download_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': [language],
                'subtitlesformat': 'srt',
                'outtmpl': os.path.join(temp_dir, '%(id)s.%(ext)s'),
            }

            try:
                with yt_dlp.YoutubeDL(download_opts) as ydl:
                    ydl.download([video_url])

                    # 查找下载的字幕文件
                    expected_file = os.path.join(temp_dir, f'{video_id}.{language}.srt')
                    auto_file = os.path.join(temp_dir, f'{video_id}.{language}-auto.srt')

                    subtitle_file = None
                    if os.path.exists(expected_file):
                        subtitle_file = expected_file
                    elif os.path.exists(auto_file):
                        subtitle_file = auto_file

                    if subtitle_file and os.path.exists(subtitle_file):
                        with open(subtitle_file, 'r', encoding='utf-8') as f:
                            return f.read()

                    # 尝试其他可能的文件名
                    for filename in os.listdir(temp_dir):
                        if filename.endswith('.srt'):
                            filepath = os.path.join(temp_dir, filename)
                            with open(filepath, 'r', encoding='utf-8') as f:
                                return f.read()

            except Exception as e:
                logger.error(f'下载字幕失败 {video_id}: {e}')

        return None

    def get_any_available_subtitle(self, video_id: str) -> Optional[str]:
        """尝试获取任意可用的字幕.

        Args:
            video_id: 视频ID

        Returns:
            字幕内容字符串，如果没有可用字幕则返回None
        """
        # 首先尝试配置的语言列表
        for lang in config.SUBTITLE_LANGUAGES:
            subtitle = self.download_subtitle(video_id, lang)
            if subtitle:
                logger.info(f'成功获取字幕: {video_id}, 语言: {lang}')
                return subtitle

        # 如果没有找到，尝试获取视频详情查看可用字幕
        video_info = self._get_video_details(video_id)
        if video_info and video_info.subtitle_languages:
            for lang in video_info.subtitle_languages:
                clean_lang = lang.replace('(auto)', '')
                subtitle = self.download_subtitle(video_id, clean_lang)
                if subtitle:
                    logger.info(f'成功获取字幕: {video_id}, 语言: {lang}')
                    return subtitle

        logger.warning(f'未找到可用字幕: {video_id}')
        return None
