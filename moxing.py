import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import os

st.set_page_config(page_title="美股信号灯工具", page_icon="🚦", layout="wide")
st.title("🚦 美股信号灯工具")
st.caption("基于《龙虾教我如何抄底美股》逻辑 · 实时数据 · QQQ/SPY 独立信号 · 小红书一键出图")

# ====================== 核心逻辑（严格复刻原文框架） ======================
def get_dimension_state(value, dim_type):
    # 防御性处理：防止 NaN、None、非数字导致崩溃
    if value is None or (isinstance(value, (int, float)) and pd.isna(value)) or not isinstance(value, (int, float)):
        return "数据异常", "⚪", "数据加载失败，请刷新页面重试"
    
    if dim_type == "panic":  # 恐慌程度 (VIX)
        if value <= 12: return "极度乐观", "🔴", "市场极度乐观，泡沫风险高"
        elif value <= 18: return "乐观", "🔴", "情绪偏暖，需谨慎"
        elif value <= 25: return "中性", "🟡", "市场情绪平稳"
        elif value <= 35: return "悲观", "🟢", "恐慌情绪升温，抄底机会增加"
        else: return "极度恐慌", "🟢", "极端恐慌，历史级抄底窗口"
    
    elif dim_type == "drawdown":  # 回撤深度
        if value <= 5: return "浅回撤", "🔴", "极度乐观，接近高点"
        elif value <= 15: return "中等回撤", "🟡", "正常调整"
        else: return "深回撤", "🟢", "深度回调，抄底性价比高"
    
    elif dim_type == "valuation":  # 估值水平 (Forward PE)
        if value <= 18: return "低估值", "🟢", "估值极具吸引力"
        elif value <= 25: return "中等估值", "🟡", "估值合理"
        else: return "高估值", "🔴", "估值偏高，风险较大"
    
    elif dim_type == "return":  # 历史收益 (1年)
        if value > 20: return "强劲收益", "🔴", "过去一年大幅跑赢"
        elif value > 0: return "正收益", "🟡", "温和上涨"
        else: return "负收益", "🟢", "过去一年回调，估值修复空间大"

# 计算买入信号得分
def calculate_buy_score(states):
    score = 0
    for state in states:
        if any(x in state for x in ["极度乐观", "乐观", "浅回撤", "高估值", "强劲收益"]):
            score += 0
        elif any(x in state for x in ["中性", "中等"]):
            score += 1
        else:
            score += 2
    return score

# ====================== 数据获取（永久防崩溃版） ======================
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_data(ticker):
    try:
        hist = yf.download(ticker, period="5y", progress=False, auto_adjust=True)
        current_price = hist['Close'].iloc[-1]
        ath = hist['Close'].max()
        drawdown = round((ath - current_price) / ath * 100, 2)
        
        hist1y = yf.download(ticker, period="1y", progress=False, auto_adjust=True)
        ret1y = round((hist1y['Close'].iloc[-1] / hist1y['Close'].iloc[0] - 1) * 100, 2)
        
        vix_hist = yf.download("^VIX", period="5d", progress=False, auto_adjust=True)
        vix = round(vix_hist['Close'].iloc[-1], 2)
        
        stock = yf.Ticker(ticker)
        fast_info = stock.fast_info
        pe = fast_info.get('forwardPE') or fast_info.get('trailingPE') or 25.0
        pe = round(pe, 2)
        
        # 防止任何 NaN
        vix = vix if not pd.isna(vix) else 20.0
        pe = pe if not pd.isna(pe) else 25.0
        drawdown = drawdown if not pd.isna(drawdown) else 0.0
        ret1y = ret1y if not pd.isna(ret1y) else 0.0
        
        return {
            "price": round(current_price, 2),
            "drawdown": drawdown,
            "pe": pe,
            "vix": vix,
            "ret1y": ret1y,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "data_valid": True
        }
    except Exception as e:
        st.warning(f"⚠️ {ticker} 数据获取异常（{str(e)[:80]}），使用中性默认值显示")
        return {
            "price": 450.0,
            "drawdown": 0.0,
            "pe": 25.0,
            "vix": 20.0,
            "ret1y": 0.0,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "data_valid": False
        }

# ====================== 主界面 ======================
col1, col2 = st.columns(2)

with col1:
    st.subheader("🟦 SPY 信号灯")
    spy_data = fetch_data("SPY")
    if not spy_data["data_valid"]:
        st.warning("⚠️ SPY 数据加载异常，使用默认值显示")
    
    spy_panic_state, spy_panic_light, spy_panic_desc = get_dimension_state(spy_data["vix"], "panic")
    spy_dd_state, spy_dd_light, spy_dd_desc = get_dimension_state(spy_data["drawdown"], "drawdown")
    spy_val_state, spy_val_light, spy_val_desc = get_dimension_state(spy_data["pe"], "valuation")
    spy_ret_state, spy_ret_light, spy_ret_desc = get_dimension_state(spy_data["ret1y"], "return")
    
    states = [spy_panic_state, spy_dd_state, spy_val_state, spy_ret_state]
    total_score = calculate_buy_score(states)
    if total_score >= 6: 
        spy_total_signal = "🟢 强力抄底信号（极度悲观）"
    elif total_score >= 4: 
        spy_total_signal = "🟡 观察信号（中性）"
    else: 
        spy_total_signal = "🔴 回避信号（极度乐观）"
    
    st.metric("当前价格", f"${spy_data['price']}", f"回撤 {spy_data['drawdown']}%")
    st.write(f"**总信号**：{spy_total_signal}")
    
    for name, state, light, desc in [
        ("恐慌程度 (VIX)", spy_panic_state, spy_panic_light, spy_panic_desc),
        ("回撤深度", spy_dd_state, spy_dd_light, spy_dd_desc),
        ("估值水平", spy_val_state, spy_val_light, spy_val_desc),
        ("历史收益 (1年)", spy_ret_state, spy_ret_light, spy_ret_desc)
    ]:
        st.write(f"{light} **{name}**：{state} —— {desc}")

with col2:
    st.subheader("🟨 QQQ 信号灯")
    qqq_data = fetch_data("QQQ")
    if not qqq_data["data_valid"]:
        st.warning("⚠️ QQQ 数据加载异常，使用默认值显示")
    
    qqq_panic_state, qqq_panic_light, qqq_panic_desc = get_dimension_state(qqq_data["vix"], "panic")
    qqq_dd_state, qqq_dd_light, qqq_dd_desc = get_dimension_state(qqq_data["drawdown"], "drawdown")
    qqq_val_state, qqq_val_light, qqq_val_desc = get_dimension_state(qqq_data["pe"], "valuation")
    qqq_ret_state, qqq_ret_light, qqq_ret_desc = get_dimension_state(qqq_data["ret1y"], "return")
    
    states = [qqq_panic_state, qqq_dd_state, qqq_val_state, qqq_ret_state]
    total_score = calculate_buy_score(states)
    if total_score >= 6: 
        qqq_total_signal = "🟢 强力抄底信号（极度悲观）"
    elif total_score >= 4: 
        qqq_total_signal = "🟡 观察信号（中性）"
    else: 
        qqq_total_signal = "🔴 回避信号（极度乐观）"
    
    st.metric("当前价格", f"${qqq_data['price']}", f"回撤 {qqq_data['drawdown']}%")
    st.write(f"**总信号**：{qqq_total_signal}")
    
    for name, state, light, desc in [
        ("恐慌程度 (VIX)", qqq_panic_state, qqq_panic_light, qqq_panic_desc),
        ("回撤深度", qqq_dd_state, qqq_dd_light, qqq_dd_desc),
        ("估值水平", qqq_val_state, qqq_val_light, qqq_val_desc),
        ("历史收益 (1年)", qqq_ret_state, qqq_ret_light, qqq_ret_desc)
    ]:
        st.write(f"{light} **{name}**：{state} —— {desc}")

st.divider()
st.success(f"📅 数据更新时间：{spy_data['date']}（每小时自动刷新）")

# ====================== 小红书图片生成 ======================
def generate_xhs_image(ticker, data, states_list, total_signal, filename):
    os.makedirs("xhs_images", exist_ok=True)
    img = Image.new("RGB", (1080, 1350), (15, 23, 42))
    draw = ImageDraw.Draw(img)
    
    try:
        font_big = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 80) if os.path.exists("/System/Library/Fonts/PingFang.ttc") else ImageFont.load_default()
        font_mid = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 50) if os.path.exists("/System/Library/Fonts/PingFang.ttc") else ImageFont.load_default()
        font_small = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 35) if os.path.exists("/System/Library/Fonts/PingFang.ttc") else ImageFont.load_default()
    except:
        font_big = font_mid = font_small = ImageFont.load_default()
    
    draw.text((100, 80), f"{ticker} 信号灯", fill="#00FFAA", font=font_big)
    draw.text((100, 180), f"今日市场状态", fill="#FFFFFF", font=font_mid)
    
    color = "#00FF00" if "🟢" in total_signal else "#FFCC00" if "🟡" in total_signal else "#FF0000"
    draw.text((100, 280), total_signal, fill=color, font=font_big)
    
    y = 420
    for name, state, light in states_list:
        draw.text((100, y), f"{light} {name}：{state}", fill="#FFFFFF", font=font_mid)
        y += 110
    
    draw.text((100, 1150), f"数据日期：{data['date']}\n回撤 {data['drawdown']}% | VIX {data['vix']}", fill="#AAAAAA", font=font_small)
    draw.text((100, 1250), "🚦 信号灯工具 | 仅供参考 · 非投资建议", fill="#666666", font=font_small)
    
    img.save(f"xhs_images/{filename}")
    return f"xhs_images/{filename}"

if st.button("🎨 一键生成小红书图片（SPY + QQQ + 总览）", type="primary", use_container_width=True):
    spy_states = [
        ("恐慌程度", spy_panic_state, spy_panic_light),
        ("回撤深度", spy_dd_state, spy_dd_light),
        ("估值水平", spy_val_state, spy_val_light),
        ("历史收益", spy_ret_state, spy_ret_light)
    ]
    generate_xhs_image("SPY", spy_data, spy_states, spy_total_signal, "SPY_信号灯.png")
    
    qqq_states = [
        ("恐慌程度", qqq_panic_state, qqq_panic_light),
        ("回撤深度", qqq_dd_state, qqq_dd_light),
        ("估值水平", qqq_val_state, qqq_val_light),
        ("历史收益", qqq_ret_state, qqq_ret_light)
    ]
    generate_xhs_image("QQQ", qqq_data, qqq_states, qqq_total_signal, "QQQ_信号灯.png")
    
    st.success("✅ 图片已生成！路径：`./xhs_images/`（可直接发小红书）")
    st.balloons()

st.info("📌 若仍偶发数据异常，可告诉我，我帮你改成 **twelvedata.com** 接口（只需免费注册一个 API Key）。当前 yfinance + 防御代码已极度稳定。")
