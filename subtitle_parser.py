# -*- coding: utf-8 -*-
"""字幕解析模块，用于解析SRT和VTT格式的字幕."""

import logging
import re
from dataclasses import dataclass
from typing import List

logger = logging.getLogger(__name__)


@dataclass
class SubtitleEntry:
    """字幕条目数据类."""
    index: int
    start_time: str
    end_time: str
    text: str


class SubtitleParser:
    """字幕解析器，支持SRT和VTT格式."""

    def __init__(self, subtitle_content: str):
        """初始化字幕解析器.

        Args:
            subtitle_content: 字幕文件内容
        """
        self.content = subtitle_content
        self.entries: List[SubtitleEntry] = []

    def parse(self) -> List[SubtitleEntry]:
        """解析字幕内容.

        Returns:
            字幕条目列表
        """
        if not self.content:
            return self.entries

        # 检测字幕格式
        if 'WEBVTT' in self.content[:100]:
            self._parse_vtt()
        else:
            self._parse_srt()

        return self.entries

    def _parse_srt(self):
        """解析SRT格式字幕."""
        # 标准化换行符
        content = self.content.replace('\r\n', '\n').replace('\r', '\n')

        # 按空行分割条目
        blocks = re.split(r'\n\s*\n', content.strip())

        for block in blocks:
            lines = block.strip().split('\n')
            if len(lines) < 2:
                continue

            # 解析序号
            try:
                index = int(lines[0].strip())
            except ValueError:
                continue

            # 解析时间轴
            time_line = lines[1].strip()
            time_match = re.match(
                r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})',
                time_line
            )

            if not time_match:
                continue

            start_time = time_match.group(1)
            end_time = time_match.group(2)

            # 解析文本内容（可能跨多行）
            text_lines = lines[2:]
            text = ' '.join(line.strip() for line in text_lines if line.strip())

            # 去除HTML标签
            text = re.sub(r'<[^>]+>', '', text)

            entry = SubtitleEntry(
                index=index,
                start_time=start_time,
                end_time=end_time,
                text=text
            )
            self.entries.append(entry)

        logger.info(f'解析了 {len(self.entries)} 条SRT字幕')

    def _parse_vtt(self):
        """解析VTT格式字幕."""
        # 移除WEBVTT头部
        content = self.content
        if 'WEBVTT' in content:
            content = content.split('WEBVTT', 1)[1]

        # 标准化换行符
        content = content.replace('\r\n', '\n').replace('\r', '\n')

        # 按空行分割条目
        blocks = re.split(r'\n\s*\n', content.strip())

        index = 0
        for block in blocks:
            lines = block.strip().split('\n')
            if not lines:
                continue

            # 检查是否是NOTE或STYLE块
            if lines[0].strip().startswith('NOTE') or lines[0].strip().startswith('STYLE'):
                continue

            # 尝试解析时间轴
            time_line = None
            text_start = 0

            for i, line in enumerate(lines):
                if '-->' in line:
                    time_line = line.strip()
                    text_start = i + 1
                    break

            if not time_line:
                continue

            # 解析时间
            time_match = re.match(
                r'([\d:.]+)\s*-->\s*([\d:.]+)',
                time_line
            )

            if not time_match:
                continue

            start_time = time_match.group(1)
            end_time = time_match.group(2)

            # 解析文本
            text_lines = lines[text_start:]
            text = ' '.join(line.strip() for line in text_lines if line.strip())

            # 去除HTML标签和VTT特有的标记
            text = re.sub(r'<[^>]+>', '', text)
            text = re.sub(r'\{[^}]+\}', '', text)

            index += 1
            entry = SubtitleEntry(
                index=index,
                start_time=start_time,
                end_time=end_time,
                text=text
            )
            self.entries.append(entry)

        logger.info(f'解析了 {len(self.entries)} 条VTT字幕')

    def get_full_text(self) -> str:
        """获取所有字幕的完整文本.

        Returns:
            合并后的字幕文本
        """
        if not self.entries:
            self.parse()

        texts = [entry.text for entry in self.entries if entry.text]
        return ' '.join(texts)

    def get_text_by_time_range(self, start: str, end: str) -> str:
        """获取指定时间范围内的字幕文本.

        Args:
            start: 开始时间
            end: 结束时间

        Returns:
            时间范围内的字幕文本
        """
        if not self.entries:
            self.parse()

        texts = []
        for entry in self.entries:
            if entry.start_time >= start and entry.end_time <= end:
                texts.append(entry.text)

        return ' '.join(texts)

    def search_text(self, keyword: str) -> List[SubtitleEntry]:
        """搜索包含关键词的字幕条目.

        Args:
            keyword: 搜索关键词

        Returns:
            匹配的字幕条目列表
        """
        if not self.entries:
            self.parse()

        results = []
        keyword_lower = keyword.lower()

        for entry in self.entries:
            if keyword_lower in entry.text.lower():
                results.append(entry)

        return results

    def extract_password_digits(self, keyword: str = '密码', digit_count: int = 4) -> str:
        """从字幕文本中提取关键词后面最先出现的指定数量数字.

        该方法搜索包含关键词的字幕文本，提取关键词后面最先出现的数字。
        例如: "今天的节点密码是5253" -> 提取 "5253"

        Args:
            keyword: 搜索关键词，默认为'密码'
            digit_count: 要提取的数字位数，默认为4位

        Returns:
            提取到的数字字符串，如果未找到则返回空字符串

        Example:
            >>> parser = SubtitleParser(subtitle_content)
            >>> password = parser.extract_password_digits()
            >>> print(password)
            '5253'
        """
        if not self.entries:
            self.parse()

        # 遍历所有字幕条目
        for entry in self.entries:
            text = entry.text

            # 查找关键词位置（不区分大小写）
            keyword_lower = keyword.lower()
            text_lower = text.lower()

            pos = text_lower.find(keyword_lower)
            if pos == -1:
                continue

            # 获取关键词后面的文本
            after_keyword = text[pos + len(keyword):]

            # 使用正则表达式提取最先出现的指定数量数字
            # 匹配关键词后面紧跟的数字（允许中间有少量非数字字符如空格、冒号等）
            pattern = r'[\s:：是]*?(\d{' + str(digit_count) + r'})'
            match = re.search(pattern, after_keyword)

            if match:
                password = match.group(1)
                logger.info(f'从字幕中提取到密码: {password}')
                return password

        logger.warning(f'未在字幕中找到关键词"{keyword}"后的{digit_count}位数字')
        return ''


def extract_first_https_link(text: str, keyword: str = None) -> str:
    """从文本中提取第一个https链接.

    该方法搜索文本中的链接。如果指定了关键词，则提取关键词后面的第一个https链接；
    否则提取整个文本中的第一个https链接。

    Args:
        text: 包含链接的文本
        keyword: 可选的关键词，如果指定则提取关键词后的第一个链接

    Returns:
        提取到的https链接，如果未找到则返回空字符串

    Example:
        >>> text = '下载地址： https://paste.to/?e51ef1ae8a2d7c9b#FPgZrmNMsdhq8wm2'
        >>> link = extract_first_https_link(text, keyword='下载地址')
        >>> print(link)
        'https://paste.to/?e51ef1ae8a2d7c9b#FPgZrmNMsdhq8wm2'
    """
    # HTTPS链接的正则表达式
    # 匹配 https:// 开头的完整URL
    pattern = r'https://[^\s<>"{}|\\^`\[\]]+'

    search_text = text

    # 如果指定了关键词，先找到关键词位置，只搜索关键词后面的文本
    if keyword:
        keyword_lower = keyword.lower()
        text_lower = text.lower()
        pos = text_lower.find(keyword_lower)

        if pos == -1:
            logger.warning(f'未在文本中找到关键词"{keyword}"')
            return ''

        # 从关键词位置开始搜索
        search_text = text[pos + len(keyword):]

    # 查找匹配的链接
    links = re.findall(pattern, search_text)

    if links:
        first_link = links[0]
        # 清理可能的结尾标点符号
        first_link = first_link.rstrip('.,;!?））」」』』')
        logger.info(f'从文本中提取到链接: {first_link}')
        return first_link

    logger.warning('未在文本中找到https链接')
    return ''
