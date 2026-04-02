import streamlit as st
import pandas as pd
import requests
import time
import random
import re

# --- 网页配置 ---
st.set_page_config(page_title="B站搜索导出工具", layout="wide")
st.title("📺 Bilibili 数据抓取助手")
st.info("居家办公专用：输入你的Cookie和关键词，直接导出清洗后的Excel。")

# --- 侧边栏：用户输入区 ---
with st.sidebar:
    st.header("1. 身份配置")
    user_cookie = st.text_area("粘贴你的 Cookie", help="按F12在Network-nav请求中获取", height=150)
    
    st.header("2. 搜索配置")
    keyword = st.text_input("搜索关键词", value="Audrey Hobert")
    pages = st.number_input("爬取页数", min_value=1, max_value=50, value=5)
    
    start_btn = st.button("🚀 开始抓取数据")

# --- 核心逻辑函数 ---
def run_spider(kw, pg, ck):
    all_videos = []
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://search.bilibili.com/",
        "Cookie": ck
    }
    
    # 进度条
    progress_bar = st.progress(0)
    search_kw = f'"{kw}"' # 自动加双引号精准搜索
    
    for p in range(1, pg + 1):
        params = {"search_type": "video", "keyword": search_kw, "page": p}
        try:
            res = requests.get("https://api.bilibili.com/x/web-interface/search/type", params=params, headers=headers)
            res_data = res.json()
            if res_data['code'] == 0 and 'result' in res_data['data']:
                for v in res_data['data']['result']:
                    title = v.get('title', '').replace('<em class="keyword">', '').replace('</em>', '')
                    # 强力过滤：必须包含核心词
                    if all(word.lower() in title.lower() for word in kw.split()):
                        all_videos.append({
                            "标题": title,
                            "播放量": v.get('play'),
                            "UP主": v.get('author'),
                            "发布时间": time.strftime("%Y-%m-%d", time.localtime(v.get('pubdate'))),
                            "链接": f"https://www.bilibili.com/video/{v.get('bvid')}"
                        })
            progress_bar.progress(p / pg)
            time.sleep(random.uniform(1, 2))
        except:
            break
            
    return pd.DataFrame(all_videos)

# --- 页面交互 ---
if start_btn:
    if not user_cookie:
        st.error("请先在左侧填入你的 Cookie！")
    else:
        with st.spinner("正在爬取并清洗数据..."):
            df_result = run_spider(keyword, pages, user_cookie)
            
        if not df_result.empty:
            st.success(f"抓取成功！共获得 {len(df_result)} 条精准匹配结果。")
            st.dataframe(df_result) # 网页预览数据
            
            # 下载按钮
            csv_data = df_result.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
            st.download_button(
                label="📥 下载清洗后的 CSV 文件",
                data=csv_data,
                file_name=f"B站_{keyword}_数据导出.csv",
                mime="text/csv"
            )
        else:
            st.warning("未找到匹配数据，请尝试更换关键词或更新 Cookie。")