import streamlit as st
import pandas as pd
import requests
import time
import random
import io
import re

# --- 1. 网页配置 ---
# 建议保持 wide 模式以便展示结果表格，但我们通过 column 控制输入区的宽度
st.set_page_config(page_title="B站数据精准抓取工具", layout="wide", page_icon="📺")

DEFAULT_COOKIE = "在此粘贴你的默认Cookie"

# 初始化搜索状态
if 'clicked' not in st.session_state:
    st.session_state.clicked = False

def click_button():
    st.session_state.clicked = True

# --- 2. 界面展示逻辑 ---

# 建立一个居中的容器
# [1, 2, 1] 表示左右留白各占 1 份，中间内容占 2 份（约占屏幕 50% 宽度）
_, main_col, _ = st.columns([1, 2, 1])

with main_col:
    if not st.session_state.clicked:
        st.title("📺 Bilibili 搜索数据导出助手")
        
        # 简介与警示
        st.markdown("""
        ### 🛠️ 工具简介
        本工具支持 B 站搜索结果自动探测、精准去重及 Excel 原生格式导出。
        """)
        
        with st.expander("📖 查看操作指南 & 风险警示"):
            col_a, col_b = st.columns(2)
            with col_a:
                st.info("""
                **操作步骤：**
                1. 填入 Cookie。
                2. 输入关键词。
                3. 设定爬取上限。
                4. 导出 Excel。
                """)
            with col_b:
                st.warning("""
                **安全提醒：**
                - 请勿泄露 Cookie。
                - 建议使用小号抓取。
                - 仅供内部业务研究。
                """)

        st.divider()

        # 配置中心
        st.header("⚙️ 配置中心")
        
        # Cookie 区：左侧输入，右侧帮助
        c1, c2 = st.columns([2, 1])
        with c1:
            user_cookie = st.text_area("1. 粘贴你的 Cookie (可选)", height=100, placeholder="留空则尝试公共通道...")
        with c2:
            st.markdown("<br>", unsafe_allow_html=True) # 稍微向下对齐
            with st.expander("🔍 获取帮助", expanded=False):
                st.caption("登录B站 -> F12 -> Network -> 找 nav -> Headers -> 复制 Cookie")

        # 搜索设置：并排显示
        col_kw, col_pg = st.columns([2, 1])
        with col_kw:
            keyword = st.text_input("2. 搜索关键词", value="Audrey Hobert")
        with col_pg:
            max_pages = st.number_input("3. 最大爬取页数", min_value=1, max_value=100, value=20)

        st.divider()
        start_btn = st.button("🚀 开始精准抓取", use_container_width=True, on_click=click_button)

# --- 3. 核心爬虫逻辑 (保持不变) ---
def run_bili_spider(kw, limit_pg, ck):
    all_videos = []
    headers = {
        "User-Agent": "Mozilla/5.0",
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

# --- 4. 运行与展示 ---
if st.session_state.clicked:
    # 结果展示区我们不需要那么窄，可以单独定义布局
    # 这里我们不用 main_col，而是直接在 wide 页面显示
    final_ck = user_cookie.strip() if user_cookie.strip() else DEFAULT_COOKIE
    if not final_ck or final_ck == "在此粘贴你的默认Cookie":
        with main_col:
            st.error("❌ 无法开始：请先配置 Cookie")
            if st.button("⬅️ 返回修改"):
                st.session_state.clicked = False
                st.rerun()
    else:
        st.title(f"🔍 正在检索: {keyword}")
        with st.spinner('正在为您筛选最精准的数据...'):
            df_final = run_bili_spider(keyword, max_pages, final_ck)
            
        if not df_final.empty:
            st.success(f"🎊 抓取完成！去重后共获得 {len(df_final)} 条精准结果。")
            st.dataframe(df_final, use_container_width=True)
            
            # 下载与重置按钮并排
            down_col, reset_col = st.columns([3, 1])
            with down_col:
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df_final.to_excel(writer, index=False, sheet_name='B站数据')
                st.download_button(
                    label="📥 下载 Excel 结果文件",
                    data=buffer.getvalue(),
                    file_name=f"B站_{keyword}_导出.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            with reset_col:
                if st.button("🔄 重新搜索", use_container_width=True):
                    st.session_state.clicked = False
                    st.rerun()
        else:
            with main_col:
                st.warning("🧐 未发现匹配结果。")
                if st.button("⬅️ 返回"):
                    st.session_state.clicked = False
                    st.rerun()
