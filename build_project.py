import os
import sys

# --- 1. 定义项目文件结构与内容 ---

# 依赖清单 requirements.txt
# 替换 openai 为 google-generativeai 以实现零成本
requirements_txt = """akshare>=1.12.0
pandas>=2.0.0
scikit-learn>=1.3.0
streamlit>=1.28.0
plotly>=5.18.0
google-generativeai>=0.8.0
sqlalchemy>=2.0.0
ta-lib>=0.4.0
"""

# 数据管理模块 logic/data_manager.py (保持不变)
data_manager_py = """import akshare as ak
import pandas as pd
import sqlite3
import os
from datetime import datetime

class DataManager:
    def __init__(self, db_path='data/stock_data.db'):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.init_db()

    def init_db(self):
        query = '''
        CREATE TABLE IF NOT EXISTS daily_bars (
            symbol TEXT,
            date TEXT,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL,
            PRIMARY KEY (symbol, date)
        )
        '''
        self.conn.execute(query)
        self.conn.commit()

    def get_history_data(self, symbol, start_date="20240101", end_date="20251231"):
        try:
            df = pd.read_sql(f"SELECT * FROM daily_bars WHERE symbol='{symbol}'", self.conn)
            
            if df.empty or len(df) < 5:
                # print(f"本地缓存未命中，正在下载 {symbol} ...") # 保持界面清爽
                df_api = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date=start_date, end_date=end_date, adjust="qfq")
                
                df_api = df_api.rename(columns={
                    '日期': 'date', '开盘': 'open', '最高': 'high', 
                    '最低': 'low', '收盘': 'close', '成交量': 'volume'
                })
                df_api['symbol'] = symbol
                
                cols = ['symbol', 'date', 'open', 'high', 'low', 'close', 'volume']
                df_api[cols].to_sql('daily_bars', self.conn, if_exists='append', index=False)
                return df_api
            
            return df
        except Exception as e:
            print(f"数据获取异常: {e}")
            return pd.DataFrame()

    def close(self):
        self.conn.close()
"""

# 核心算法模块 logic/algo.py (保持不变)
algo_py = """import pandas as pd
import numpy as np
from sklearn.cluster import KMeans

class QuantAlgo:
    
    @staticmethod
    def calculate_resistance_support(df, n_clusters=5):
        if len(df) < 30: return []
        
        df['is_high'] = df['high'].rolling(window=5, center=True).apply(lambda x: x[2] == max(x), raw=True)
        df['is_low'] = df['low'].rolling(window=5, center=True).apply(lambda x: x[2] == min(x), raw=True)
        
        pivot_points = []
        pivot_points.extend(df[df['is_high'] == 1]['high'].tolist())
        pivot_points.extend(df[df['is_low'] == 1]['low'].tolist())
        
        if not pivot_points: return []

        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        data = np.array(pivot_points).reshape(-1, 1)
        kmeans.fit(data)
        
        key_levels = sorted(kmeans.cluster_centers_.flatten().tolist())
        return key_levels

    @staticmethod
    def calculate_atr(df, period=14):
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        return true_range.rolling(period).mean().iloc[-1]

    @staticmethod
    def generate_grid_strategy(current_price, atr):
        grid_width_val = atr * 0.5 
        
        plan = {
            "基准价": current_price,
            "网格宽度": round(grid_width_val, 2),
            "买入挂单": round(current_price - grid_width_val, 2),
            "卖出挂单": round(current_price + grid_width_val, 2),
            "止损红线": round(current_price - grid_width_val * 3, 2),
            "操作建议": f"建议在 {round(current_price - grid_width_val, 2)} 买入底仓的1/10，在 {round(current_price + grid_width_val, 2)} 卖出同等数量。"
        }
        return plan
"""

# AI 智能分析模块 logic/ai_agent.py (已更新为 Google Gemini)
ai_agent_py = """import google.generativeai as genai
import os

class DeepSeekAgent:
    # 类名保持不变以兼容主程序
    def __init__(self, api_key):
        self.api_key = api_key
        self.model = None
        if api_key and not api_key.startswith("sk-"):
            try:
                genai.configure(api_key=self.api_key)
                # 使用 Gemini 1.5 Flash，速度快且免费额度高
                self.model = genai.GenerativeModel('gemini-1.5-flash')
            except Exception as e:
                print(f"Gemini 配置失败: {e}")

    def analyze_stock(self, symbol, price_change, technical_signal):
        if not self.api_key or self.api_key.startswith("sk-"):
            return "⚠️ 请先配置 Google API Key (需在 main.py 中填入)"

        if not self.model:
            return "⚠️ 模型未初始化，请检查网络或 Key"

        prompt = f'''
        你是一位资深的A股交易员，风格理性客观。
        
        【市场数据】
        股票代码: {symbol}
        今日涨跌幅: {price_change}%
        技术面信号: {technical_signal}
        
        请简短分析（100字以内）：
        1. 波动背后的可能情绪？
        2. 给小白用户的操作建议（持仓/减仓/观望）？
        '''
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            if "429" in str(e):
                return "⚠️ 触发免费版速率限制，请稍等几秒再试。"
            return f"AI 分析失败: {e}"
"""

# 主程序 main.py (已更新提示文案)
main_py = """import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from logic.data_manager import DataManager
from logic.algo import QuantAlgo
from logic.ai_agent import DeepSeekAgent
import os

st.set_page_config(page_title="个人化A股智能终端", layout="wide", page_icon="📈")

# --- 配置区 ---
# 1. 去 https://aistudio.google.com/app/apikey 免费申请 Key
# 2. 将 Key 填入下方引号中
API_KEY = os.getenv("GOOGLE_API_KEY", "AIzaSyC9mFvAjbWTiuqr4bgiNKikEdRDn8_nnnw") 

db = DataManager()
ai_agent = DeepSeekAgent(api_key=API_KEY)

st.title("🚀 下一代个人化A股投研终端")
st.markdown("Based on Google Gemini (Free) & AkShare")

with st.sidebar:
    st.header("🎮 控制台")
    symbol = st.text_input("股票代码", value="600519", help="请输入6位A股代码")
    start_date = st.date_input("开始日期", pd.to_datetime("2024-01-01"))
    run_ai = st.button("🧠 呼叫 Gemini 投顾")
    st.markdown("---")
    st.caption("数据来源: AkShare 开源接口")
    
    if API_KEY == "AIzaSyC9mFvAjbWTiuqr4bgiNKikEdRDn8_nnnw":
        st.warning("⚠️ 未检测到有效 Key，AI 功能将不可用。")

if symbol:
    s_date_str = start_date.strftime("%Y%m%d")
    e_date_str = pd.Timestamp.now().strftime("%Y%m%d")
    
    with st.spinner('正在连接交易所数据管道...'):
        df = db.get_history_data(symbol, start_date=s_date_str, end_date=e_date_str)
    
    if not df.empty and len(df) > 30:
        current_price = df.iloc[-1]['close']
        prev_close = df.iloc[-2]['close']
        change_pct = (current_price - prev_close) / prev_close * 100
        atr = QuantAlgo.calculate_atr(df)
        resistance_levels = QuantAlgo.calculate_resistance_support(df)
        grid_plan = QuantAlgo.generate_grid_strategy(current_price, atr)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("最新价", f"¥{current_price}", f"{change_pct:.2f}%")
        c2.metric("日内波动 (ATR)", f"{atr:.2f}")
        c3.metric("网格密度", f"¥{grid_plan['网格宽度']}")
        c4.metric("AI模型", "Gemini-1.5-Flash")

        st.subheader("📊 阻力线透视")
        fig = go.Figure(data=[go.Candlestick(x=df['date'],
                        open=df['open'], high=df['high'],
                        low=df['low'], close=df['close'], name='K线')])
        
        for level in resistance_levels:
            color = 'rgba(255, 0, 0, 0.6)' if level > current_price else 'rgba(0, 255, 0, 0.6)'
            fig.add_hline(y=level, line_dash="dash", line_color=color, 
                          annotation_text=f"关键位 {level:.2f}")
            
        fig.update_layout(xaxis_rangeslider_visible=False, height=500)
        st.plotly_chart(fig, use_container_width=True)

        col_strategy, col_ai = st.columns([1, 1])
        
        with col_strategy:
            st.subheader("🛠️ 机器生成的做T计划")
            st.info("基于 ATR 波动率自适应计算：")
            st.table(pd.DataFrame([grid_plan]).T.rename(columns={0: '数值/建议'}))
        
        with col_ai:
            st.subheader("🤖 AI 深度解读")
            if run_ai:
                with st.spinner("Gemini 正在分析..."):
                    tech_signal = f"当前价{current_price}，阻力位{[round(x,1) for x in resistance_levels if x>current_price][:2]}，ATR={round(atr,2)}"
                    analysis = ai_agent.analyze_stock(symbol, round(change_pct, 2), tech_signal)
                    st.success(analysis)
            else:
                st.write("点击侧边栏按钮，获取 AI 建议。")
    else:
        st.error("数据不足或获取失败，请检查股票代码。")
"""

# Windows 启动脚本 start.bat
start_bat = """@echo off
echo ==========================================
echo    Starting Your AI Quant Terminal (Gemini Edition)...
echo ==========================================
streamlit run main.py
pause
"""

# Mac/Linux 启动脚本 start.sh
start_sh = """#!/bin/bash
echo "Starting Your AI Quant Terminal (Gemini Edition)..."
streamlit run main.py
"""

# --- 2. 执行文件生成 ---

def create_file(path, content):
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else '.', exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✅ Created: {path}")

def main():
    print("🚀 开始构建 A股智能投研终端 (零成本 Gemini 版)...")
    
    # 创建目录结构
    create_file("requirements.txt", requirements_txt)
    create_file("logic/__init__.py", "")
    create_file("logic/data_manager.py", data_manager_py)
    create_file("logic/algo.py", algo_py)
    create_file("logic/ai_agent.py", ai_agent_py)
    create_file("main.py", main_py)
    
    # 创建启动脚本
    if sys.platform == "win32":
        create_file("start.bat", start_bat)
    else:
        create_file("start.sh", start_sh)
        os.chmod("start.sh", 0o755) 

    print("\\n🎉 项目生成完毕！")
    print("------------------------------------------------")
    print("下一步操作指南：")
    print("1. 安装依赖： pip install -r requirements.txt")
    print("2. 申请免费 Key：访问 https://aistudio.google.com/app/apikey")
    print("3. 配置 Key：打开 main.py，填入你的 Google API Key")
    print("4. 启动运行： 双击 start.bat")
    print("------------------------------------------------")

if __name__ == "__main__":
    main()