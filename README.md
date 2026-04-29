# YouTube 免费节点提取工具

## 使用方法

### 安装依赖

```bash
pip install -r requirements.txt
```

### 安装额外依赖

- 建议安装 `deno`，用于支持 YouTube 的 JavaScript 提取逻辑
- 推荐导出 YouTube 登录 cookies 到 `youtube_cookies.txt`

### 导出 cookies

如果 `main.py` 仍然提示需要登录或验证，请手动导出浏览器中的 YouTube cookies，并保存为项目根目录下的 `youtube_cookies.txt`。推荐使用以下方式之一：

1. 使用浏览器扩展（例如 `cookies.txt`）导出 `youtube.com` 域名的 cookies。
2. 使用 `yt-dlp` 的 `--cookies-from-browser` 功能。
3. 使用项目自带的导出脚本：

```bash
pip install browser-cookie3
python export_youtube_cookies.py --browser edge
```

如果你遇到类似 “RequiresAdminError” 的错误，说明浏览器数据库仍被 Edge 占用或当前命令需要管理员权限。此时请：

- 关闭所有 Edge 窗口；
- 以管理员身份打开 PowerShell；
- 再次运行导出命令；
- 或使用浏览器扩展手动导出 cookies。

导出后，你可以打开 `youtube_cookies.txt` 验证是否包含以下关键 cookies：
- `SID`
- `HSID`
- `SSID`
- `SAPISID`
- `APISID`

如果你希望使用特定的浏览器配置文件，可以设置环境变量：

```bash
set YOUTUBE_COOKIES_FROM_BROWSER=edge:Default
```

或者在 PowerShell 中：

```powershell
$env:YOUTUBE_COOKIES_FROM_BROWSER = 'edge:Default'
```

### 运行程序

```bash
python main.py
```

## 程序流程

```
1. 获取 YouTube 博主 "ZYFXS" 的最新视频列表
       ↓
2. 查找标题包含 "免费节点" 的视频
       ↓
3. 从视频描述中提取 "下载地址" 后的 PrivateBin 链接
       ↓
4. 下载视频字幕
       ↓
5. 从字幕中提取 "密码" 后面的 4 位数字
       ↓
6. 使用密码解密 PrivateBin 链接
       ↓
7. 从解密内容中提取 V2Ray 订阅链接
```

## 输出示例

```
找到目标视频: xxx免费节点视频
============================================================
下载地址: https://paste.to/?e51ef1ae8a2d7c9b#FPgZrmNMsdhq8wm2...
============================================================
获取视频字幕成功
找到密码: 5253
**************************************************
https://dlink.host/1drv/aHR0cHM6Ly8xZHJ2Lm1zL3Qv...
**************************************************
```

## 自定义配置

如需监控其他博主，修改 `main.py` 中的频道名称：

```python
youtubemonitor = YouTubeMonitor("你的频道名")
```

如需修改视频标题关键词，修改：

```python
if '你的关键词' in item.title:
```
