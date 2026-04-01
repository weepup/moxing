import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from PIL import Image, ImageDraw, ImageFont
import io
from datetime import datetime

# --- 1. 核心逻辑引擎 (严格复刻 SPY/QQQ 逻辑) ---
def get_action_logic(trend, risk, style):
    """根据三灯组合，输出原文风格的操作建议"""
    if trend == "UP" and risk == "LOW":
        return "【极度乐观】趋势向上且波动极低。建议：满仓分批买入 QQQ，享受动量溢价。"
    elif trend == "UP" and risk == "HIGH":
        return "【结构性牛市】虽然趋势在，但波动加大。建议：持有 SPY，减仓 QQQ，谨防闪崩。"
    elif trend == "DOWN" and risk == "HIGH":
        return "【风险回避】趋势破位且恐慌蔓延。建议：现金为王，空仓观望，等待跌破后站稳。"
    else:
        return "【震荡磨底】信号不统一。建议：分批低吸标普500，严禁追高纳指。"

@st.cache_data(ttl=3600)
def fetch_and_clean_data():
    tickers = ['SPY', 'QQQ', '^VIX']
    raw_data = yf.download(tickers, period='1y', interval='1d')
    
    # 修复 MultiIndex 问题，直接提取 Close
    data = raw_data['Close'].copy()
    data = data.ffill().dropna() # 填充空值并删除无效行
    
    # 计算指标
    data['SPY_EMA20'] = data['SPY'].ewm(span=20).mean()
    data['QQQ_SPY_Ratio'] = data['QQQ'] / data['SPY']
    return data

# --- 2. 页面交互设计 ---
st.set_page_config(page_title="美股量化信号灯系统", layout="wide")
st.markdown("<h1 style='text-align: center;'>🚥 美股量化信号灯自动化看板</h1>", unsafe_allow_html=True)

try:
    df = fetch_and_clean_data()
    current = df.iloc[-1]
    
    # 指标计算
    is_trend_up = current['SPY'] > current['SPY_EMA20']
    is_risk_low = current['^VIX'] < 20
    is_style_qqq = df['QQQ_SPY_Ratio'].pct_change(5).iloc[-1] > 0
    
    t_signal = "UP" if is_trend_up else "DOWN"
    r_signal = "LOW" if is_risk_low else "HIGH"
    s_signal = "QQQ" if is_style_qqq else "SPY"
    
    action_text = get_action_logic(t_signal, r_signal, s_signal)

    # --- 顶层看板 ---
    cols = st.columns(3)
    cols[0].metric("趋势灯 (Trend)", "看多 (BULL)" if is_trend_up else "看空 (BEAR)", 
                   delta=f"Price: {current['SPY']:.2f}", delta_color="normal" if is_trend_up else "inverse")
    cols[1].metric("风险灯 (Risk)", "安全 (SAFE)" if is_risk_low else "警报 (DANGER)", 
                   delta=f"VIX: {current['^VIX']:.2f}", delta_color="normal" if is_risk_low else "inverse")
    cols[2].metric("风格灯 (Style)", "科技股强 (QQQ)" if is_style_qqq else "标普稳 (SPY)")

    # --- 核心图表 ---
    st.subheader("📈 逻辑可视化验证")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df['SPY'], name='SPY 价格', line=dict(color='#00FFAB', width=2)))
    fig.add_trace(go.Scatter(x=df.index, y=df['SPY_EMA20'], name='EMA20 支撑', line=dict(dash='dash', color='gray')))
    fig.update_layout(template="plotly_dark", height=400, margin=dict(l=20, r=20, t=20, b=20))
    st.plotly_chart(fig, use_container_width=True)

    # --- 小红书海报生成器 (重写绘图引擎) ---
    st.sidebar.header("🎨 小红书海报发布")
    if st.sidebar.button("🎨 渲染今日高清信号海报"):
        # 创建 3:4 画布
        w, h = 1080, 1440
        canvas = Image.new('RGB', (w, h), color='#0F1116')
        draw = ImageDraw.Draw(canvas)
        
        # 1. 绘制顶部色块 (根据信号变色)
        header_color = "#00FFAB" if is_trend_up else "#FF3D68"
        draw.rectangle([0, 0, w, 350], fill=header_color)
        
        # 2. 写入大标题 (这里不依赖外部字体，通过放大比例模拟)
        draw.text((60, 80), "US MARKET", fill="#000000", font_size=90)
        draw.text((60, 180), "SIGNAL LIGHT", fill="#000000", font_size=110)
        
        # 3. 绘制中间数据区
        draw.text((60, 420), f"DATE: {datetime.now().strftime('%Y-%m-%d')}", fill="white", font_size=50)
        
        # 4. 绘制信号卡片 (视觉化)
        def draw_signal_box(y, label, status, val, color):
            draw.rectangle([60, y, w-60, y+180], outline=color, width=3)
            draw.text((100, y+40), label, fill="white", font_size=40)
            draw.text((100, y+100), f"{status} | {val}", fill=color, font_size=55)

        draw_signal_box(550, "TREND SIGNAL", "BULLISH" if is_trend_up else "BEARISH", f"SPY ${current['SPY']:.1f}", "#00FFAB" if is_trend_up else "#FF3D68")
        draw_signal_box(760, "RISK LEVEL", "SAFE" if is_risk_low else "CAUTION", f"VIX {current['^VIX']:.1f}", "#00FFAB" if is_risk_low else "#FFAA00")
        draw_signal_box(970, "INVEST STYLE", "GROWTH" if is_style_qqq else "VALUE", "QQQ/SPY Ratio", "#00A2FF")

        # 5. 底部操作建议 (自动换行逻辑模拟)
        draw.text((60, 1200), "STRATEGY / 建议:", fill="#FFAA00", font_size=45)
        # 简单切分建议文字
        draw.text((60, 1270), action_text[:20], fill="white", font_size=35)
        draw.text((60, 1320), action_text[20:], fill="white", font_size=35)

        # 预览与下载
        st.image(canvas, caption="海报已生成，可直接长按保存或下载", width=450)
        buf = io.BytesIO()
        canvas.save(buf, format="PNG")
        st.sidebar.download_button("📥 下载 4K 原图", buf.getvalue(), file_name="xhs_signal.png")

except Exception as e:
    st.error(f"数据加载失败: {e}")
    st.write("请检查网络环境，或 yfinance 接口暂时不可用。")
