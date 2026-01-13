from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import os
import time

# 配置项
TARGET_URL = "https://epg.51zmt.top:8001/multicast/"
M3U8_OUTPUT_PATH = "tv_channels.m3u8"

def fetch_page_content_with_playwright(url):
    """用Playwright爬取动态渲染的页面（支持JS加载）"""
    html_content = None
    try:
        with sync_playwright() as p:
            # 启动无头浏览器（无界面模式，适合CI/CD）
            browser = p.chromium.launch(headless=True, ignore_https_errors=True)
            context = browser.new_context(
                ignore_https_errors=True,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            # 访问页面，等待JS加载完成（关键）
            page.goto(url, timeout=60000)
            time.sleep(3)  # 等待3秒，确保动态内容加载完毕
            # 可选：等待特定元素加载（更精准）
            # page.wait_for_selector("a[href*='rtsp://']", timeout=30000)
            
            # 获取加载后的完整HTML
            html_content = page.content()
            browser.close()
            
            # 保存动态加载后的页面到本地
            with open("debug_dynamic_page.html", "w", encoding="utf-8") as f:
                f.write(html_content)
            print("✅ 动态页面爬取成功，已保存 debug_dynamic_page.html 供调试")
    except Exception as e:
        print(f"❌ 动态爬取页面失败：{e}")
        import traceback
        traceback.print_exc()
    return html_content

def parse_channel_info(html_content):
    """解析动态页面中的RTSP频道信息"""
    channels = []
    if not html_content:
        return channels
    
    soup = BeautifulSoup(html_content, "lxml")
    try:
        # 找到所有包含RTSP链接的a标签
        all_a_tags = soup.find_all("a", href=True)
        rtsp_a_tags = [a for a in all_a_tags if a["href"].strip().startswith("rtsp://")]
        print(f"🔍 找到 {len(rtsp_a_tags)} 个包含RTSP链接的a标签")
        
        if len(rtsp_a_tags) == 0:
            # 打印所有href，确认动态页面是否有RTSP链接
            all_hrefs = [a["href"].strip() for a in all_a_tags if a["href"].strip()][:20]
            print(f"⚠️ 动态页面仍未找到RTSP链接，所有a标签href：{all_hrefs}")
            return channels
        
        # 提取频道信息
        for a_tag in rtsp_a_tags:
            play_url = a_tag["href"].strip()
            channel_name = a_tag.get_text(strip=True) or f"未知频道_{play_url[-6:]}"
            group = "默认分组"
            
            # 尝试提取分组（从父元素找关键词）
            parent_elem = a_tag.find_parent(["div", "li", "span"])
            if parent_elem:
                parent_text = parent_elem.get_text(strip=True)
                for keyword in ["央视", "卫视", "地方", "体育", "电影", "新闻"]:
                    if keyword in parent_text:
                        group = keyword
                        break
            
            # 提取台标（动态页面中的img标签）
            logo = ""
            img_tag = a_tag.find_previous_sibling("img") or parent_elem.find("img") if parent_elem else None
            if img_tag and "src" in img_tag.attrs:
                logo = img_tag["src"].strip()
                if logo and not logo.startswith(("http://", "https://")):
                    logo = f"https://epg.51zmt.top:8001{logo}"
            
            channels.append({
                "name": channel_name,
                "url": play_url,
                "group": group,
                "logo": logo
            })
        
        print(f"✅ 成功解析 {len(channels)} 个有效RTSP频道")
    except Exception as e:
        print(f"❌ 解析频道信息失败：{e}")
        traceback.print_exc()
    return channels

def generate_m3u8(channels, output_path):
    """生成标准m3u8文件"""
    if not channels:
        print("⚠️ 无有效频道，跳过生成m3u8")
        return
    
    m3u8_header = "#EXTM3U x-tvg-url=\"https://epg.51zmt.top:8001/xmltv.xml\"\n"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(m3u8_header)
        for idx, channel in enumerate(channels):
            logo = channel["logo"] if channel["logo"] else ""
            extinf_line = f"#EXTINF:-1 tvg-id=\"{idx+1}\" tvg-name=\"{channel['name']}\" tvg-logo=\"{logo}\" group-title=\"{channel['group']}\",{channel['name']}\n"
            f.write(extinf_line)
            f.write(f"{channel['url']}\n\n")
    
    print(f"📁 m3u8文件生成完成：{output_path}（共{len(channels)}个频道）")

if __name__ == "__main__":
    # 1. 爬取动态页面
    html = fetch_page_content_with_playwright(TARGET_URL)
    if not html:
        exit(1)
    
    # 2. 解析频道信息
    channels = parse_channel_info(html)
    if not channels:
        print("❌ 未解析到任何有效RTSP频道信息")
        exit(1)
    
    # 3. 生成m3u8文件
    generate_m3u8(channels, M3U8_OUTPUT_PATH)
