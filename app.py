import streamlit as st
import pandas as pd
import requests
import time
import random
import io

# --- 网页基础配置 ---
st.set_page_config(page_title="B站数据精准抓取工具", layout="wide")

# --- 界面头部 ---
st.title("📺 Bilibili 搜索数据导出助手")
st.markdown("""
本工具专为居家办公设计，支持**精准关键词匹配**和**Excel原生格式导出**。
> **使用说明**：
> 1. 在左侧填入你的 **Cookie**（获取方式见下方提示）。
> 2. 输入关键词（如 `Audrey Hobert`），系统会自动进行双引号精确搜索。
> 3. 点击开始，抓取完成后直接在线预览并下载 Excel。
""")

# --- 侧边栏：参数输入 ---
with st.sidebar:
    st.header("⚙️ 配置中心")
    
    # Cookie 输入框（加密显示）
    user_cookie = st.text_area("1. 粘贴你的 Cookie", height=150, help="F12 -> Network -> 找 nav 请求 -> Headers 中的 Cookie")
    
    # 搜索词
    keyword = st.text_input("2. 搜索关键词", value="Audrey Hobert")
    
    # 页数选择
    pages = st.number_input("3. 爬取页数 (建议不超过50)", min_value=1, max_value=100, value=5)
    
    st.divider()
    
    # 开始按钮
    start_btn = st.button("🚀 开始抓取并清洗")
    
    # 简单的教程帮助
    with st.expander("如何获取 Cookie？"):
        st.write("1. 电脑浏览器打开B站并登录")
        st.write("2. 按 F12 键，点击 '网络/Network'")
        st.write("3. 刷新页面，在左侧找到 'nav'")
        st.write("4. 点击 'nav'，在右侧 '标头/Headers' 里找到 Cookie 字段并全选复制")

# --- 核心爬虫与逻辑函数 ---
def run_bili_spider(kw, pg, ck):
    all_videos = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://search.bilibili.com/",
        "Cookie": ck
    }
    
    # 自动处理双引号逻辑：让搜索更精准
    search_kw = f'"{kw}"' if '"' not in kw else kw
    url = "https://api.bilibili.com/x/web-interface/search/type"
    
    # 创建网页进度条
    progress_text = "正在搬运数据，请稍候..."
    my_bar = st.progress(0, text=progress_text)

    for p in range(1, pg + 1):
        params = {
            "search_type": "video",
            "keyword": search_kw,
            "page": p,
            "page_size": 42
        }
        
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            data = resp.json()
            
            if data['code'] == 0 and 'result' in data['data']:
                v_list = data['data']['result']
                for v in v_list:
                    title = v.get('title', '').replace('<em class="keyword">', '').replace('</em>', '')
                    
                    # 强力二次清洗：确保标题里真的含有你要的词，防止B站乱推荐
                    core_words = kw.replace('"', '').split()
                    if all(word.lower() in title.lower() for word in core_words):
                        all_videos.append({
                            "标题": title,
                            "播放量": v.get('play'),
                            "弹幕数": v.get('video_review'),
                            "发布日期": time.strftime("%Y-%m-%d", time.localtime(v.get('pubdate'))),
                            "UP主": v.get('author'),
                            "时长": v.get('duration'),
                            "视频链接": f"https://www.bilibili.com/video/{v.get('bvid')}"
                        })
            else:
                # 如果某一页没数据了，提前跳出循环
                break
        except Exception as e:
            st.error(f"第 {p} 页抓取出现异常: {e}")
            break
            
        # 更新进度条
        my_bar.progress(p / pg, text=f"正在爬取第 {p}/{pg} 页...")
        time.sleep(random.uniform(1, 2)) # 适度休眠
        
    my_bar.empty() # 完成后移除进度条
    return pd.DataFrame(all_videos)

# --- 页面逻辑执行 ---
if start_btn:
    if not user_cookie:
        st.error("⚠️ 错误：检测到 Cookie 为空，请先在左侧配置中心粘贴你的 Cookie。")
    else:
        with st.spinner(f'正在为您精准筛选关于 "{keyword}" 的视频...'):
            df_final = run_bili_spider(keyword, pages, user_cookie)
            
        if not df_final.empty:
            st.success(f"🎊 抓取成功！共找到 {len(df_final)} 条精准匹配的视频。")
            
            # --- 1. 网页预览 ---
            st.subheader("📊 数据预览 (仅展示前100条)")
            st.dataframe(df_final, use_container_width=True)
            
            # --- 2. 导出 Excel ---
            # 使用内存缓冲，不占用服务器硬盘
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_final.to_excel(writer, index=False, sheet_name='B站搜索结果')
            excel_data = output.getvalue()
            
            # --- 3. 下载按钮 ---
            st.download_button(
                label="📥 点击下载精准版 Excel 文件",
                data=excel_data,
                file_name=f"B站数据_{keyword}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("🧐 搜索完成，但没有找到符合条件的精准结果。")
            st.info("建议：1. 检查 Cookie 是否过期；2. 缩短搜索关键词；3. 确认关键词在B站确有相关内容。")