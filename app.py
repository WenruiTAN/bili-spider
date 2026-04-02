import streamlit as st
import pandas as pd
import requests
import time
import random
import io
import re

# --- 1. 网页配置 ---
st.set_page_config(page_title="B站数据精准抓取工具", layout="wide", page_icon="📺")

DEFAULT_COOKIE = "在此粘贴你的默认Cookie"

# 初始化搜索状态：如果没点过开始，设为 False
if 'clicked' not in st.session_state:
    st.session_state.clicked = False

def click_button():
    st.session_state.clicked = True

# --- 2. 界面展示逻辑 ---

# 只有在还没点击搜索时，才显示这些复杂的文字说明
if not st.session_state.clicked:
    st.title("📺 Bilibili 搜索数据导出助手")
    
    col_desc, col_warn = st.columns([2, 1])
    with col_desc:
        st.markdown("""
        ### 🛠️ 工具简介
        本工具会自动探测 B 站搜索结果的总量，您无需手动确认页数。
        
        ### 📖 操作指南
        1. **填入 Cookie**：在下方框内粘贴（或使用默认通道）。
        2. **输入关键词**：直接输入艺人或品牌名（如 `Audrey Hobert`）。
        3. **设定上限**：设置一个您愿意等待的最大页数（如 50），程序搜完即止。
        4. **一键导出**：等待去重和清洗完成后下载 Excel。
        """)

    with col_warn:
        st.warning("""
        ### ⚠️ Cookie 风险警示
        - 请妥善保管您的 Cookie，切勿泄露。
        - 建议使用 B 站小号进行高频次抓取。
        - 本工具仅供公司内部业务研究使用。
        """)

    st.divider()

    # 将原本侧边栏的内容全部移到主页面
    st.header("⚙️ 配置中心")
    c1, c2 = st.columns([2, 1])
    with c1:
        user_cookie = st.text_area("1. 粘贴你的 Cookie (可选)", height=100)
    with c2:
        with st.expander("🔍 如何获取 Cookie？", expanded=True):
            st.markdown("登录B站 -> F12 -> 网络 -> 找 nav 请求 -> Headers -> 复制 Cookie。")

    col1, col2 = st.columns(2)
    with col1:
        keyword = st.text_input("2. 搜索关键词", value="Audrey Hobert")
    with col2:
        max_pages = st.number_input("3. 最大爬取页数 (搜完自动停止)", min_value=1, max_value=100, value=20)

    st.divider()
    # 点击按钮时触发 click_button 函数
    start_btn = st.button("🚀 开始精准抓取", use_container_width=True, on_click=click_button)

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
    
    progress_bar = st.progress(0, text="正在探测数据总量...")

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
                st.info(f"📍 已到达 B 站搜索末尾（第 {p-1} 页），正在准备结果...")
                break
        except Exception as e:
            st.error(f"抓取中断: {e}")
            break
        progress_bar.progress(p / limit_pg, text=f"正在采集第 {p} 页数据...")
        time.sleep(random.uniform(0.6, 1.2))
    
    progress_bar.empty()
    
    if not all_videos:
        return pd.DataFrame()

    df = pd.DataFrame(all_videos)
    df.drop_duplicates(subset=['BVID'], keep='first', inplace=True)
    df['播放量'] = pd.to_numeric(df['播放量'], errors='coerce').fillna(0).astype(int)
    df['弹幕数'] = pd.to_numeric(df['弹幕数'], errors='coerce').fillna(0).astype(int)
    df.sort_values(by='播放量', ascending=False, inplace=True)
    df.drop(columns=['BVID'], inplace=True)
    return df

# --- 4. 运行与展示 ---
# 如果点击了搜索按钮，则执行以下逻辑
if st.session_state.clicked:
    final_ck = user_cookie.strip() if user_cookie.strip() else DEFAULT_COOKIE
    if not final_ck or final_ck == "在此粘贴你的默认Cookie":
        st.error("❌ 无法开始：请先配置 Cookie")
        # 如果出错了，允许用户重置状态回来重新输入
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
            # 完成后提供一个“重新搜索”的按钮
            if st.button("🔄 重新搜索"):
                st.session_state.clicked = False
                st.rerun()
        else:
            st.warning("🧐 抓取结束，未发现匹配结果。")
            if st.button("⬅️ 返回"):
                st.session_state.clicked = False
                st.rerun()
