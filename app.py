import streamlit as st
import pandas as pd
import requests
import time
import random
import io
import re

# --- 1. 网页基础配置 ---
st.set_page_config(page_title="B站数据精准抓取工具", layout="wide", page_icon="📺")

# 💡【核心配置】在这里填入你的默认Cookie（若有）
DEFAULT_COOKIE = "在此粘贴你的默认Cookie"

# --- 2. 主页面头部内容 ---
st.title("📺 Bilibili 搜索数据导出助手")

# 使用 columns 布局让界面更丰富
col_desc, col_warn = st.columns([2, 1])

with col_desc:
    st.markdown("""
    ### 🛠️ 工具简介
    本工具旨在帮助团队成员快速获取 B 站视频搜索数据，支持**精准关键词匹配**、**自动去重**以及**Excel 原生格式导出**。
    
    ### 📖 操作指南
    1. **配置权限**：在左侧边栏填入您的 B 站 Cookie（若不填将尝试公共通道）。
    2. **设置关键词**：输入搜索词，系统会自动执行 `""` 精确搜索。
    3. **开始任务**：点击“开始抓取”，等待进度条完成后即可预览。
    4. **下载结果**：点击下载按钮获取可排序的 Excel 文件。
    """)

with col_warn:
    st.warning("""
    ### ⚠️ Cookie 风险警示
    - **账号安全**：Cookie 相当于您的临时登录密码，请勿泄露。
    - **风控风险**：频繁抓取可能会导致您的 B 站账号触发验证码或短暂限制搜索。
    - **隐私保护**：本工具仅在内存中处理数据，不会在服务器上存储您的任何个人信息。
    """)

st.divider() # 分割线

# --- 3. 侧边栏：参数输入 ---
with st.sidebar:
    st.header("⚙️ 配置中心")
    
    user_cookie = st.text_area("1. 粘贴你的 Cookie (可选)", height=100, placeholder="留空则尝试默认通道...")
    
    # 帮助文档嵌套在侧边栏
    with st.expander("🔍 如何获取 Cookie？"):
        st.markdown("""
        1. 登录 B 站网页版。
        2. 按 **F12** 进入开发者工具。
        3. 选 **网络 (Network)** 标签。
        4. 刷新页面，点第一个 **nav**。
        5. 复制 **Headers** 里的 **Cookie** 字段内容。
        """)
        
    st.divider()
    keyword = st.text_input("2. 搜索关键词", value="Audrey Hobert")
    pages = st.number_input("3. 爬取页数", min_value=1, max_value=50, value=5)
    
    st.divider()
    start_btn = st.button("🚀 开始精准抓取", use_container_width=True)

# --- 4. 核心爬虫逻辑 (保持之前的稳定逻辑) ---
def run_bili_spider(kw, pg, ck):
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

    for p in range(1, pg + 1):
        params = {"search_type": "video", "keyword": search_kw, "page": p}
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            data = resp.json()
            if data['code'] == 0 and 'result' in data['data']:
                for v in data['data']['result']:
                    title = re.sub(r'<[^>]+>', '', v.get('title', ''))
                    bvid = v.get('bvid')
                    
                    # 二次精准匹配
                    core_words = clean_kw.split()
                    if all(word.lower() in title.lower() for word in core_words):
                        all_videos.append({
                            "BVID": bvid, 
                            "标题": title,
                            "播放量": v.get('play'),
                            "弹幕数": v.get('video_review'),
                            "发布日期": time.strftime("%Y-%m-%d", time.localtime(v.get('pubdate'))),
                            "UP主": v.get('author'),
                            "时长": v.get('duration'),
                            "视频链接": f"https://www.bilibili.com/video/{bvid}"
                        })
            else:
                break
        except:
            break
        progress_bar.progress(p / pg, text=f"正在采集第 {p}/{pg} 页数据...")
        time.sleep(random.uniform(0.6, 1.2))
    
    progress_bar.empty()
    
    if not all_videos:
        return pd.DataFrame()

    df = pd.DataFrame(all_videos)
    df.drop_duplicates(subset=['BVID'], keep='first', inplace=True)
    
    # 强制数值转换以支持 Excel 排序
    df['播放量'] = pd.to_numeric(df['播放量'], errors='coerce').fillna(0).astype(int)
    df['弹幕数'] = pd.to_numeric(df['弹幕数'], errors='coerce').fillna(0).astype(int)
    
    df.sort_values(by='播放量', ascending=False, inplace=True)
    df.drop(columns=['BVID'], inplace=True)
    return df

# --- 5. 结果展示区域 ---
if start_btn:
    final_ck = user_cookie.strip() if user_cookie.strip() else DEFAULT_COOKIE
    if not final_ck or final_ck == "在此粘贴你的默认Cookie":
        st.error("❌ 无法开始：未检测到有效 Cookie。请在左侧填入或联系管理员。")
    else:
        with st.spinner('正在搬运并筛选数据中...'):
            df_final = run_bili_spider(keyword, pages, final_ck)
            
        if not df_final.empty:
            st.success(f"🎊 抓取完成！去重后共获得 {len(df_final)} 条精准结果。")
            
            st.subheader("📊 实时数据预览")
            st.dataframe(df_final, use_container_width=True)
            
            # Excel 导出
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df_final.to_excel(writer, index=False, sheet_name='B站搜索数据')
            
            st.download_button(
                label="📥 点击下载 Excel 结果文件",
                data=buffer.getvalue(),
                file_name=f"B站_{keyword}_导出结果.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        else:
            st.warning("🧐 抓取结束，但未发现符合精准关键词的结果。")
