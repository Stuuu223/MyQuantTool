#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
全局版本号配置

Author: iFlow CLI
Version: V20.0.0
"""

# 🚀 全局版本号
VERSION = "V20.0.0"

# 版本信息
VERSION_INFO = {
    "major": 20,
    "minor": 0,
    "patch": 0,
    "full": "V20.0.0",
    "release_date": "2026-03-01",
    "codename": "Pure Blood QMT",
    "description": "CTO数据根基重铸 - 100%纯血QMT本地化"
}

# 版本历史
VERSION_HISTORY = [
    {
        "version": "V20.0.0",
        "release_date": "2026-03-01",
        "codename": "Pure Blood QMT",
        "description": "CTO数据根基重铸 - 100%纯血QMT本地化",
        "changes": [
            "核心重构：粉碎双轨制，删除老旧QMTManager类",
            "安全修复：删除硬编码VIP Token，强制从.env读取",
            "架构净化：清理所有Tushare残留，100%纯血QMT本地化",
            "修复断链：修复unified_downloader.py幽灵引用路径",
            "异步优化：重写Tick下载验证（异步指数退避30秒）",
            "统一标准：死亡换手率统一为70%"
        ]
    },
    {
        "version": "V18.6.1",
        "release_date": "2026-01-19",
        "codename": "Async Refactoring",
        "description": "异步化改造 - 解决致命阻塞隐患",
        "changes": [
            "紧急修复：异步化 DDE 数据获取，使用后台线程避免阻塞主线程",
            "优化 1：增强单位清洗鲁棒性，处理中文单位（亿、万）",
            "优化 2：盘前预计算 MA4，盘中实时计算 MA5（乖离率）",
            "深化迭代：实现 DDE 加速度（Derivative）检测点火信号",
            "UI 集成：将 DDE 加速度和点火信号集成到 V18.6 UI",
            "性能测试：验证非阻塞运行，观察系统是否卡顿"
        ]
    },
    {
        "version": "V18.6",
        "release_date": "2026-01-18",
        "codename": "Full Spectrum Battle Logic",
        "description": "全谱系战斗逻辑 - 从追高到低吸的全面升级",
        "changes": [
            "修复问题 A：在 signal_generator.py 中引入 BUY_MODE 参数",
            "优化 1：在 low_suction_engine.py 中引入价格缓冲区",
            "优化 2：在 utils.py 中增加高精度校准",
            "V18.6 深化迭代：实现'二波预期'、'托单套路'、'国家队护盘指纹'"
        ]
    },
    {
        "version": "V18.5",
        "release_date": "2026-01-17",
        "codename": "Navigator",
        "description": "V18.4 Navigator - 完整旗舰版",
        "changes": [
            "实现全维板块共振系统",
            "实现龙头溯源功能",
            "实现资金热度加权"
        ]
    }
]


def get_version():
    """获取当前版本号"""
    return VERSION


def get_version_info():
    """获取版本信息"""
    return VERSION_INFO


def get_version_history():
    """获取版本历史"""
    return VERSION_HISTORY


def print_version():
    """打印版本信息"""
    print(f"🚀 {VERSION_INFO['full']} - {VERSION_INFO['codename']}")
    print(f"📅 发布日期: {VERSION_INFO['release_date']}")
    print(f"📝 描述: {VERSION_INFO['description']}")
    print(f"🔢 版本号: {VERSION_INFO['major']}.{VERSION_INFO['minor']}.{VERSION_INFO['patch']}")


if __name__ == "__main__":
    print_version()