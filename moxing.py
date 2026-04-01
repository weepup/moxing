import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from PIL import Image, ImageDraw, ImageFont
import io
from datetime import datetime

# --- 1. 数据引擎 (解决 MultiIndex 报错) ---
@st.cache_data(ttl=3600)
def get_clean_data():
    # 抓取大盘、科技、波动率、以及代表宽度的标普500成分股站上均线比例(模拟计算)
    tickers = ['SPY', 'QQQ', '^VIX', '^GSPC']
    raw = yf.download(tickers, period='1y', interval='1d')
    # 核心：解包 yfinance 的多层索引
    df = raw['Close'].copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
    
    df = df.ffill().dropna()
    # 计算 EMA20
    df['SPY_EMA20'] = df['SPY'].ewm(span=20).mean()
    # 模拟宽度指标 (Breadth): 真实环境建议接入数据接口，此处用 QQQ/SPY 相对强度模拟
    df['Breadth'] = (df['QQQ'] / df['SPY']).rolling(20).rank(pct=True) * 100
    return df

# --- 2. 视觉设计引擎 (小红书多图生成) ---
def generate_xhs_images(date_str, spy_p, vix_p, signals):
    images = []
    # 风格配置
    bg_color = (15, 15, 15)
    accent_color = (0, 255, 171) # 荧光绿
    warn_color = (255, 61, 104) # 警告红
    
    # 图 1：封面图 (核心信号)
    img1 = Image.new('RGB', (1080, 1440), color=bg_color)
    d = ImageDraw.Draw(img1)
    d.rectangle([40, 40, 1040, 1400], outline=(40, 40, 40), width=4)
    # 标题排版 (由于云端字体限制，模拟大号文字)
    d.text((100, 200), "US MARKET", fill=accent_color)
    d.text((100, 320), "SIGNAL LIGHT", fill=(255, 255, 255))
    d.text((100, 450), f"DATE: {date_str}", fill=(150, 150, 150))
    # 大状态展示
    status = "BULLISH" if signals['trend'] == 'GREEN' else "CAUTION"
    status_color = accent_color if status == "BULLISH" else warn_color
    d.rectangle([100, 600, 980, 850], fill=status_color)
    d.text((350, 680), status, fill=(0, 0, 0))
    images.append(img1)

    # 图 2：指标拆解图 (Dashboard)
    img2 = Image.new('RGB', (1080, 1440), color=bg_color)
    d2 = ImageDraw.Draw(img2)
    d2.text((100, 150), "SIGNAL DETAILS", fill=accent_color)
    # 绘制三盏灯
    y = 400
    for label, sig in [("TREND", signals['trend']), ("RISK", signals['risk']), ("WIDTH", signals['width'])]:
        color = accent_color if sig == 'GREEN' else warn_color
        d2.ellipse([100, y, 180, y+80], fill=color)
        d2.text((220, y+20), f"{label}: {sig}", fill=(255, 255, 255))
        y += 200
    images.append(img2)
    
    return images

# --- 3. 可视化 UI 系统 ---
st.set_page_config(page_title="美股信号灯 Pro", layout="wide")
st.title("🚦 美股量化信号灯系统 (SPY/QQQ 专项)")

try:
    df = get_clean_data()
    curr = df.iloc[-1]
    
    # 信号计算逻辑
    trend = "GREEN" if curr['SPY'] > curr['SPY_EMA20'] else "RED"
    risk = "GREEN" if curr['^VIX'] < 20 else ("YELLOW" if curr['^VIX'] < 25 else "RED")
    width = "GREEN" if curr['Breadth'] > 50 else "RED"
    
    signals = {"trend": trend, "risk": risk, "width": width}

    # 顶部状态栏
    c1, c2, c3 = st.columns(3)
    c1.metric("趋势 (Trend)", trend, delta=f"SPY: ${curr['SPY']:.1f}")
    c2.metric("风险 (Risk)", risk, delta=f"VIX: {curr['^VIX']:.1f}", delta_color="inverse")
    c3.metric("市场宽度 (Width)", f"{curr['Breadth']:.1f}%")

    # 逻辑可视化图表
    st.subheader("📊 逻辑回溯 (Price vs EMA20)")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df['SPY'], name='SPY', line=dict(color='#00FFAB')))
    fig.add_trace(go.Scatter(x=df.index, y=df['SPY_EMA20'], name='EMA20', line=dict(dash='dash', color='gray')))
    fig.update_layout(template="plotly_dark", height=450)
    st.plotly_chart(fig, use_container_width=True)

    # 社交媒体发布模块
    st.sidebar.header("📤 社交媒体导出")
    if st.sidebar.button("生成小红书多图套装"):
        imgs = generate_xhs_images(datetime.now().strftime("%Y/%m/%d"), curr['SPY'], curr['^VIX'], signals)
        
        st.subheader("🖼️ 生成结果预览")
        cols = st.columns(len(imgs))
        for i, img in enumerate(imgs):
            cols[i].image(img, caption=f"Slide {i+1}")
            # 下载按钮
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            st.sidebar.download_button(f"下载图 {i+1}", buf.getvalue(), f"xhs_{i+1}.png", "image/png")

    # 自动化建议区
    st.info(f"💡 **操作建议：** 基于当前信号，市场处于 **{trend}** 趋势。建议仓位：{'80%-100%' if trend=='GREEN' and risk=='GREEN' else '30%-50%（防御）'}")

except Exception as e:
    st.error(f"系统运行错误: {e}")
