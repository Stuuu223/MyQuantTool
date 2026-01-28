# -*- coding: utf-8 -*-
"""
xtpythonclient 占位符

注意：这是 xtquant 交易接口的底层模块，通常由 QMT 官方提供。
完整的 xtpythonclient 需要从 QMT 安装目录的 bin.x64/Lib/site-packages 中复制。

如果无法获取，QMT 交易接口将无法使用，但不影响数据接口。

Author: iFlow CLI
Date: 2026-01-28
"""


class XtQuantAsyncClient:
    """占位符类"""
    def __init__(self, path, account, session):
        self.path = path
        self.account = account
        self.session = session
        raise NotImplementedError(
            "xtpythonclient 需要从 QMT 官方安装目录获取。\n"
            "请从 QMT 客户端的 bin.x64/Lib/site-packages 复制以下文件到 xtquant 目录：\n"
            "  - IPythonApiClient.py\n"
            "  - xtpythonclient.py\n"
            "或设置 PYTHONPATH 环境变量指向 QMT 安装目录。"
        )


class XtQuantTrader:
    """占位符类"""
    def __init__(self, callback, session):
        self.callback = callback
        self.session = session
        raise NotImplementedError(
            "xtpythonclient 需要从 QMT 官方安装目录获取。\n"
            "请从 QMT 客户端的 bin.x64/Lib/site-packages 复制以下文件到 xtquant 目录。"
        )


class XtQuantTraderCallback:
    """交易回调基类"""
    def on_connected(self):
        pass

    def on_disconnected(self):
        pass

    def on_account_status(self, status):
        pass

    def on_stock_asset(self, asset):
        pass

    def on_stock_order(self, order):
        pass

    def on_stock_trade(self, trade):
        pass

    def on_stock_position(self, position):
        pass

    def on_order_error(self, order_error):
        pass

    def on_cancel_error(self, cancel_error):
        pass

    def on_order_stock_async_response(self, response):
        pass

    def on_smt_appointment_async_response(self, response):
        pass

    def on_cancel_order_stock_async_response(self, response):
        pass