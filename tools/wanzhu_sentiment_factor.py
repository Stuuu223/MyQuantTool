"""
顽主杯复盘因子生成器
- 每天盘后/盘前运行一次
- 生成情绪因子和个股标签
"""

import json
import pandas as pd
from pathlib import Path
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ================= 配置 =================
PROJECT_ROOT = Path(__file__).resolve().parent.parent
WANZHU_API = 'https://bp3qvsy5v2.coze.site/api/stocks'
SENTIMENT_FILE = PROJECT_ROOT / 'config' / 'market_sentiment.json'
STOCK_TAGS_FILE = PROJECT_ROOT / 'config' / 'stock_wanzhu_tags.json'

def fetch_wanzhu_data():
    """获取顽主杯数据"""
    try:
        import requests
        response = requests.get(WANZHU_API, timeout=10)
        if response.status_code == 200:
            return response.json()
        logger.error(f"获取顽主杯数据失败: HTTP {response.status_code}")
        return None
    except Exception as e:
        logger.error(f"获取顽主杯数据失败: {e}")
        return None

def calculate_sentiment_factor(wanzhu_data):
    """计算市场情绪因子"""
    if not wanzhu_data or 'stocks' not in wanzhu_data:
        return None

    stocks = wanzhu_data['stocks']
    
    # 提取前50名的持仓金额变动
    top_50_changes = []
    for stock in stocks[:50]:
        try:
            amount_change = float(stock.get('amountChange', 0))
            top_50_changes.append(amount_change)
        except:
            pass
    
    # 计算平均变动
    if top_50_changes:
        avg_change = sum(top_50_changes) / len(top_50_changes)
        
        # 情绪评分（-1 到 1）
        # 正数表示赚钱效应，负数表示亏损效应
        sentiment_score = min(max(avg_change / 1000, -1), 1)
        
        return {
            'date': wanzhu_data.get('currentDate', ''),
            'sentiment_score': round(sentiment_score, 3),
            'avg_amount_change': round(avg_change, 2),
            'total_stocks': len(stocks)
        }
    
    return None

def generate_stock_tags(wanzhu_data, active_stocks):
    """
    生成个股标签
    - WZ_HOT: 顽主榜前50重仓股
    - WZ_TRAP: 顽主榜大亏股（持仓金额大幅减少）
    """
    if not wanzhu_data or 'stocks' not in wanzhu_data:
        return {}

    tags = {}
    stocks = wanzhu_data['stocks']
    
    # 构建股票代码映射
    stock_map = {}
    for stock in stocks:
        name = stock['stockName']
        # 通过AkShare获取代码（简化版，这里假设已有代码）
        # 实际应该从wanzhu_top_120.json读取
        stock_map[name] = stock
    
    # 读取顽主杯120只股票代码
    try:
        with open(PROJECT_ROOT / 'config' / 'wanzhu_top_120.json', 'r', encoding='utf-8') as f:
            wanzhu_120 = json.load(f)
        
        # 构建代码到股票信息的映射
        code_to_stock = {s['code']: s for s in wanzhu_120}
        
        # 生成标签
        for stock_info in stocks[:50]:  # 前50名
            code = code_to_stock.get(stock_info['stockName'])
            if code and code in active_stocks:
                try:
                    amount_change = float(stock_info.get('amountChange', 0))
                    
                    if amount_change > 100:  # 持仓增加超过100万
                        tags[code] = 'WZ_HOT'
                    elif amount_change < -100:  # 持仓减少超过100万
                        tags[code] = 'WZ_TRAP'
                except:
                    pass
    except Exception as e:
        logger.warning(f"生成股票标签失败: {e}")
    
    return tags

def generate_sentiment_report():
    """生成情绪复盘报告"""
    logger.info("=" * 60)
    logger.info("📊 生成顽主杯情绪复盘因子")
    logger.info("=" * 60)
    
    # 1. 获取顽主杯数据
    logger.info("\n1️⃣  获取顽主杯数据...")
    wanzhu_data = fetch_wanzhu_data()
    if not wanzhu_data:
        logger.error("❌ 无法获取顽主杯数据")
        return False
    
    logger.info(f"   ✅ 获取成功，当前日期: {wanzhu_data.get('currentDate', '')}")
    logger.info(f"   ✅ 股票数量: {len(wanzhu_data.get('stocks', []))} 只")
    
    # 2. 计算情绪因子
    logger.info("\n2️⃣  计算市场情绪因子...")
    sentiment = calculate_sentiment_factor(wanzhu_data)
    if sentiment:
        logger.info(f"   ✅ 情绪评分: {sentiment['sentiment_score']}")
        logger.info(f"   ✅ 平均金额变动: {sentiment['avg_amount_change']} 万")
        
        # 判断市场情绪
        if sentiment['sentiment_score'] > 0.3:
            mood = "🔥 极热（进攻）"
        elif sentiment['sentiment_score'] > 0:
            mood = "📈 温和（积极）"
        elif sentiment['sentiment_score'] > -0.3:
            mood = "📉 冷淡（谨慎）"
        else:
            mood = "❄️ 冰点（防守）"
        
        logger.info(f"   🎯 市场情绪: {mood}")
        
        # 保存情绪因子
        with open(SENTIMENT_FILE, 'w', encoding='utf-8') as f:
            json.dump(sentiment, f, ensure_ascii=False, indent=2)
        logger.info(f"   ✅ 情绪因子已保存: {SENTIMENT_FILE}")
    
    # 3. 生成个股标签
    logger.info("\n3️⃣  生成个股标签...")
    try:
        with open(PROJECT_ROOT / 'config' / 'active_stocks.json', 'r', encoding='utf-8') as f:
            active_stocks = set(json.load(f))
        
        tags = generate_stock_tags(wanzhu_data, active_stocks)
        
        if tags:
            hot_count = sum(1 for t in tags.values() if t == 'WZ_HOT')
            trap_count = sum(1 for t in tags.values() if t == 'WZ_TRAP')
            
            logger.info(f"   ✅ 标记股票: {len(tags)} 只")
            logger.info(f"   🔥 WZ_HOT: {hot_count} 只")
            logger.info(f"   ⚠️  WZ_TRAP: {trap_count} 只")
            
            # 保存标签
            with open(STOCK_TAGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(tags, f, ensure_ascii=False, indent=2)
            logger.info(f"   ✅ 股票标签已保存: {STOCK_TAGS_FILE}")
        else:
            logger.info("   ℹ️  没有需要标记的股票")
    except Exception as e:
        logger.warning(f"生成个股标签失败: {e}")
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ 顽主杯情绪复盘因子生成完成！")
    logger.info("=" * 60)
    
    return True

if __name__ == "__main__":
    generate_sentiment_report()
