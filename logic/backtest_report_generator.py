"""
回测报告生成器
"""

import pandas as pd
import numpy as np
from typing import Dict, Any
from datetime import datetime
import base64
import io


class BacktestReportGenerator:
    """
    回测报告生成器
    
    生成HTML格式的详细回测报告
    """
    
    def __init__(self):
        """初始化报告生成器"""
        self.template = self._get_html_template()
    
    def generate_report(
        self,
        symbol: str,
        metrics: Dict[str, Any],
        equity_curve: list,
        trades: list,
        params: Dict[str, Any] = None,
        enhanced_metrics: Dict[str, float] = None
    ) -> str:
        """
        生成HTML报告
        
        Args:
            symbol: 股票代码
            metrics: 回测指标
            equity_curve: 净值曲线
            trades: 交易记录
            params: 策略参数
            enhanced_metrics: 增强指标
        
        Returns:
            HTML报告
        """
        # 基础指标
        total_return = metrics.get('total_return', 0)
        annual_return = metrics.get('annual_return', 0)
        sharpe_ratio = metrics.get('sharpe_ratio', 0)
        max_drawdown = metrics.get('max_drawdown', 0)
        win_rate = metrics.get('win_rate', 0)
        profit_factor = metrics.get('profit_factor', 0)
        total_trades = metrics.get('total_trades', 0)
        excess_return = metrics.get('excess_return', 0)
        
        # 增强指标
        sortino_ratio = enhanced_metrics.get('sortino_ratio', 0) if enhanced_metrics else 0
        calmar_ratio = enhanced_metrics.get('calmar_ratio', 0) if enhanced_metrics else 0
        information_ratio = enhanced_metrics.get('information_ratio', 0) if enhanced_metrics else 0
        var_95 = enhanced_metrics.get('var_95', 0) if enhanced_metrics else 0
        max_consecutive_losses = enhanced_metrics.get('max_consecutive_losses', 0) if enhanced_metrics else 0
        recovery_time = enhanced_metrics.get('recovery_time', 0) if enhanced_metrics else 0
        
        # 生成净值曲线图表数据
        equity_chart_data = self._generate_equity_chart(equity_curve)
        
        # 生成交易表格
        trades_table = self._generate_trades_table(trades)
        
        # 生成参数表格
        params_table = self._generate_params_table(params)
        
        # 填充模板
        html = self.template.format(
            symbol=symbol,
            report_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            total_return=f"{total_return:.2%}",
            total_return_color=self._get_color(total_return, threshold=0),
            annual_return=f"{annual_return:.2%}",
            annual_return_color=self._get_color(annual_return, threshold=0.15),
            sharpe_ratio=f"{sharpe_ratio:.4f}",
            sharpe_ratio_color=self._get_color(sharpe_ratio, threshold=1.0),
            max_drawdown=f"{max_drawdown:.2%}",
            max_drawdown_color=self._get_color(max_drawdown, threshold=-0.2, reverse=True),
            win_rate=f"{win_rate:.2%}",
            win_rate_color=self._get_color(win_rate, threshold=0.5),
            profit_factor=f"{profit_factor:.2f}",
            profit_factor_color=self._get_color(profit_factor, threshold=1.0),
            total_trades=total_trades,
            excess_return=f"{excess_return:.2%}",
            excess_return_color=self._get_color(excess_return, threshold=0),
            sortino_ratio=f"{sortino_ratio:.4f}",
            calmar_ratio=f"{calmar_ratio:.4f}",
            information_ratio=f"{information_ratio:.4f}",
            var_95=f"{var_95:.2%}",
            max_consecutive_losses=max_consecutive_losses,
            recovery_time=recovery_time,
            equity_chart_data=equity_chart_data,
            trades_table=trades_table,
            params_table=params_table
        )
        
        return html
    
    def _get_color(self, value: float, threshold: float, reverse: bool = False) -> str:
        """
        获取颜色
        
        Args:
            value: 数值
            threshold: 阈值
            reverse: 是否反向 (越大越差)
        
        Returns:
            颜色代码
        """
        if reverse:
            if value > threshold:
                return "#dc3545"  # 红色
            elif value > threshold * 0.8:
                return "#ffc107"  # 黄色
            else:
                return "#28a745"  # 绿色
        else:
            if value < threshold:
                return "#dc3545"  # 红色
            elif value < threshold * 1.2:
                return "#ffc107"  # 黄色
            else:
                return "#28a745"  # 绿色
    
    def _generate_equity_chart(self, equity_curve: list) -> str:
        """
        生成净值曲线图表
        
        Args:
            equity_curve: 净值曲线数据
        
        Returns:
            图表数据 (JSON)
        """
        import json
        
        data = {
            'labels': list(range(len(equity_curve))),
            'values': equity_curve
        }
        
        return json.dumps(data)
    
    def _generate_trades_table(self, trades: list) -> str:
        """
        生成交易表格
        
        Args:
            trades: 交易记录
        
        Returns:
            HTML表格
        """
        if not trades:
            return "<p>无交易记录</p>"
        
        html = """
        <table class="table table-striped">
            <thead>
                <tr>
                    <th>交易ID</th>
                    <th>股票代码</th>
                    <th>方向</th>
                    <th>数量</th>
                    <th>价格</th>
                    <th>盈亏</th>
                </tr>
            </thead>
            <tbody>
        """
        
        for trade in trades[:100]:  # 最多显示100条
            direction = trade.get('direction', '')
            pnl = trade.get('pnl', 0)
            pnl_color = self._get_color(pnl, 0)
            
            html += f"""
            <tr>
                <td>{trade.get('trade_id', '')}</td>
                <td>{trade.get('symbol', '')}</td>
                <td>{direction}</td>
                <td>{trade.get('quantity', 0)}</td>
                <td>¥{trade.get('price', 0):.2f}</td>
                <td style="color: {pnl_color}">¥{pnl:.2f}</td>
            </tr>
            """
        
        html += "</tbody></table>"
        return html
    
    def _generate_params_table(self, params: Dict[str, Any]) -> str:
        """
        生成参数表格
        
        Args:
            params: 参数字典
        
        Returns:
            HTML表格
        """
        if not params:
            return "<p>无参数信息</p>"
        
        html = """
        <table class="table table-bordered">
            <thead>
                <tr>
                    <th>参数名</th>
                    <th>参数值</th>
                </tr>
            </thead>
            <tbody>
        """
        
        for key, value in params.items():
            html += f"""
            <tr>
                <td>{key}</td>
                <td>{value}</td>
            </tr>
            """
        
        html += "</tbody></table>"
        return html
    
    def _get_html_template(self) -> str:
        """
        获取HTML模板
        
        Returns:
            HTML模板字符串
        """
        return """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>回测报告 - {symbol}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {
            font-family: 'Microsoft YaHei', Arial, sans-serif;
            background-color: #f8f9fa;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px 0;
            margin-bottom: 30px;
        }
        .metric-card {
            background: white;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .metric-value {
            font-size: 2.5em;
            font-weight: bold;
        }
        .metric-label {
            color: #6c757d;
            font-size: 0.9em;
        }
        .section-title {
            color: #495057;
            border-left: 4px solid #667eea;
            padding-left: 15px;
            margin-bottom: 20px;
        }
        .table {
            background: white;
            border-radius: 10px;
            overflow: hidden;
        }
        .footer {
            text-align: center;
            padding: 20px;
            color: #6c757d;
            margin-top: 50px;
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="container">
            <h1>📊 回测报告</h1>
            <p class="mb-0">股票代码: {symbol} | 生成时间: {report_time}</p>
        </div>
    </div>
    
    <div class="container">
        <!-- 核心指标 -->
        <h2 class="section-title">核心指标</h2>
        <div class="row">
            <div class="col-md-3">
                <div class="metric-card">
                    <div class="metric-value" style="color: {total_return_color}">{total_return}</div>
                    <div class="metric-label">总收益率</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="metric-card">
                    <div class="metric-value" style="color: {annual_return_color}">{annual_return}</div>
                    <div class="metric-label">年化收益</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="metric-card">
                    <div class="metric-value" style="color: {sharpe_ratio_color}">{sharpe_ratio}</div>
                    <div class="metric-label">夏普比率</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="metric-card">
                    <div class="metric-value" style="color: {max_drawdown_color}">{max_drawdown}</div>
                    <div class="metric-label">最大回撤</div>
                </div>
            </div>
        </div>
        
        <div class="row">
            <div class="col-md-3">
                <div class="metric-card">
                    <div class="metric-value" style="color: {win_rate_color}">{win_rate}</div>
                    <div class="metric-label">胜率</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="metric-card">
                    <div class="metric-value" style="color: {profit_factor_color}">{profit_factor}</div>
                    <div class="metric-label">盈亏比</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="metric-card">
                    <div class="metric-value">{total_trades}</div>
                    <div class="metric-label">交易次数</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="metric-card">
                    <div class="metric-value" style="color: {excess_return_color}">{excess_return}</div>
                    <div class="metric-label">超额收益</div>
                </div>
            </div>
        </div>
        
        <!-- 增强指标 -->
        <h2 class="section-title">增强指标</h2>
        <div class="row">
            <div class="col-md-4">
                <div class="metric-card">
                    <div class="metric-value">{sortino_ratio}</div>
                    <div class="metric-label">索提诺比率</div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="metric-card">
                    <div class="metric-value">{calmar_ratio}</div>
                    <div class="metric-label">卡玛比率</div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="metric-card">
                    <div class="metric-value">{information_ratio}</div>
                    <div class="metric-label">信息比率</div>
                </div>
            </div>
        </div>
        
        <div class="row">
            <div class="col-md-4">
                <div class="metric-card">
                    <div class="metric-value">{var_95}</div>
                    <div class="metric-label">VaR (95%)</div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="metric-card">
                    <div class="metric-value">{max_consecutive_losses}</div>
                    <div class="metric-label">连续亏损天数</div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="metric-card">
                    <div class="metric-value">{recovery_time}</div>
                    <div class="metric-label">恢复时间 (天)</div>
                </div>
            </div>
        </div>
        
        <!-- 净值曲线 -->
        <h2 class="section-title">净值曲线</h2>
        <div class="metric-card">
            <canvas id="equityChart" height="100"></canvas>
        </div>
        
        <!-- 交易记录 -->
        <h2 class="section-title">交易记录</h2>
        <div class="table-responsive">
            {trades_table}
        </div>
        
        <!-- 策略参数 -->
        <h2 class="section-title">策略参数</h2>
        <div class="table-responsive">
            {params_table}
        </div>
    </div>
    
    <div class="footer">
        <p>Generated by MyQuantTool | {report_time}</p>
    </div>
    
    <script>
        // 净值曲线图表
        const ctx = document.getElementById('equityChart').getContext('2d');
        const chartData = {equity_chart_data};
        
        new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: chartData.labels,
                datasets: [{{
                    label: '净值曲线',
                    data: chartData.values,
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    fill: true,
                    tension: 0.4
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{
                        display: false
                    }}
                }},
                scales: {{
                    x: {{
                        title: {{
                            display: true,
                            text: '交易日'
                        }}
                    }},
                    y: {{
                        title: {{
                            display: true,
                            text: '净值'
                        }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>
        """
    
    def save_report(self, html: str, filename: str):
        """
        保存HTML报告
        
        Args:
            html: HTML内容
            filename: 文件名
        """
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html)