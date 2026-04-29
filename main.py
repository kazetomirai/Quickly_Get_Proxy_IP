# -*- coding: utf-8 -*-
"""主程序入口，YouTube视频密码提取监控工具.

该程序每天定时监控指定YouTube博主的最新视频，
提取视频字幕中的密码信息并保存。
"""
import logging
import os
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

from youtube_monitor import YouTubeMonitor
from subtitle_parser import SubtitleParser, extract_first_https_link
from privatebin_decrypt import PrivateBinDecryptor

def main():

    youtubemonitor = YouTubeMonitor("ZYFXS", cookies_file="./www.youtube.com_cookies.txt")
    print("开始获取视频列表...")
    cnt = 0 
    # 获取最新视频列表
    for item in youtubemonitor.get_latest_videos(limit=5):
        # 检查视频标题是否包含关键词
        if '免费节点' in item.title:
            # print(f"找到目标视频: {item.title}")
            # print("=" * 60)

            # 从视频描述中提取第一个https链接
            description = item.description
            # print(description)
            download_link = extract_first_https_link(description, keyword='下载地址')
            if download_link:
                print(f"下载地址: {download_link}")
            else:
                print("未找到下载地址")
            
            # print("=" * 60)

            # 检查是否有可用字幕
            if not item.subtitle_languages:
                print("该视频没有可用字幕")
                break
            
            # 下载字幕（使用第一个可用语言）
            subtitle = youtubemonitor.download_subtitle(
                item.video_id,
                item.subtitle_languages[0].replace('(auto)', '')
            )

            if subtitle:
                # print("获取视频字幕成功")

                # 解析字幕并提取密码
                subtitleparser = SubtitleParser(subtitle)

                # 提取"密码"后面的4位数字
                password = subtitleparser.extract_password_digits(
                    keyword='密码',
                    digit_count=4
                )

                if password:
                    print(f"找到密码: {password}")

                    # 检查下载链接是否存在
                    if not download_link:
                        print("错误: 未找到下载地址，无法解密")
                    else:
                        # https://paste.to/js/privatebin.js?2.0.3
                        decryptor = PrivateBinDecryptor()
                        result = decryptor.decrypt_from_url(
                            download_link,
                            password=password
                        )
                        # print(result)
                        proxy_link = extract_first_https_link(result, keyword='v2ray')
                        cnt += 1
                        print(f"已处理 {cnt} 个视频")
                        print("*"*50)
                        print(proxy_link)
                        print("*"*50)

                    
                else:
                    print("未找到密码")
            else:
                print("获取字幕失败")



if __name__ == '__main__':
    main()
