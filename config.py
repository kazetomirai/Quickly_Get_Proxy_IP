# -*- coding: utf-8 -*-
"""配置文件，存储项目相关配置信息."""

import os

# YouTube 博主配置
# 支持以下格式：
# - 频道ID: UCxxxxxxxxxxxxxxxxxxx
# - 用户名: @username
# - 频道URL: https://www.youtube.com/@username
YOUTUBE_CHANNEL = os.getenv('YOUTUBE_CHANNEL', '')

# 定时任务配置
SCHEDULE_HOUR = 10  # 每天10点执行
SCHEDULE_MINUTE = 0

# 字幕语言偏好（按优先级排序）
# 'zh-CN' - 简体中文
# 'zh-TW' - 繁体中文
# 'en' - 英文
# 'auto' - 自动生成的字幕
SUBTITLE_LANGUAGES = ['zh-CN', 'zh-TW', 'zh-Hans', 'zh-Hant', 'en', 'auto']

# 数据存储路径
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
PROCESSED_VIDEOS_FILE = os.path.join(DATA_DIR, 'processed_videos.json')
EXTRACTED_PASSWORDS_FILE = os.path.join(DATA_DIR, 'extracted_passwords.json')

# 密码匹配正则表达式模式
# 支持多种常见密码格式
PASSWORD_PATTERNS = [
    r'密码[:：]\s*([\w\-]+)',  # 密码: xxx 或 密码：xxx
    r'password[:：]\s*([\w\-]+)',  # password: xxx
    r'口令[:：]\s*([\w\-]+)',  # 口令: xxx
    r'提取码[:：]\s*([\w\-]+)',  # 提取码: xxx
    r'访问码[:：]\s*([\w\-]+)',  # 访问码: xxx
    r'验证码[:：]\s*([\w\-]+)',  # 验证码: xxx
]

# 日志配置
LOG_LEVEL = 'INFO'
LOG_FILE = os.path.join(DATA_DIR, 'app.log')

# 确保数据目录存在
def ensure_data_dir():
    """确保数据目录存在."""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
