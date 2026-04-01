import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from PIL import Image, ImageDraw, ImageFont
import io

# --- 页面配置 ---
st.set_page_config(page_title="US Market Signal Light", layout="wide")
st.title("🚦 美股量化信号灯系统")
st.markdown("---")

# --- 逻辑引擎：严格复刻原文章 ---
@st.cache_data(ttl=3600)
def fetch_data():
    data = yf.download(['SPY', 'QQQ', '^VIX'], period='1y')
    return data['Close']

df = fetch_data()

# 核心指标计算
spy = df['SPY']
ema20 = spy.ewm(span=20).mean()
vix = df['^VIX'].iloc[-1]
last_price = spy.iloc[-1]

# 信号判断逻辑
trend_signal = "Green" if last_price > ema20.iloc[-1] else "Red"
risk_signal = "Green" if vix < 20 else ("Yellow" if vix < 28 else "Red")
strength_signal = "Green" if (df['QQQ'].pct_change(5).iloc[-1] > df['SPY'].pct_change(5).iloc[-1]) else "Yellow"

# --- 模块一：看板展示 ---
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("趋势灯 (Trend)", "BULLISH" if trend_signal == "Green" else "BEARISH")
    st.info(f"SPY 价格: ${last_price:.2f} | EMA20: ${ema20.iloc[-1]:.2f}")

with col2:
    st.metric("风险灯 (Risk)", "SAFE" if risk_signal == "Green" else "HIGH RISK")
    st.info(f"VIX 指数: {vix:.2f}")

with col3:
    st.metric("强弱灯 (Growth)", "NASDAQ Strong" if strength_signal == "Green" else "SPY Strong")
    st.info("判断依据: QQQ/SPY 5日动量")

# --- 模块二：逻辑可视化 (让你看见) ---
st.subheader("📈 逻辑可视化回溯")
fig = go.Figure()
fig.add_trace(go.Scatter(x=spy.index, y=spy, name='SPY Price'))
fig.add_trace(go.Scatter(x=ema20.index, y=ema20, name='EMA20 (关键生命线)', line=dict(dash='dash')))
fig.update_layout(template="plotly_dark", height=400)
st.plotly_chart(fig, use_container_width=True)

# --- 模块三：社交媒体海报生成 ---
st.sidebar.header("🎨 海报生成器")
if st.sidebar.button("预览并生成今日海报"):
    st.subheader("🖼️ 海报预览 (小红书 3:4 比例)")
    
    # 画布创建
    canvas = Image.new('RGB', (1080, 1440), color=(15, 15, 15))
    draw = ImageDraw.Draw(canvas)
    
    # 简单的视觉模拟 (因为需要系统字体，这里仅作为占位逻辑)
    draw.rectangle([50, 50, 1030, 1390], outline=(0, 255, 171), width=5)
    draw.text((100, 150), "US MARKET SIGNAL", fill=(0, 255, 171)) # 需指定字体路径
    
    # 展示预览
    st.image(canvas, caption="生成的社交媒体卡片", width=400)
    
    # 下载按钮
    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    st.download_button(label="📥 立即下载这张图", data=buf.getvalue(), file_name="market_signal.png", mime="image/png")