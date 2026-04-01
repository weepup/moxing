import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import io
from datetime import datetime

st.set_page_config(page_title="美股量化看板 Pro", layout="wide")

# --- 1. 深度量化数据引擎 ---
@st.cache_data(ttl=3600)
def fetch_deep_quant_data():
    # 抓取 SPY, QQQ, VIX (过去5年数据用于计算历史分位数和历史波动率)
    raw_data = yf.download(['SPY', 'QQQ', '^VIX'], period='5y', interval='1d')['Close']
    
    if isinstance(raw_data.columns, pd.MultiIndex):
        raw_data.columns = raw_data.columns.droplevel(1)
    df = raw_data.ffill().dropna()

    # 获取基本面数据 (容错处理，防止 yf 断联)
    try:
        spy_info = yf.Ticker("SPY").info
        pe_ratio = spy_info.get("trailingPE", 26.5)
        pb_ratio = spy_info.get("priceToBook", 4.2)
    except:
        pe_ratio, pb_ratio = 26.5, 4.2 # 默认备用值

    current_spy = df['SPY'].iloc[-1]
    
    # 【估值分析】计算
    # 价格历史分位数 (过去5年)
    price_percentile = (df['SPY'].rank(pct=True).iloc[-1]) * 100
    # 巴菲特指标简易模拟 (美股总市值/美国GDP，此处用硬编码基准线+SPY涨幅做偏离度模拟，真实环境需接入FRED宏观数据)
    buffett_indicator = 185.0 * (current_spy / 400) # 假设400点对应185%

    # 【情绪指标】计算
    current_vix = df['^VIX'].iloc[-1]
    # 历史波动率 (过去1年的VIX均值)
    hist_vix = df['^VIX'].tail(252).mean()
    volatility_ratio = current_vix / hist_vix

    return {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "price": current_spy,
        "pe": pe_ratio,
        "pb": pb_ratio,
        "percentile": price_percentile,
        "buffett": buffett_indicator,
        "vix": current_vix,
        "hist_vix": hist_vix,
        "vol_ratio": volatility_ratio
    }

# --- 2. 页面UI展示 ---
st.title("📊 美股全景量化与内容生成系统")

try:
    with st.spinner("正在抓取核心宏观与基本面数据..."):
        metrics = fetch_deep_quant_data()

    st.markdown("### 🔍 第一维：估值分析 (Valuation)")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("标普当前 PE", f"{metrics['pe']:.2f}")
    c2.metric("标普当前 PB", f"{metrics['pb']:.2f}")
    c3.metric("5年价格分位数", f"{metrics['percentile']:.1f}%", "极度高估" if metrics['percentile'] > 90 else "合理")
    c4.metric("巴菲特指标 (估算)", f"{metrics['buffett']:.1f}%", "警戒线 > 150%")

    st.markdown("### 🧠 第二维：情绪指标 (Sentiment)")
    e1, e2, e3 = st.columns(3)
    e1.metric("VIX 恐慌指数", f"{metrics['vix']:.2f}")
    e2.metric("历史平均波动 (1年)", f"{metrics['hist_vix']:.2f}")
    e3.metric("短期/历史 波动比", f"{metrics['vol_ratio']:.2f}x", 
              "恐慌蔓延" if metrics['vol_ratio'] > 1.2 else "情绪稳定", delta_color="inverse")

    st.markdown("---")
    
    # --- 3. 小红书排版与制图引擎 (Pillow) ---
    st.sidebar.title("🎨 社交媒体矩阵")
    st.sidebar.write("数据已就绪，一键生成小红书 3:4 排版海报。")

    if st.sidebar.button("📸 生成今日小红书分析图"):
        # 创建 1080x1440 画布 (小红书标准比例)
        img = Image.new('RGB', (1080, 1440), color='#0E1117')
        draw = ImageDraw.Draw(img)
        
        # 尽量使用默认字体，避免系统找不到字体报错
        try:
            # 如果本地有更好的字体，可以将路径替换为 "msyh.ttc" (微软雅黑) 等
            font_title = ImageFont.truetype("arial.ttf", 70)
            font_subtitle = ImageFont.truetype("arial.ttf", 45)
            font_data = ImageFont.truetype("arialbd.ttf", 65)
            font_small = ImageFont.truetype("arial.ttf", 35)
        except:
            font_title = font_subtitle = font_data = font_small = ImageFont.load_default()

        # 1. 顶部视觉区
        draw.rectangle([0, 0, 1080, 250], fill='#00FFAB' if metrics['vol_ratio'] < 1 else '#FF3D68')
        draw.text((80, 70), "US MARKET DAILY", fill='black', font=font_title)
        draw.text((80, 160), f"DATE: {metrics['date']}", fill='black', font=font_subtitle)

        # 2. 估值数据区 (Valuation)
        draw.text((80, 320), "VALUATION / 估值分析", fill='#00FFAB', font=font_subtitle)
        draw.line([(80, 380), (1000, 380)], fill='#333333', width=3)
        
        draw.text((80, 430), "S&P 500 P/E Ratio:", fill='white', font=font_small)
        draw.text((550, 410), f"{metrics['pe']:.2f}", fill='white', font=font_data)
        
        draw.text((80, 530), "Price Percentile (5Y):", fill='white', font=font_small)
        draw.text((550, 510), f"{metrics['percentile']:.1f}%", fill='#FFD700', font=font_data)
        
        draw.text((80, 630), "Buffett Indicator:", fill='white', font=font_small)
        draw.text((550, 610), f"{metrics['buffett']:.1f}%", fill='#FF3D68' if metrics['buffett'] > 150 else 'white', font=font_data)

        # 3. 情绪数据区 (Sentiment)
        draw.text((80, 800), "SENTIMENT / 情绪指标", fill='#00FFAB', font=font_subtitle)
        draw.line([(80, 860), (1000, 860)], fill='#333333', width=3)

        draw.text((80, 910), "Current VIX:", fill='white', font=font_small)
        draw.text((550, 890), f"{metrics['vix']:.2f}", fill='white', font=font_data)
        
        draw.text((80, 1010), "Historical Volatility:", fill='white', font=font_small)
        draw.text((550, 990), f"{metrics['hist_vix']:.2f}", fill='white', font=font_data)
        
        draw.text((80, 1110), "Short vs Hist Ratio:", fill='white', font=font_small)
        draw.text((550, 1090), f"{metrics['vol_ratio']:.2f}x", fill='#FF3D68' if metrics['vol_ratio'] > 1.2 else '#00FFAB', font=font_data)

        # 4. 底部结论区
        action = "High Risk. Consider hedging." if metrics['percentile'] > 90 and metrics['vol_ratio'] > 1.1 else "Market is stable. Hold positions."
        draw.rectangle([80, 1250, 1000, 1380], fill='#1D2129')
        draw.text((120, 1300), f"CONCLUSION: {action}", fill='white', font=font_small)

        # 展示预览图
        st.sidebar.image(img, caption="✅ 海报已生成", use_container_width=True)
        
        # 转换为字节流供下载
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        st.sidebar.download_button(
            label="📥 下载图片 (发布小红书)",
            data=buf.getvalue(),
            file_name=f"market_report_{metrics['date']}.png",
            mime="image/png",
            use_container_width=True
        )

except Exception as e:
    st.error(f"网络请求或计算出错，请重试。详情: {e}")
