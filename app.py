import streamlit as st
import pandas as pd
import requests
import time
import random
import io
import re

# --- 1. 网页配置 ---
st.set_page_config(page_title="B站数据精准抓取工具", layout="wide", page_icon="📺")

# 💡 开发者预设 Cookie
DEFAULT_COOKIE = "在此粘贴你的默认Cookie"

# --- 2. 初始化 Session State (核心修复) ---
# 确保所有输入变量在点击按钮后依然存在
if 'clicked' not in st.session_state:
    st.session_state.clicked = False
if 'user_cookie' not in st.session_state:
    st.session_state.user_cookie = ""
if 'keyword' not in st.session_state:
    st.session_state.keyword = "Audrey Hobert"
if 'max_pages' not in st.session_state:
    st.session_state.max_pages = 20

def click_button():
    st.session_state.clicked = True

# --- 3. 核心爬虫逻辑 (保持不变) ---
def run_bili_spider(kw, limit_pg, ck):
    all_videos = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://search.bilibili.com/",
        "Cookie": ck
    }
    clean_kw = kw.replace('"', '').replace('“', '').replace('”', '')
    search_kw = f'"{clean_kw}"'
    url = "https://api.bilibili.com/x/web-interface/search/type"
    
    progress_bar = st.progress(0, text="准备开始...")
    for p in range(1, limit_pg + 1):
        params = {"search_type": "video", "keyword": search_kw, "page": p}
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            data = resp.json()
            if data['code'] == 0 and 'result' in data['data'] and data['data']['result']:
                v_list = data['data']['result']
                if p == 1:
                    total_results = data['data'].get('numResults', '未知')
                    st.toast(f"💡 搜索到约 {total_results} 条相关视频", icon="🔍")
                for v in v_list:
                    title = re.sub(r'<[^>]+>', '', v.get('title', ''))
                    core_words = clean_kw.split()
                    if all(word.lower() in title.lower() for word in core_words):
                        all_videos.append({
                            "BVID": v.get('bvid'), 
                            "标题": title,
                            "播放量": v.get('play'),
                            "弹幕数": v.get('video_review'),
                            "发布日期": time.strftime("%Y-%m-%d", time.localtime(v.get('pubdate'))),
                            "UP主": v.get('author'),
                            "时长": v.get('duration'),
                            "视频链接": f"https://www.bilibili.com/video/{v.get('bvid')}"
                        })
            else:
                st.info(f"📍 已到达 B 站搜索末尾（第 {p-1} 页）")
                break
        except:
            break
        progress_bar.progress(p / limit_pg, text=f"正在采集第 {p}/{limit_pg} 页...")
        time.sleep(random.uniform(0.6, 1.2))
    progress_bar.empty()
    if not all_videos: return pd.DataFrame()
    df = pd.DataFrame(all_videos)
    df.drop_duplicates(subset=['BVID'], keep='first', inplace=True)
    df['播放量'] = pd.to_numeric(df['播放量'], errors='coerce').fillna(0).astype(int)
    df['弹幕数'] = pd.to_numeric(df['弹幕数'], errors='coerce').fillna(0).astype(int)
    df.sort_values(by='播放量', ascending=False, inplace=True)
    df.drop(columns=['BVID'], inplace=True)
    return df

# --- 4. 界面布局 ---
_, main_col, _ = st.columns([1, 2, 1])

with main_col:
    # 情况 A：显示搜索前的配置页面
    if not st.session_state.clicked:
        st.title("📺 Bilibili 数据精准导出助手")
        
        with st.expander("📖 使用指南 & 风险警示"):
            col_a, col_b = st.columns(2)
            with col_a:
                st.info("1.填Cookie -> 2.输词 -> 3.设上限 -> 4.导出")
            with col_b:
                st.warning("Cookie 请妥善保管，建议使用小号")

        st.divider()
        st.header("⚙️ 配置中心")
        
        # 将输入框直接绑定到 session_state
        st.session_state.user_cookie = st.text_area(
            "1. 粘贴你的 Cookie (可选)", 
            value=st.session_state.user_cookie,
            height=100, 
            placeholder="留空则尝试公共通道..."
        )
        
        c_kw, c_pg = st.columns([2, 1])
        with c_kw:
            st.session_state.keyword = st.text_input("2. 搜索关键词", value=st.session_state.keyword)
        with c_pg:
            st.session_state.max_pages = st.number_input("3. 最大爬取页数", min_value=1, max_value=100, value=st.session_state.max_pages)

        st.divider()
        st.button("🚀 开始精准抓取", use_container_width=True, on_click=click_button)

# 情况 B：显示搜索中及结果页面
if st.session_state.clicked:
    # 重新读取变量
    final_ck = st.session_state.user_cookie.strip() if st.session_state.user_cookie.strip() else DEFAULT_COOKIE
    
    if not final_ck or final_ck == "在此粘贴你的默认Cookie":
        with main_col:
            st.error("❌ 无法开始：请先配置有效的 Cookie")
            if st.button("⬅️ 返回修改"):
                st.session_state.clicked = False
                st.rerun()
    else:
        st.title(f"🔍 正在检索: {st.session_state.keyword}")
        with st.spinner('正在为您筛选最精准的数据...'):
            df_final = run_bili_spider(st.session_state.keyword, st.session_state.max_pages, final_ck)
            
        if not df_final.empty:
            st.success(f"🎊 抓取完成！共获得 {len(df_final)} 条结果。")
            st.dataframe(df_final, use_container_width=True)
            
            # 下载与重置
            d_col, r_col = st.columns([3, 1])
            with d_col:
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df_final.to_excel(writer, index=False, sheet_name='B站数据')
                st.download_button(
                    label="📥 下载 Excel 结果文件",
                    data=buffer.getvalue(),
                    file_name=f"B站_{st.session_state.keyword}_导出.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            with r_col:
                if st.button("🔄 重新搜索", use_container_width=True):
                    st.session_state.clicked = False
                    st.rerun()
        else:
            with main_col:
                st.warning("🧐 未发现匹配结果。")
                if st.button("⬅️ 返回"):
                    st.session_state.clicked = False
                    st.rerun()
