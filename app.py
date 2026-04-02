import streamlit as st
import pandas as pd
import requests
import time
import random
import io
import re

# --- 1. 网页配置 ---
st.set_page_config(page_title="B站数据精准抓取工具", layout="wide", page_icon="📺")

# 💡 开发者预设 Cookie（若有）
DEFAULT_COOKIE = "buvid3=4FFE90A5-DB8E-89DB-3AA7-023812EB92D330991infoc; b_nut=1765379530; _uuid=9AFD3B64-11079-7951-81FC-B105FDCE10DDB447515infoc; buvid4=ABEC55F1-734C-B783-DFEC-4969D35C23A949573-025121023-5yW1q3nj6f5c0VmjaSw8pQ%3D%3D; rpdid=|(k~|YR)R)lk0J'u~YlJ~ml)Y; theme-tip-show=SHOWED; theme-avatar-tip-show=SHOWED; theme-switch-show=SHOWED; hit-dyn-v2=1; fingerprint=4e8509a82836e5445a31ca7fcccc4da8; buvid_fp_plain=undefined; buvid_fp=4e8509a82836e5445a31ca7fcccc4da8; PVID=1; CURRENT_BLACKGAP=0; bp_t_offset_36630361=1183601126017073152; CURRENT_QUALITY=80; share_source_origin=copy_web; CURRENT_FNVAL=2000; bili_ticket=eyJhbGciOiJIUzI1NiIsImtpZCI6InMwMyIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NzUzNzc4MjYsImlhdCI6MTc3NTExODU2NiwicGx0IjotMX0.xcywLCJR5sabt-13Pw7is5dQI3dq48ClJ9_DfDbyDYs; bili_ticket_expires=1775377766; bp_t_offset_503461703=1186617460074217472; SESSDATA=83d9f394%2C1790671343%2Cf884a%2A42CjBk6i1yXOllcacN5NQDB6Wa4NYRePjX7YszFRC0-QApZuV1jdviVZfcvjQtRsZK0YQSVnNrSG5wS0F6R0QweUJ3NTdidDFFQ1U0aFJJbHJlSllkR1VRMW1XVzNiV1p0NHgxa2VQR2lLZDVDbjJNUG5EaTE1WGpvalIzVkNWd2h3TjVTMHdDVVlRIIEC; bili_jct=3f9891a1a2eb711111ee7a08b0489e68; DedeUserID=3706960658565980; DedeUserID__ckMd5=110ca6b208d10335; sid=6r2edjrc; bsource=search_bing; bp_t_offset_3706960658565980=1186643629309952000; home_feed_column=4; browser_resolution=481-828; b_lsid=D2F501BB_19D4E39A067"

# --- 2. 初始化 Session State ---
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
    if not st.session_state.clicked:
        st.title("📺 Bilibili 搜索数据采集工具")
        
        # A. 工具简介（直接展示）
        st.markdown("""
        ### 🛠️ 工具简介
        这是一个专门帮大家在 B 站“捞数据”的省力工具。
        
        它只找标题里完全符合关键词的视频，自动过滤无关干扰。
        """)

        # B. 操作指南（折叠框）
        with st.expander("📖 点击查看：操作指南 & 风险警示"):
            c_guide, c_warn = st.columns([2, 1])
            with c_guide:
                st.markdown("""
                **操作步骤：**
                1. **填入 Cookie**：在下方框内粘贴。只要不点“退出登录”，这个CooKie就可以一直用，下次搜其他关键词时也不用换。
                2. **输入关键词**：输入你想搜的关键词。
                3. **设定上限**：设一个最大爬取页数（建议 20-50）。
                4. **下载结果**：等进度条跑完，点击下载 Excel 即可。
                """)
            with c_warn:
                st.warning("""
                **安全提醒：**
                - 请妥善保管 Cookie。
                - 建议使用 B 站小号。
                - 仅供内部业务研究。
                """)

        st.divider()
        st.header("⚙️ 配置中心")
        
        # C. Cookie 输入与教程（折叠框）
        st.session_state.user_cookie = st.text_area(
            "1. 粘贴你的 Cookie (可选)", 
            value=st.session_state.user_cookie,
            height=80, 
            placeholder="留空则尝试公共通道..."
        )
        
        with st.expander("🔍 不知道怎么拿 Cookie？点击看保姆级教程"):
            st.markdown("""
            1. **登录**：电脑浏览器打开 B 站并登录。
            2. **检查**：在网页空白处**右键 -> 检查** (或按 F12)。
            3. **刷新**：点顶部菜单的 **网络 (Network)**，然后 **刷新页面 (F5)**。
            4. **复制**：在左侧列表找 **`nav`** 点击，右侧找到 **`cookie:`** 后面那一长串文字并全部复制。
            """)
            
        # D. 搜索参数
        col1, col2 = st.columns([2, 1])
        with col1:
            st.session_state.keyword = st.text_input("2. 搜索关键词", value=st.session_state.keyword)
        with col2:
            st.session_state.max_pages = st.number_input("3. 最大爬取页数", min_value=1, max_value=100, value=st.session_state.max_pages)

        st.divider()
        st.button("🚀 开始精准抓取", use_container_width=True, on_click=click_button)

# 情况 B：搜索结果页面
if st.session_state.clicked:
    final_ck = st.session_state.user_cookie.strip() if st.session_state.user_cookie.strip() else DEFAULT_COOKIE
    
    if not final_ck or final_ck == "在此粘贴你的默认Cookie":
        with main_col:
            st.error("❌ 无法开始：请先配置 Cookie")
            if st.button("⬅️ 返回修改"):
                st.session_state.clicked = False
                st.rerun()
    else:
        st.title(f"🔍 正在检索: {st.session_state.keyword}")
        with st.spinner('正在为您筛选最精准的数据...'):
            df_final = run_bili_spider(st.session_state.keyword, st.session_state.max_pages, final_ck)
            
        if not df_final.empty:
            st.success(f"🎊 抓取完成！去重后共获得 {len(df_final)} 条精准结果。")
            st.dataframe(df_final, use_container_width=True)
            
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
