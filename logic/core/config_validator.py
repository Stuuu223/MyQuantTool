# -*- coding: utf-8 -*-
"""
配置验证器 - CTO强制: 物理保险栓、环境隔离、资金红线

Author: AI总监
Date: 2026-02-23
Version: 1.0.0
"""
import os
import sys
import logging
from typing import Optional, Tuple, List
from dataclasses import dataclass
from enum import Enum

from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

logger = logging.getLogger(__name__)


class SystemEnv(Enum):
    """系统运行环境"""
    BACKTEST = "BACKTEST"
    PAPER_TRADING = "PAPER_TRADING"
    PRODUCTION = "PRODUCTION"


class TradeMode(Enum):
    """交易模式"""
    SIMULATION = "SIMULATION"
    REAL = "REAL"


@dataclass
class ValidationResult:
    """验证结果"""
    valid: bool
    errors: List[str]
    warnings: List[str]


class ConfigValidator:
    """
    配置验证器 - 系统启动时的强制检查
    
    功能:
    1. 验证环境变量完整性
    2. 强制执行资金上限 (MAX_TRADE_AMOUNT)
    3. 验证交易模式和环境的一致性
    4. 防止配置错误导致实盘风险
    """
    
    # CTO强制红线
    ABSOLUTE_MAX_TRADE_AMOUNT = 50000.0  # 绝对上限5万，超过此值拒绝启动
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self._validated = False
        self._config = {}
    
    def validate_all(self) -> ValidationResult:
        """
        执行完整验证
        
        Returns:
            ValidationResult: 验证结果
        """
        self.errors = []
        self.warnings = []
        
        # 1. 验证系统环境
        self._validate_system_env()
        
        # 2. 验证交易模式
        self._validate_trade_mode()
        
        # 3. 验证资金保险栓
        self._validate_trade_limits()
        
        # 4. 验证数据源配置
        self._validate_data_sources()
        
        # 5. 验证必要配置
        self._validate_required_configs()
        
        self._validated = True
        
        return ValidationResult(
            valid=len(self.errors) == 0,
            errors=self.errors,
            warnings=self.warnings
        )
    
    def _validate_system_env(self):
        """验证系统运行环境"""
        env = os.getenv('SYSTEM_ENV', 'BACKTEST')
        
        try:
            system_env = SystemEnv(env)
            self._config['system_env'] = system_env
            logger.info(f"【ConfigValidator】系统环境: {system_env.value}")
            
            # 警告检查
            if system_env == SystemEnv.PRODUCTION:
                self.warnings.append("⚠️  当前为PRODUCTION实盘环境，请确保所有配置正确！")
                
        except ValueError:
            self.errors.append(f"❌ SYSTEM_ENV '{env}' 无效，必须是 BACKTEST/PAPER_TRADING/PRODUCTION 之一")
    
    def _validate_trade_mode(self):
        """验证交易模式"""
        mode = os.getenv('TRADE_MODE', 'SIMULATION')
        
        try:
            trade_mode = TradeMode(mode)
            self._config['trade_mode'] = trade_mode
            logger.info(f"【ConfigValidator】交易模式: {trade_mode.value}")
            
            # 关键检查: PRODUCTION环境必须是REAL模式才有意义
            system_env = self._config.get('system_env')
            if system_env == SystemEnv.PRODUCTION and trade_mode == TradeMode.SIMULATION:
                self.warnings.append("⚠️  PRODUCTION环境但TRADE_MODE=SIMULATION，这将导致在模拟盘运行！")
            
            # 安全红线: 从SIMULATION切换到REAL需要明确确认
            if trade_mode == TradeMode.REAL:
                self.warnings.append("🚨 TRADE_MODE=REAL，系统将执行真实交易！")
                
                # 检查是否设置了账户ID
                account_id = os.getenv('TRADE_ACCOUNT_ID')
                if not account_id or account_id == 'your_account_id_here':
                    self.errors.append("❌ TRADE_MODE=REAL时必须配置有效的TRADE_ACCOUNT_ID")
                    
        except ValueError:
            self.errors.append(f"❌ TRADE_MODE '{mode}' 无效，必须是 SIMULATION/REAL 之一")
    
    def _validate_trade_limits(self):
        """验证交易限制 - CTO强制物理保险栓"""
        # 1. 验证MAX_TRADE_AMOUNT
        max_amount_str = os.getenv('MAX_TRADE_AMOUNT', '20000.0')
        
        try:
            max_amount = float(max_amount_str)
            
            # 检查是否为正数
            if max_amount <= 0:
                self.errors.append(f"❌ MAX_TRADE_AMOUNT必须大于0，当前值: {max_amount}")
                return
            
            # CTO绝对红线检查: 超过5万拒绝启动
            if max_amount > self.ABSOLUTE_MAX_TRADE_AMOUNT:
                self.errors.append(
                    f"🚫 MAX_TRADE_AMOUNT {max_amount} 超过绝对上限 {self.ABSOLUTE_MAX_TRADE_AMOUNT}！"
                    f"这是CTO设置的红线，防止误操作导致大额亏损。如需调整请联系CTO。"
                )
                return
            
            # 警告: 超过2万提醒
            if max_amount > 20000:
                self.warnings.append(f"⚠️  MAX_TRADE_AMOUNT={max_amount} 超过建议值20000，请注意风险！")
            
            self._config['max_trade_amount'] = max_amount
            logger.info(f"【ConfigValidator】✅ 资金保险栓已设置: MAX_TRADE_AMOUNT={max_amount}")
            
        except ValueError:
            self.errors.append(f"❌ MAX_TRADE_AMOUNT '{max_amount_str}' 不是有效的数字")
        
        # 2. 验证其他风险控制参数
        max_loss = os.getenv('MAX_DAILY_LOSS_RATIO', '0.05')
        try:
            loss_ratio = float(max_loss)
            if loss_ratio > 0.1:
                self.warnings.append(f"⚠️  MAX_DAILY_LOSS_RATIO={loss_ratio} 设置较高，建议不超过0.1")
        except ValueError:
            self.errors.append(f"❌ MAX_DAILY_LOSS_RATIO '{max_loss}' 不是有效的数字")
    
    def _validate_data_sources(self):
        """验证数据源配置 - CTO铁律: 100%纯血QMT本地化"""
        # 检查降级顺序（仅支持QMT）
        fallback_order = os.getenv('DATA_FALLBACK_ORDER', 'QMT_LOCAL')
        valid_sources = {'QMT_VIP', 'QMT_LOCAL'}
        
        sources = [s.strip() for s in fallback_order.split(',')]
        for source in sources:
            if source not in valid_sources:
                self.errors.append(f"❌ DATA_FALLBACK_ORDER中的'{source}'无效，必须是{valid_sources}之一")
        
        # 检查VIP配置（仅PRODUCTION环境需要）
        system_env = self._config.get('system_env')
        if system_env == SystemEnv.PRODUCTION and 'QMT_VIP' in sources:
            vip_token = os.getenv('QMT_VIP_TOKEN')
            if not vip_token or vip_token == 'your_vip_token_here':
                self.errors.append("❌ PRODUCTION环境使用QMT_VIP时必须配置QMT_VIP_TOKEN")
    
    def _validate_required_configs(self):
        """验证必要的配置项"""
        # QMT路径
        qmt_path = os.getenv('QMT_PATH')
        if not qmt_path:
            self.warnings.append("⚠️  QMT_PATH未配置，将使用默认值")
    
    def get_max_trade_amount(self) -> float:
        """获取最大交易金额（强制调用前必须先validate_all）"""
        if not self._validated:
            raise RuntimeError("必须先调用validate_all()才能获取配置")
        return self._config.get('max_trade_amount', 20000.0)
    
    def get_system_env(self) -> SystemEnv:
        """获取系统环境"""
        if not self._validated:
            raise RuntimeError("必须先调用validate_all()才能获取配置")
        return self._config.get('system_env', SystemEnv.BACKTEST)
    
    def get_trade_mode(self) -> TradeMode:
        """获取交易模式"""
        if not self._validated:
            raise RuntimeError("必须先调用validate_all()才能获取配置")
        return self._config.get('trade_mode', TradeMode.SIMULATION)
    
    def is_real_trading(self) -> bool:
        """是否真实交易"""
        if not self._validated:
            raise RuntimeError("必须先调用validate_all()")
        return (self._config.get('trade_mode') == TradeMode.REAL and 
                self._config.get('system_env') == SystemEnv.PRODUCTION)


class TradeGuardian:
    """
    交易守卫 - 在交易执行时强制执行保险栓
    
    功能:
    1. 拦截超过MAX_TRADE_AMOUNT的订单
    2. 检查交易模式是否允许真实下单
    3. 记录所有交易尝试
    """
    
    def __init__(self):
        self.validator = ConfigValidator()
        self._initialized = False
    
    def initialize(self) -> bool:
        """初始化验证器"""
        result = self.validator.validate_all()
        
        if not result.valid:
            logger.error("=" * 60)
            logger.error("【TradeGuardian】❌ 配置验证失败，系统拒绝启动！")
            for error in result.errors:
                logger.error(f"  {error}")
            logger.error("=" * 60)
            return False
        
        if result.warnings:
            logger.warning("【TradeGuardian】⚠️ 配置警告:")
            for warning in result.warnings:
                logger.warning(f"  {warning}")
        
        self._initialized = True
        logger.info("【TradeGuardian】✅ 交易守卫已激活，所有保险栓就位")
        return True
    
    def check_order(self, amount: float, stock_code: str = '') -> Tuple[bool, str]:
        """
        检查订单是否允许执行
        
        Args:
            amount: 订单金额
            stock_code: 股票代码
            
        Returns:
            (是否允许, 拒绝原因)
        """
        if not self._initialized:
            return False, "TradeGuardian未初始化"
        
        # 检查是否在模拟盘模式
        if not self.validator.is_real_trading():
            # 模拟盘允许任何金额，但记录日志
            logger.info(f"【TradeGuardian】📝 模拟盘订单: {stock_code} 金额={amount:.2f}")
            return True, "SIMULATION_MODE"
        
        # 真实交易模式: 强制执行资金上限
        max_amount = self.validator.get_max_trade_amount()
        
        if amount > max_amount:
            error_msg = (
                f"🚫 订单被拒绝！金额 {amount:.2f} 超过保险栓上限 {max_amount:.2f}。"
                f"如需调整限额，请修改.env中的MAX_TRADE_AMOUNT并重启系统。"
            )
            logger.error(f"【TradeGuardian】{error_msg}")
            return False, error_msg
        
        # 检查通过
        logger.info(f"【TradeGuardian】✅ 真实订单通过: {stock_code} 金额={amount:.2f} (上限={max_amount:.2f})")
        return True, "APPROVED"


# 全局实例
guardian = TradeGuardian()


def validate_and_init() -> bool:
    """初始化验证（系统启动时调用）"""
    return guardian.initialize()


def check_trade_permission(amount: float, stock_code: str = '') -> Tuple[bool, str]:
    """检查交易权限（交易执行前调用）"""
    return guardian.check_order(amount, stock_code)


if __name__ == '__main__':
    # 测试
    logging.basicConfig(level=logging.INFO)
    
    success = validate_and_init()
    if success:
        print("\n测试订单检查:")
        result, msg = check_trade_permission(15000, '002969.SZ')
        print(f"  15000元订单: {'✅通过' if result else '❌拒绝'} - {msg}")
        
        result, msg = check_trade_permission(25000, '002969.SZ')
        print(f"  25000元订单: {'✅通过' if result else '❌拒绝'} - {msg}")