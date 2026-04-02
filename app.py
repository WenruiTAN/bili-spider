import streamlit as st
import pandas as pd
import requests
import time
import random
import io
import re

# --- 1. 网页配置 ---
st.set_page_config(page_title="B站数据抓取工具", layout="wide", page_icon="📺")

# 💡 开发者预设 Cookie
DEFAULT_COOKIE = "在此粘贴你的默认Cookie"

# --- 2. 初始化 Session State (解决 NameError 的关键) ---
if 'clicked' not in st.session_state:
    st.session_state.clicked = False
# 预设输入框的初始值
if 'user_cookie' not in st.session_state:
    st.session_state.user_cookie = ""
if 'keyword' not in st.session_state:
    st.session_state.keyword = "Audrey Hobert"
if 'max_pages' not in st.session_state:
    st.session_state.max_pages = 20

def click_button():
    st.session_state.clicked = True

# --- 3. 核心爬虫逻辑 ---
def run_bili_spider(kw, limit_pg, ck):
    all_videos = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://search.bilibili.com/",
        "Cookie": ck
    }
    clean_kw = kw.replace('"', '').replace('“', '').replace('”', '')
    search_kw = f'"{clean_kw}"'
    url = "https://api.api.bilibili.com/x/web-interface/search/type"
    
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

# 使用 [1, 2, 1] 比例让输入框区域保持适中宽度，不分散
_, main_col, _ = st.columns([1, 2, 1])

with main_col:
    # 情况 A：初始搜索页面（显示完整说明）
    if not st.session_state.clicked:
        st.title("📺 Bilibili 搜索数据导出助手")
        
        # 还原完整的文字说明
        # 还原最通俗易懂的文字说明
        col_desc, col_warn = st.columns([2, 1])
        with col_desc:
            st.markdown("""
            ### 🛠️ 工具简介
            这是一个专门帮大家在 B 站“捞数据”的省力工具。
            
            它只找标题里完全符合关键词的视频，干扰项会被自动过滤。
            
            ### 📖 操作指南
            1. **填入 Cookie**：在下方框内粘贴（下方有获取教程）。
            2. **输入关键词**：直接输入你想搜的名字（如 Audrey Hobert）。
            3. **设定上限**：设一个最大爬取页数（比如 50 页），搜完它会自动停。
            4. **下载结果**：等进度条跑完，点击下载 Excel 即可。
            """)
            
        with col_warn:
            st.warning("""
            ### ⚠️ Cookie 风险警示
            - 请妥善保管您的 Cookie，切勿泄露。
            - 建议使用 B 站小号进行高频次抓取。
            - 本工具仅供公司内部业务研究使用。
            """)

        st.divider()

        st.header("⚙️ 配置中心")
        
        # Cookie 输入区
        st.session_state.user_cookie = st.text_area(
            "1. 粘贴你的 Cookie (可选)", 
            value=st.session_state.user_cookie,
            height=100, 
            placeholder="只要不点 B 站的“退出登录”，这串Cookie就可以一直使用，搜索其他关键词时也不用换。"
        )
        
        with st.expander("🔍 点击查看：超详细的 Cookie 获取教程", expanded=False):
            st.markdown("""
            ### 4步拿走 Cookie：
            1. **登录**：在电脑打开 B 站并登录。
            2. **检查**：在网页空白处**右键 -> 检查** (或按 F12)。
            3. **刷新**：点顶部菜单的 **网络 (Network)**，然后 **刷新页面 (F5)**。
            4. **复制**：在左侧列表找 **`nav`** 点击，右侧找 **`cookie:`** 后面那一长串文字。
            
            ---
            **💡 小贴士**：
            * 如果没看到 `nav`，可以在搜索框输入 `nav` 过滤一下。
            * 复制时记得从 `_uuid=...` 一直拉到最后，全部都要。
            """)
            
        # 搜索参数区
        col1, col2 = st.columns([2, 1])
        with col1:
            st.session_state.keyword = st.text_input("2. 搜索关键词", value=st.session_state.keyword)
        with col2:
            st.session_state.max_pages = st.number_input("3. 最大爬取页数", min_value=1, max_value=100, value=st.session_state.max_pages)

        st.divider()
        st.button("🚀 开始精准抓取", use_container_width=True, on_click=click_button)

# 情况 B：搜索结果页面（隐藏说明，全屏展示结果）
if st.session_state.clicked:
    # 确定最终 Cookie
    final_ck = st.session_state.user_cookie.strip() if st.session_state.user_cookie.strip() else DEFAULT_COOKIE
    
    if not final_ck or final_ck == "在此粘贴你的默认Cookie":
        with main_col:
            st.error("❌ 无法开始：请先配置 Cookie")
            if st.button("⬅️ 返回修改"):
                st.session_state.clicked = False
                st.rerun()
    else:
        # 结果页标题
        st.title(f"🔍 正在检索关键词: {st.session_state.keyword}")
        
        with st.spinner('正在为您筛选最精准的数据...'):
            df_final = run_bili_spider(st.session_state.keyword, st.session_state.max_pages, final_ck)
            
        if not df_final.empty:
            st.success(f"🎊 抓取完成！去重后共获得 {len(df_final)} 条精准结果。")
            
            # 展示数据表格
            st.dataframe(df_final, use_container_width=True)
            
            # 下载与操作按钮
            d_col, r_col = st.columns([3, 1])
            with d_col:
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df_final.to_excel(writer, index=False, sheet_name='B站数据')
                st.download_button(
                    label="📥 下载 Excel 结果文件 (可直接排序)",
                    data=buffer.getvalue(),
                    file_name=f"B站_{st.session_state.keyword}_导出结果.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            with r_col:
                if st.button("🔄 重新搜索", use_container_width=True):
                    st.session_state.clicked = False
                    st.rerun()
        else:
            with main_col:
                st.warning("🧐 抓取结束，但未发现符合精准关键词的结果。")
                if st.button("⬅️ 返回修改"):
                    st.session_state.clicked = False
                    st.rerun()
