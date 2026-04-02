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

# --- 2. 主页面头部 ---
st.title("📺 Bilibili 搜索数据导出助手")

col_desc, col_warn = st.columns([2, 1])
with col_desc:
    st.markdown("""
    ### 🛠️ 工具简介
    本工具会自动探测 B 站搜索结果的总量，您无需手动确认页数。
    
    ### 📖 操作指南
    1. **填入 Cookie**：在左侧粘贴（或使用默认通道）。
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

# --- 3. 侧边栏：参数输入 ---
with st.sidebar:
    st.header("⚙️ 配置中心")
    user_cookie = st.text_area("1. 粘贴你的 Cookie (可选)", height=100)
    
    with st.expander("🔍 如何获取 Cookie？"):
        st.markdown("登录B站 -> F12 -> 网络 -> 找 nav 请求 -> Headers -> 复制 Cookie。")
        
    st.divider()
    keyword = st.text_input("2. 搜索关键词", value="Audrey Hobert")
    
    # 这里的含义变成了“最大爬取上限”，用户可以放心填一个大数字
    max_pages = st.number_input("3. 最大爬取页数 (搜完自动停止)", min_value=1, max_value=100, value=20)
    
    st.divider()
    start_btn = st.button("🚀 开始精准抓取", use_container_width=True)

# --- 4. 核心爬虫逻辑 (新增自动探测与跳出) ---
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
    
    # 初始化显示
    progress_bar = st.progress(0, text="正在探测数据总量...")

    for p in range(1, limit_pg + 1):
        params = {"search_type": "video", "keyword": search_kw, "page": p}
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            data = resp.json()
            
            # 关键：检查是否有结果
            if data['code'] == 0 and 'result' in data['data'] and data['data']['result']:
                v_list = data['data']['result']
                
                # 第一页时，给用户一个反馈，告诉他一共找到了多少
                if p == 1:
                    total_results = data['data'].get('numResults', '未知')
                    st.toast(f"💡 搜索到约 {total_results} 条相关视频", icon="🔍")

                for v in v_list:
                    title = re.sub(r'<[^>]+>', '', v.get('title', ''))
                    # 精准过滤
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
                # 【核心改进】如果这一页没数据了，说明到底了，直接收工
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

# --- 5. 展示结果 ---
if start_btn:
    final_ck = user_cookie.strip() if user_cookie.strip() else DEFAULT_COOKIE
    if not final_ck or final_ck == "在此粘贴你的默认Cookie":
        st.error("❌ 无法开始：请先配置 Cookie")
    else:
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
        else:
            st.warning("🧐 抓取结束，未发现匹配结果。")
