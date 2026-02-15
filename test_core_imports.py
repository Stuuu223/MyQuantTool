# -*- coding: utf-8 -*-
import pytest
from pathlib import Path

# Test core modules can be imported
def test_imports():
    modules = [
        'logic.strategies.event_detector',
        'logic.strategies.triple_funnel_scanner',
        'logic.strategies.full_market_scanner',
        'logic.core.rate_limiter',
        'logic.core.failsafe',
        'logic.data_providers.qmt_manager',
        'logic.data_providers.level1_provider',
        'logic.analyzers.trap_detector',
    ]
    
    for module in modules:
        try:
            __import__(module)
        except Exception as e:
            pytest.fail(f'Failed to import {module}: {e}')
