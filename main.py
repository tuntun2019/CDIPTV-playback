import requests
from bs4 import BeautifulSoup
import os

# 禁用 SSL 警告（目标站点可能证书不规范）
requests.packages.urllib3.disable_warnings()

# 配置项
TARGET_URL = "https://epg.51zmt.top:8001/multicast/"
M3U8_OUTPUT_PATH = "tv_channels.m3u8"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def fetch_page_content(url):
    """爬取目标页面内容"""
    try:
        headers = {"User-Agent": USER_AGENT}
        # 目标站点用了自签证书，添加 verify=False
        response = requests.get(url, headers=headers, verify=False, timeout=30)
        response.raise_for_status()  # 抛出 HTTP 错误
        response.encoding = response.apparent_encoding  # 自动识别编码
        return response.text
    except Exception as e:
        print(f"爬取页面失败：{e}")
        return None

def parse_channel_info(html_content):
    """解析页面，提取频道信息（名称、地址、分组、台标）"""
    channels = []
    if not html_content:
        return channels
    
    soup = BeautifulSoup(html_content, "lxml")
    # 根据目标页面的 HTML 结构解析（需适配页面实际结构）
    # 核心逻辑：遍历频道列表行，提取关键信息
    try:
        # 假设页面是表格布局（实际需根据页面结构调整选择器）
        table = soup.find("table")
        if not table:
            print("未找到频道表格")
            return channels
        
        rows = table.find_all("tr")[1:]  # 跳过表头行
        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 3:
                continue  # 跳过无效行
            
            # 提取基础信息（需根据页面实际列调整索引）
            channel_name = cols[0].get_text(strip=True)  # 频道名称
            play_url = cols[1].find("a")["href"] if cols[1].find("a") else ""  # 播放地址
            group = cols[2].get_text(strip=True) if len(cols)>=3 else "默认分组"  # 频道分组
            logo = cols[3].find("img")["src"] if len(cols)>=4 and cols[3].find("img") else ""  # 台标
            
            # 补全台标地址（如果是相对路径）
            if logo and not logo.startswith(("http://", "https://")):
                logo = f"https://epg.51zmt.top:8001{logo}"
            
            if channel_name and play_url:
                channels.append({
                    "name": channel_name,
                    "url": play_url,
                    "group": group,
                    "logo": logo
                })
        print(f"成功解析 {len(channels)} 个频道")
    except Exception as e:
        print(f"解析频道信息失败：{e}")
    return channels

def generate_m3u8(channels, output_path):
    """生成带分组、台标的标准 m3u8 文件"""
    # m3u8 头部（必须以 #EXTM3U 开头，添加扩展参数支持分组/台标）
    m3u8_header = (
        "#EXTM3U x-tvg-url=\"https://epg.51zmt.top:8001/xmltv.xml\"\n"
    )
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(m3u8_header)
        for channel in channels:
            # 构建 EXTM3U 核心行（包含台标、分组、频道名）
            extinf_line = f"#EXTINF:-1 tvg-name=\"{channel['name']}\" tvg-logo=\"{channel['logo']}\" group-title=\"{channel['group']}\",{channel['name']}\n"
            f.write(extinf_line)
            f.write(f"{channel['url']}\n\n")  # 播放地址行
    print(f"m3u8 文件已生成：{output_path}")

if __name__ == "__main__":
    # 1. 爬取页面
    html = fetch_page_content(TARGET_URL)
    if not html:
        exit(1)
    
    # 2. 解析频道信息
    channels = parse_channel_info(html)
    if not channels:
        print("未解析到任何频道信息")
        exit(1)
    
    # 3. 生成 m3u8 文件
    generate_m3u8(channels, M3U8_OUTPUT_PATH)
