import requests
from bs4 import BeautifulSoup
import os

# 禁用 SSL 警告
requests.packages.urllib3.disable_warnings()

# 配置项
TARGET_URL = "https://epg.51zmt.top:8001/multicast/"
M3U8_OUTPUT_PATH = "tv_channels.m3u8"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def fetch_page_content(url):
    """爬取目标页面内容（保存调试文件）"""
    try:
        headers = {"User-Agent": USER_AGENT}
        response = requests.get(url, headers=headers, verify=False, timeout=30)
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        
        # 保存页面到本地，方便调试
        with open("debug_page.html", "w", encoding="utf-8") as f:
            f.write(response.text)
        print("✅ 页面爬取成功，已保存 debug_page.html 供调试")
        return response.text
    except Exception as e:
        print(f"❌ 爬取页面失败：{e}")
        return None

def parse_channel_info(html_content):
    """核心：先找RTSP链接，再反向提取频道信息"""
    channels = []
    if not html_content:
        return channels
    
    soup = BeautifulSoup(html_content, "lxml")
    try:
        # 第一步：找到所有包含RTSP链接的a标签（精准筛选目标地址）
        all_a_tags = soup.find_all("a", href=True)
        rtsp_a_tags = [a for a in all_a_tags if a["href"].strip().startswith("rtsp://")]
        print(f"🔍 找到 {len(rtsp_a_tags)} 个包含RTSP链接的a标签")
        
        if len(rtsp_a_tags) == 0:
            # 兜底：打印所有a标签的href，确认是否有RTSP链接
            all_hrefs = [a["href"].strip() for a in all_a_tags if a["href"].strip()]
            print(f"⚠️ 未找到RTSP链接，页面中所有a标签href：{all_hrefs[:10]}")  # 只打印前10个避免刷屏
            return channels
        
        # 第二步：遍历每个RTSP链接，提取对应频道信息
        for a_tag in rtsp_a_tags:
            play_url = a_tag["href"].strip()  # RTSP播放地址
            channel_name = ""
            group = "默认分组"
            logo = ""
            
            # 提取频道名称：优先找a标签的文本，若无则找父元素的文本
            if a_tag.get_text(strip=True):
                channel_name = a_tag.get_text(strip=True)
            else:
                # 向上找父元素（p/div/h4等）提取名称
                parent_elem = a_tag.find_parent(["div", "p", "h4", "li"])
                if parent_elem:
                    channel_name = parent_elem.get_text(strip=True).replace("\n", "").replace(" ", "")
            
            # 提取分组：找相邻的标签（如span/label），包含「央视」「卫视」「地方」等关键词
            # 向上找2层父元素，查找分组标签
            parent_div = a_tag.find_parent("div")
            if parent_div:
                group_tags = parent_div.find_all(["span", "label", "b"])
                for tag in group_tags:
                    tag_text = tag.get_text(strip=True)
                    if any(keyword in tag_text for keyword in ["央视", "卫视", "地方", "体育", "电影", "新闻"]):
                        group = tag_text
                        break
            
            # 提取台标：找相邻的img标签（优先找class含logo/img的）
            img_tag = a_tag.find_next_sibling("img") or parent_div.find("img") if parent_div else None
            if img_tag and "src" in img_tag.attrs:
                logo = img_tag["src"].strip()
                # 补全台标路径
                if logo and not logo.startswith(("http://", "https://")):
                    logo = f"https://epg.51zmt.top:8001{logo}"
            
            # 过滤无效频道（名称为空的跳过）
            if channel_name and play_url:
                # 清理频道名称中的特殊字符
                channel_name = channel_name.replace("【", "").replace("】", "").replace("|", "").strip()
                channels.append({
                    "name": channel_name,
                    "url": play_url,
                    "group": group,
                    "logo": logo
                })
        
        print(f"✅ 成功解析 {len(channels)} 个有效RTSP频道")
    except Exception as e:
        print(f"❌ 解析频道信息失败：{e}")
        import traceback
        traceback.print_exc()
    return channels

def generate_m3u8(channels, output_path):
    """生成带分组、台标的标准 m3u8 文件"""
    if not channels:
        print("⚠️ 无有效频道，跳过生成m3u8")
        return
    
    m3u8_header = "#EXTM3U x-tvg-url=\"https://epg.51zmt.top:8001/xmltv.xml\"\n"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(m3u8_header)
        for idx, channel in enumerate(channels):
            logo = channel["logo"] if channel["logo"] else ""
            # 构建标准EXTINF行（兼容IPTV播放器）
            extinf_line = f"#EXTINF:-1 tvg-id=\"{idx+1}\" tvg-name=\"{channel['name']}\" tvg-logo=\"{logo}\" group-title=\"{channel['group']}\",{channel['name']}\n"
            f.write(extinf_line)
            f.write(f"{channel['url']}\n\n")
    
    print(f"📁 m3u8文件生成完成：{output_path}（共{len(channels)}个频道）")

if __name__ == "__main__":
    # 1. 爬取页面
    html = fetch_page_content(TARGET_URL)
    if not html:
        exit(1)
    
    # 2. 解析RTSP频道信息
    channels = parse_channel_info(html)
    if not channels:
        print("❌ 未解析到任何有效RTSP频道信息")
        exit(1)
    
    # 3. 生成m3u8文件
    generate_m3u8(channels, M3U8_OUTPUT_PATH)
