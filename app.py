import streamlit as st
import pandas as pd
import requests
import time
import random
import io
import re

# --- 1. 网页配置 ---
st.set_page_config(page_title="B站数据精准抓取工具", layout="wide", page_icon="📺")

# 💡 开发者预设 Cookie（已保留你的默认值）
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

# --- 3. 核心爬虫逻辑 (已修复缓存报错问题) ---
@st.cache_data(show_spinner=False)  
def run_bili_spider(kw, limit_pg, ck):
    """
    此函数仅负责数据抓取，不包含任何 Streamlit 视觉组件(st.progress, st.toast等)，
    这样可以完美避开 CacheReplayClosureError 错误。
    """
    all_videos = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://search.bilibili.com/",
        "Cookie": ck
    }
    clean_kw = kw.replace('"', '').replace('“', '').replace('”', '')
    search_kw = f'"{clean_kw}"'
    url = "https://api.bilibili.com/x/web-interface/search/type"
    
    for p in range(1, limit_pg + 1):
        params = {"search_type": "video", "keyword": search_kw, "page": p}
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            data = resp.json()
            if data['code'] == 0 and 'result' in data['data'] and data['data']['result']:
                v_list = data['data']['result']
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
                break
        except:
            break
        time.sleep(random.uniform(0.6, 1.2))
    
    if not all_videos: return pd.DataFrame()
    df = pd.DataFrame(all_videos)
    df.drop_duplicates(subset=['BVID'], keep='first', inplace=True)
    df['播放量'] = pd.to_numeric(df['播放量'], errors='coerce').fillna(0).astype(int)
    df['弹幕数'] = pd.to_numeric(df['弹幕数'], errors='coerce').fillna(0).astype(int)
    df.sort_values(by='播放量', ascending=False, inplace=True)
    df.drop(columns=['BVID'], inplace=True)
    return df

# --- 4. 界面布局 ---
# 注入自定义 CSS 以实现“蓝色便签纸”效果和统一标题
st.markdown("""
    <style>
    /* 统一标题样式 */
    .custom-header {
        font-size: 28px !important;
        font-weight: 700 !important;
        color: #1E1E1E;
        margin-bottom: 10px !important;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    /* 蓝色便签纸卡片 */
    .note-card {
        background-color: #E3F2FD;
        border-left: 5px solid #2196F3;
        padding: 20px;
        border-radius: 8px;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.05);
        margin-bottom: 25px;
    }
    .note-card p {
        color: #0D47A1;
        margin-bottom: 5px;
        font-size: 16px;
    }
    </style>
""", unsafe_allow_html=True)

_, main_col, _ = st.columns([1, 2, 1])

with main_col:
    if not st.session_state.clicked:
        st.markdown("<h1 style='text-align: center;'>📺 Bilibili 搜索数据采集工具</h1>", unsafe_allow_html=True)
        
        # A. 工具简介（蓝色便签纸样式）
        st.markdown("""
            <div class="note-card">
                <div style="font-size: 20px; font-weight: bold; color: #0D47A1; margin-bottom: 10px;">🛠️ 工具简介</div>
                <p>这是一个专门帮大家在 B 站“捞数据”的省力工具。</p>
                <p style="font-weight: 500;">✨ 它只找标题里完全符合关键词的视频，自动过滤无关干扰。</p>
            </div>
        """, unsafe_allow_html=True)

        # B. 操作指南
        with st.expander("📖 点击查看：操作指南 & 风险警示"):
            c_guide, c_warn = st.columns([2, 1])
            with c_guide:
                st.markdown("""
                **操作步骤：**
                1. **填入 Cookie**：在下方框内粘贴。只要不点“退出登录”，这个CooKie就可以一直用。
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
        
        # 使用统一字号的配置中心标题
        st.markdown('<div class="section-header">⚙️ 采集配置</div>', unsafe_allow_html=True)
        
        # C. Cookie 输入与教程
        st.session_state.user_cookie = st.text_area(
            "1. 粘贴你的 Cookie (可选)", 
            value=st.session_state.user_cookie,
            height=80, 
            placeholder="留空则尝试公共通道。如搜索失败请填入自己账号的 Cookie。"
        )
        
        with st.expander("🔍 不知道怎么获取 Cookie？点击看保姆级教程"):
            st.markdown("""
            1. **登录**：电脑浏览器打开 B 站并登录。
            2. **检查**：右键 -> 检查 (F12)。
            3. **刷新**：点 **网络 (Network)** -> **刷新 (F5)**。
            4. **复制**：找 **`nav`** 请求，复制 Headers 里的 **`cookie:`** 后面全部内容。
            """)
            
        # D. 搜索参数
        col1, col2 = st.columns([2, 1])
        with col1:
            st.session_state.keyword = st.text_input("2. 搜索关键词", value=st.session_state.keyword)
        with col2:
            st.session_state.max_pages = st.number_input("3. 最大爬取页数", min_value=1, max_value=100, value=st.session_state.max_pages)

        st.divider()
        st.button("🚀 开始精准抓取", use_container_width=True, on_click=click_button)

# 情况 B：搜索结果页面逻辑保持不变...
# 情况 B：搜索结果页面
if st.session_state.clicked:
    # --- 顶部的返回导航 ---
    top_back_col, _ = st.columns([1, 4])
    with top_back_col:
        if st.button("⬅️ 返回重新搜索", use_container_width=True):
            # 这里的逻辑是清除缓存并返回首页，如果不想清除缓存可以注释掉下行
            # st.cache_data.clear() 
            st.session_state.clicked = False
            st.rerun()
    st.divider()

    final_ck = st.session_state.user_cookie.strip() if st.session_state.user_cookie.strip() else DEFAULT_COOKIE
    
    if not final_ck:
        with main_col:
            st.error("❌ 无法开始：未配置有效的 Cookie")
            if st.button("⬅️ 返回修改参数"):
                st.session_state.clicked = False
                st.rerun()
    else:
        st.title(f"🔍 正在检索: {st.session_state.keyword}")
        
        # 将进度条和提示放在主循环外面处理
        placeholder = st.empty()
        with placeholder.container():
            st.info("🔄 正在从 B 站服务器获取精准匹配数据，请稍候...")
            
        # 执行爬虫逻辑
        df_final = run_bili_spider(st.session_state.keyword, st.session_state.max_pages, final_ck)
        placeholder.empty() # 抓取完清空提示
            
        if not df_final.empty:
            st.success(f"🎊 抓取完成！共获得 {len(df_final)} 条结果。")
            st.dataframe(df_final, use_container_width=True)
            
            # --- 下载与重置按钮并排 ---
            d_col, r_col = st.columns([3, 1])
            with d_col:
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df_final.to_excel(writer, index=False, sheet_name='B站数据')
                
                # 由于有了 @st.cache_data，下载时页面刷新会瞬间读取结果，不会触发重复搜索
                st.download_button(
                    label="📥 下载 Excel 结果文件",
                    data=buffer.getvalue(),
                    file_name=f"B站_{st.session_state.keyword}_导出.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            with r_col:
                if st.button("🔄 重新搜索", use_container_width=True):
                    # st.cache_data.clear() # 若需彻底新搜索可取消注释
                    st.session_state.clicked = False
                    st.rerun()
        else:
            with main_col:
                st.warning("🧐 抱歉，未发现匹配结果，请尝试更换关键词。")
                if st.button("⬅️ 返回修改关键词"):
                    st.session_state.clicked = False
                    st.rerun()
