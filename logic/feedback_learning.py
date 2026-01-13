"""
反馈学习机制
记录历史预测准确率，实现模型的自我迭代和优化
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import sqlite3
import json
import os
from dataclasses import dataclass, asdict
from .ml_news_analyzer import MLNewsAnalyzer


@dataclass
class PredictionRecord:
    """预测记录"""
    id: Optional[int]
    timestamp: datetime
    news_title: str
    news_content: str
    news_source: str
    related_stocks: str  # JSON格式存储
    
    # 预测结果
    predicted_sentiment: str
    predicted_confidence: float
    predicted_impact: float
    
    # 实际结果（反馈）
    actual_sentiment: Optional[str]
    actual_impact: Optional[float]
    stock_price_change: Optional[float]  # 股价实际变化百分比
    
    # 评估指标
    is_correct: Optional[bool]
    sentiment_error: Optional[float]
    impact_error: Optional[float]
    
    # 备注
    notes: Optional[str]


class FeedbackDatabase:
    """反馈数据库"""
    
    def __init__(self, db_path: str = "data/feedback_learning.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                news_title TEXT NOT NULL,
                news_content TEXT NOT NULL,
                news_source TEXT NOT NULL,
                related_stocks TEXT,
                
                predicted_sentiment TEXT NOT NULL,
                predicted_confidence REAL NOT NULL,
                predicted_impact REAL NOT NULL,
                
                actual_sentiment TEXT,
                actual_impact REAL,
                stock_price_change REAL,
                
                is_correct INTEGER,
                sentiment_error REAL,
                impact_error REAL,
                
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS model_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_name TEXT NOT NULL,
                version TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                
                sentiment_accuracy REAL,
                sentiment_precision REAL,
                sentiment_recall REAL,
                sentiment_f1 REAL,
                
                impact_mse REAL,
                impact_mae REAL,
                impact_r2 REAL,
                
                total_predictions INTEGER,
                correct_predictions INTEGER,
                
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_prediction(self, record: PredictionRecord) -> int:
        """添加预测记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO predictions (
                timestamp, news_title, news_content, news_source, related_stocks,
                predicted_sentiment, predicted_confidence, predicted_impact,
                actual_sentiment, actual_impact, stock_price_change,
                is_correct, sentiment_error, impact_error, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            record.timestamp.isoformat(),
            record.news_title,
            record.news_content,
            record.news_source,
            json.dumps(record.related_stocks, ensure_ascii=False),
            record.predicted_sentiment,
            record.predicted_confidence,
            record.predicted_impact,
            record.actual_sentiment,
            record.actual_impact,
            record.stock_price_change,
            1 if record.is_correct else 0 if record.is_correct is not None else None,
            record.sentiment_error,
            record.impact_error,
            record.notes
        ))
        
        record_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return record_id
    
    def update_feedback(self, prediction_id: int, actual_sentiment: str = None,
                       actual_impact: float = None, stock_price_change: float = None,
                       notes: str = None):
        """更新反馈信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 计算误差
        sentiment_error = None
        impact_error = None
        is_correct = None
        
        # 获取原始预测
        cursor.execute('SELECT predicted_sentiment, predicted_impact FROM predictions WHERE id = ?', (prediction_id,))
        row = cursor.fetchone()
        
        if row:
            predicted_sentiment, predicted_impact = row
            
            if actual_sentiment:
                is_correct = (predicted_sentiment == actual_sentiment)
                sentiment_error = 0 if is_correct else 1
            
            if actual_impact is not None:
                impact_error = abs(predicted_impact - actual_impact)
        
        # 更新记录
        cursor.execute('''
            UPDATE predictions SET
                actual_sentiment = ?,
                actual_impact = ?,
                stock_price_change = ?,
                is_correct = ?,
                sentiment_error = ?,
                impact_error = ?,
                notes = ?
            WHERE id = ?
        ''', (
            actual_sentiment,
            actual_impact,
            stock_price_change,
            1 if is_correct else 0 if is_correct is not None else None,
            sentiment_error,
            impact_error,
            notes,
            prediction_id
        ))
        
        conn.commit()
        conn.close()
    
    def get_predictions(self, limit: int = 100, with_feedback: bool = False) -> List[Dict]:
        """获取预测记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if with_feedback:
            cursor.execute('''
                SELECT * FROM predictions
                WHERE actual_sentiment IS NOT NULL OR actual_impact IS NOT NULL
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (limit,))
        else:
            cursor.execute('''
                SELECT * FROM predictions
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (limit,))
        
        columns = [description[0] for description in cursor.description]
        rows = cursor.fetchall()
        
        conn.close()
        
        results = []
        for row in rows:
            record = dict(zip(columns, row))
            # 解析JSON
            if record['related_stocks']:
                record['related_stocks'] = json.loads(record['related_stocks'])
            results.append(record)
        
        return results
    
    def calculate_performance_metrics(self, days: int = 30) -> Dict:
        """计算性能指标"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 获取指定天数内的有反馈的记录
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor.execute('''
            SELECT * FROM predictions
            WHERE timestamp >= ? AND actual_sentiment IS NOT NULL
            ORDER BY timestamp DESC
        ''', (cutoff_date,))
        
        columns = [description[0] for description in cursor.description]
        rows = cursor.fetchall()
        
        conn.close()
        
        if not rows:
            return {
                'total_predictions': 0,
                'correct_predictions': 0,
                'accuracy': 0.0,
                'sentiment_distribution': {},
                'avg_impact_error': 0.0
            }
        
        # 计算指标
        total = len(rows)
        correct = 0
        sentiment_counts = {'positive': 0, 'negative': 0, 'neutral': 0}
        impact_errors = []
        
        for row in rows:
            record = dict(zip(columns, row))
            
            if record['is_correct']:
                correct += 1
            
            if record['predicted_sentiment']:
                sentiment_counts[record['predicted_sentiment']] += 1
            
            if record['impact_error'] is not None:
                impact_errors.append(record['impact_error'])
        
        accuracy = correct / total if total > 0 else 0.0
        avg_impact_error = np.mean(impact_errors) if impact_errors else 0.0
        
        return {
            'total_predictions': total,
            'correct_predictions': correct,
            'accuracy': accuracy,
            'sentiment_distribution': sentiment_counts,
            'avg_impact_error': avg_impact_error,
            'period_days': days
        }
    
    def get_training_data(self, min_confidence: float = 0.7) -> pd.DataFrame:
        """获取用于重新训练的数据"""
        conn = sqlite3.connect(self.db_path)
        
        query = '''
            SELECT 
                news_title as title,
                news_content as content,
                news_source as source,
                related_stocks,
                actual_sentiment as sentiment,
                actual_impact as impact_score,
                predicted_confidence
            FROM predictions
            WHERE actual_sentiment IS NOT NULL 
                AND actual_impact IS NOT NULL
                AND predicted_confidence >= ?
            ORDER BY timestamp DESC
        '''
        
        df = pd.read_sql_query(query, conn, params=(min_confidence,))
        conn.close()
        
        # 解析JSON
        if 'related_stocks' in df.columns:
            df['related_stocks'] = df['related_stocks'].apply(
                lambda x: json.loads(x) if x else []
            )
        
        return df
    
    def save_model_performance(self, model_name: str, version: str, metrics: Dict):
        """保存模型性能记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO model_performance (
                model_name, version, timestamp,
                sentiment_accuracy, sentiment_precision, sentiment_recall, sentiment_f1,
                impact_mse, impact_mae, impact_r2,
                total_predictions, correct_predictions, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            model_name,
            version,
            datetime.now().isoformat(),
            metrics.get('sentiment_accuracy'),
            metrics.get('sentiment_precision'),
            metrics.get('sentiment_recall'),
            metrics.get('sentiment_f1'),
            metrics.get('impact_mse'),
            metrics.get('impact_mae'),
            metrics.get('impact_r2'),
            metrics.get('total_predictions'),
            metrics.get('correct_predictions'),
            json.dumps(metrics, ensure_ascii=False)
        ))
        
        conn.commit()
        conn.close()


class FeedbackLearningSystem:
    """反馈学习系统"""
    
    def __init__(self, ml_analyzer: MLNewsAnalyzer, db_path: str = "data/feedback_learning.db"):
        self.ml_analyzer = ml_analyzer
        self.db = FeedbackDatabase(db_path)
        self.retrain_threshold = 50  # 当有50条新反馈数据时重新训练
        self.min_confidence_for_retrain = 0.7
    
    def predict_and_record(self, title: str, content: str, source: str,
                          related_stocks: List[str] = None, notes: str = None) -> Dict:
        """预测并记录结果"""
        # 使用ML模型预测
        prediction = self.ml_analyzer.analyze(title, content, source, related_stocks)
        
        # 创建记录
        record = PredictionRecord(
            id=None,
            timestamp=datetime.now(),
            news_title=title,
            news_content=content,
            news_source=source,
            related_stocks=related_stocks or [],
            predicted_sentiment=prediction.sentiment,
            predicted_confidence=prediction.sentiment_confidence,
            predicted_impact=prediction.impact_score,
            actual_sentiment=None,
            actual_impact=None,
            stock_price_change=None,
            is_correct=None,
            sentiment_error=None,
            impact_error=None,
            notes=notes
        )
        
        # 保存到数据库
        record_id = self.db.add_prediction(record)
        
        return {
            'prediction': prediction,
            'record_id': record_id
        }
    
    def add_feedback(self, record_id: int, actual_sentiment: str = None,
                    actual_impact: float = None, stock_price_change: float = None,
                    notes: str = None):
        """添加反馈"""
        self.db.update_feedback(
            record_id,
            actual_sentiment=actual_sentiment,
            actual_impact=actual_impact,
            stock_price_change=stock_price_change,
            notes=notes
        )
        
        # 检查是否需要重新训练
        self._check_and_retrain()
    
    def get_performance_report(self, days: int = 30) -> Dict:
        """获取性能报告"""
        metrics = self.db.calculate_performance_metrics(days)
        
        report = {
            'period': f'最近{days}天',
            'metrics': metrics,
            'summary': self._generate_summary(metrics)
        }
        
        return report
    
    def _generate_summary(self, metrics: Dict) -> str:
        """生成性能摘要"""
        total = metrics['total_predictions']
        accuracy = metrics['accuracy']
        
        if total == 0:
            return "暂无反馈数据"
        
        if accuracy >= 0.8:
            status = "优秀"
        elif accuracy >= 0.7:
            status = "良好"
        elif accuracy >= 0.6:
            status = "一般"
        else:
            status = "需要改进"
        
        summary = f"在{metrics['period_days']}天内，共处理{total}条预测，准确率为{accuracy:.2%}，状态：{status}"
        
        return summary
    
    def _check_and_retrain(self):
        """检查并重新训练模型"""
        # 获取可用于重新训练的数据
        training_data = self.db.get_training_data(self.min_confidence_for_retrain)
        
        if len(training_data) >= self.retrain_threshold:
            print(f"收集到{len(training_data)}条新反馈数据，开始重新训练模型...")
            
            try:
                # 重新训练模型
                results = self.ml_analyzer.train_models(training_data)
                
                # 保存性能记录
                self.db.save_model_performance(
                    model_name="MLNewsAnalyzer",
                    version=f"v{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    metrics={
                        'sentiment_accuracy': results.get('sentiment_accuracy'),
                        'impact_mse': results.get('impact_mse'),
                        'total_predictions': len(training_data),
                        'correct_predictions': int(len(training_data) * results.get('sentiment_accuracy', 0))
                    }
                )
                
                print("模型重新训练完成！")
                
            except Exception as e:
                print(f"重新训练失败: {str(e)}")
    
    def get_predictions_for_review(self, limit: int = 20) -> List[Dict]:
        """获取需要人工审核的预测（没有反馈的记录）"""
        return self.db.get_predictions(limit, with_feedback=False)
    
    def export_training_data(self, filepath: str = "data/training_data_export.csv"):
        """导出训练数据"""
        df = self.db.get_training_data(min_confidence=0.0)
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        print(f"训练数据已导出到 {filepath}")
        return filepath


# 使用示例
if __name__ == "__main__":
    # 创建ML分析器
    ml_analyzer = MLNewsAnalyzer()
    
    # 创建示例训练数据并训练
    sample_data = ml_analyzer.create_sample_training_data()
    ml_analyzer.train_models(sample_data)
    
    # 创建反馈学习系统
    feedback_system = FeedbackLearningSystem(ml_analyzer)
    
    print("=" * 60)
    print("测试预测和记录...")
    print("=" * 60)
    
    # 测试预测
    result = feedback_system.predict_and_record(
        title="公司业绩大幅增长，股价创新高",
        content="公司发布业绩报告，净利润同比增长80%，股价应声上涨，创下历史新高。",
        source="证券时报",
        related_stocks=["600519"]
    )
    
    print(f"\n预测结果:")
    print(f"情绪: {result['prediction'].sentiment}")
    print(f"置信度: {result['prediction'].sentiment_confidence:.4f}")
    print(f"影响度: {result['prediction'].impact_score:.2f}")
    print(f"记录ID: {result['record_id']}")
    
    print("\n" + "=" * 60)
    print("添加反馈...")
    print("=" * 60)
    
    # 添加反馈
    feedback_system.add_feedback(
        record_id=result['record_id'],
        actual_sentiment="positive",
        actual_impact=85.0,
        stock_price_change=5.2,
        notes="预测准确，股价确实上涨"
    )
    
    print("反馈已添加")
    
    print("\n" + "=" * 60)
    print("获取性能报告...")
    print("=" * 60)
    
    # 获取性能报告
    report = feedback_system.get_performance_report(days=30)
    print(f"\n{report['summary']}")
    print(f"\n详细指标:")
    for key, value in report['metrics'].items():
        print(f"  {key}: {value}")
    
    print("\n" + "=" * 60)
    print("导出训练数据...")
    print("=" * 60)
    
    # 导出训练数据
    feedback_system.export_training_data()