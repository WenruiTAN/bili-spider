import streamlit as st
import pandas as pd
import requests
import time
import random
import io
import re

# --- 网页基础配置 ---
st.set_page_config(page_title="B站精准数据导出工具", layout="wide")
st.title("📺 Bilibili 搜索数据导出助手")
st.markdown("支持**自动去重**、**精准清洗**及**Excel原生格式导出**。")

# 💡【开发者提示】在这里填入你抓好的有效Cookie，小白同事没填时会自动调用它
DEFAULT_COOKIE = "在此粘贴你的Cookie"

# --- 1. 让小白也会获取Cookie (保姆级教程) ---
with st.sidebar:
    st.header("🔑 权限配置")
    user_cookie = st.text_area("粘贴你的 Cookie (可选)", height=100, placeholder="如果不填，将尝试使用内置公共通道...")
    
    with st.expander("❓ 如何获取 Cookie？"):
        st.markdown("""
        1. 在电脑浏览器打开 [Bilibili.com](https://www.bilibili.com) 并登录。
        2. 按下键盘上的 **F12**（或右键点击“检查”）。
        3. 在弹出的窗口顶部点击 **网络 (Network)** 标签。
        4. **刷新一遍页面**，在左侧列表中找到第一个叫 **nav** 的文件。
        5. 点击它，在右侧找到 **Cookie:** 后面那一大串文字，全部复制并贴到上方框内。
        """)
    
    st.divider()
    st.header("🔍 搜索设置")
    keyword = st.text_input("搜索关键词", value="Audrey Hobert")
    pages = st.number_input("爬取页数", min_value=1, max_value=50, value=5)
    
    st.divider()
    start_btn = st.button("🚀 开始精准抓取")

# --- 核心处理逻辑 ---
def run_bili_spider(kw, pg, ck):
    all_videos = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://search.bilibili.com/",
        "Cookie": ck
    }
    
    # 2. “”内关键词精准搜索 (逻辑加固)
    clean_kw = kw.replace('"', '').replace('“', '').replace('”', '')
    search_kw = f'"{clean_kw}"'
    
    url = "https://api.bilibili.com/x/web-interface/search/type"
    my_bar = st.progress(0, text="准备开始...")

    for p in range(1, pg + 1):
        params = {"search_type": "video", "keyword": search_kw, "page": p}
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            data = resp.json()
            if data['code'] == 0 and 'result' in data['data']:
                for v in data['data']['result']:
                    # 清理标题标签
                    title = re.sub(r'<[^>]+>', '', v.get('title', ''))
                    bvid = v.get('bvid')
                    
                    # 二次校验：标题必须同时包含关键词的所有拆分词
                    core_words = clean_kw.split()
                    if all(word.lower() in title.lower() for word in core_words):
                        all_videos.append({
                            "BVID": bvid, 
                            "标题": title,
                            "播放量": v.get('play'), # 此时还是原始数据
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
        my_bar.progress(p / pg, text=f"正在采集第 {p} 页数据...")
        time.sleep(random.uniform(0.6, 1.2))
    
    my_bar.empty()
    
    if not all_videos:
        return pd.DataFrame()

    # --- 3. 去重逻辑 ---
    df = pd.DataFrame(all_videos)
    df.drop_duplicates(subset=['BVID'], keep='first', inplace=True)

    # --- 5. 格式转换 (让Excel能排序的关键) ---
    # 强制将播放量等列转为数字类型，否则Excel会当成文本
    df['播放量'] = pd.to_numeric(df['播放量'], errors='coerce').fillna(0).astype(int)
    df['弹幕数'] = pd.to_numeric(df['弹幕数'], errors='coerce').fillna(0).astype(int)
    
    # 默认按播放量降序
    df.sort_values(by='播放量', ascending=False, inplace=True)
    df.drop(columns=['BVID'], inplace=True)
    
    return df

# --- 4. 网页预览与下载 ---
if start_btn:
    final_ck = user_cookie.strip() if user_cookie.strip() else DEFAULT_COOKIE
    if not final_ck or final_ck == "在此粘贴你的Cookie":
        st.error("❌ 请先配置 Cookie (手动粘贴或联系管理员配置默认值)")
    else:
        with st.spinner('正在为您筛选最精准的数据...'):
            df_final = run_bili_spider(keyword, pages, final_ck)
            
        if not df_final.empty:
            st.success(f"🎊 抓取完成！去重后共 {len(df_final)} 条结果。")
            
            # 网页预览表格
            st.subheader("📊 数据实时预览")
            st.dataframe(df_final, use_container_width=True)
            
            # 导出 Excel (真正的 .xlsx 格式)
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df_final.to_excel(writer, index=False, sheet_name='B站精准抓取')
            
            st.download_button(
                label="📥 下载可排序的 Excel 文件",
                data=buffer.getvalue(),
                file_name=f"B站_{keyword}_精准版.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("🧐 未找到匹配内容。请检查：1.Cookie是否失效 2.关键词是否太冷门")
