"""
【量纲宪法守护者 V188】五票探针版

运行方式:
    python tools/verify_units.py

集成到 main.py:
    from tools.verify_units import verify_units
    verify_units()  # 启动前调用

【CTO V188升级】：
1. 五票诊断：使用5只不同市值代表性股票验证
2. 白盒可观测：通过Normalizer做归一化验证
3. Fail-Close：区分"无QMT包"和"QMT崩溃"
"""
import sys
import os
import logging

logger = logging.getLogger(__name__)

# 【CTO V188】五票诊断样本：覆盖大盘/中盘/小盘/创业板/科创板
# 【CTO I-2修复】茅台expected_float数量级修正：126亿→12.56亿
PROBE_STOCKS = [
    {'code': '000001.SZ', 'name': '平安银行', 'expected_float': 19_200_000_000, 'type': '大盘银行'},  # 约192亿股
    {'code': '600519.SH', 'name': '贵州茅台', 'expected_float': 1_256_000_000, 'type': '超大盘消费'},  # 约12.56亿股（I-2修复）
    {'code': '002475.SZ', 'name': '立讯精密', 'expected_float': 7_200_000_000, 'type': '中盘科技'},  # 约72亿股
    {'code': '300750.SZ', 'name': '宁德时代', 'expected_float': 4_400_000_000, 'type': '创业板龙头'},  # 约44亿股
    {'code': '688981.SH', 'name': '中芯国际', 'expected_float': 1_900_000_000, 'type': '科创板龙头'},  # 约19亿股
]


def verify_units() -> dict:
    """
    五票探针验证QMT数据源单位
    
    Returns:
        dict: {
            'float_volume_results': list,  # 每只股票的验证结果
            'full_tick_volume_unit': str,
            'passed': bool,
            'errors': list
        }
    """
    # 【CTO I-4】测试环境豁免：CI/CD可通过设置环境变量跳过
    # 生产环境不得设置此变量！
    if os.environ.get('QMT_SKIP_UNIT_VERIFY', '').lower() in ('1', 'true', 'yes'):
        logger.warning("[verify_units] 环境变量 QMT_SKIP_UNIT_VERIFY=1，跳过单位验证（测试环境专用）")
        return {'passed': True, 'errors': [], 'skipped': True, 'float_volume_results': [], 'full_tick_volume_unit': None}
    
    result = {
        'float_volume_results': [],
        'full_tick_volume_unit': None,
        'passed': True,
        'errors': []
    }
    
    # 【Fail-Close】区分"无QMT包"和"QMT崩溃"
    try:
        from xtquant import xtdata
    except ImportError as e:
        # 生产环境ImportError = 真实错误，Fail-Close
        result['errors'].append(f"[致命] 无法导入xtquant: {e}")
        result['errors'].append("生产环境必须安装QMT！测试环境可设置QMT_SKIP_UNIT_VERIFY=1跳过")
        result['passed'] = False
        return result
    
    print("=" * 70)
    print("[量纲宪法守护者 V188] 五票探针开始...")
    print("=" * 70)
    
    # ========== 验证1: FloatVolume 五票探针 ==========
    print("\n[探针1] FloatVolume流通股本单位验证（5只代表性股票）")
    print("-" * 70)
    
    for stock in PROBE_STOCKS:
        code = stock['code']
        name = stock['name']
        expected = stock['expected_float']
        stock_type = stock['type']
        
        try:
            detail = xtdata.get_instrument_detail(code, True)
            if detail is None:
                result['errors'].append(f"{name}({code}): 无法获取instrument_detail")
                result['passed'] = False
                continue
            
            fv_raw = detail.get('FloatVolume', 0)
            if fv_raw is None or fv_raw == 0:
                result['errors'].append(f"{name}({code}): FloatVolume为空或0")
                result['passed'] = False
                continue
            
            # 【V188】使用Normalizer做归一化验证
            from logic.data_providers.qmt_normalizer import QMTNormalizer
            up_price = detail.get('UpStopPrice', 0) or 0
            fv_clean = QMTNormalizer.normalize_float_shares(float(fv_raw), float(up_price))
            
            # 判断单位
            if abs(fv_raw - expected) / expected < 0.2:
                unit = '股'
                status = '✅'
            elif abs(fv_raw * 10000 - expected) / expected < 0.2:
                unit = '万股'
                status = '⚠️ 已升维'
            else:
                unit = '未知'
                status = '❌'
                result['passed'] = False
                result['errors'].append(
                    f"{name}: FloatVolume={fv_raw:,.0f}，预期约{expected:,.0f}股，无法判断单位！"
                )
            
            probe_result = {
                'code': code,
                'name': name,
                'type': stock_type,
                'raw_value': fv_raw,
                'clean_value': fv_clean,
                'expected': expected,
                'unit': unit,
                'status': status
            }
            result['float_volume_results'].append(probe_result)
            
            print(f"  {name:8s} ({stock_type:8s}): raw={fv_raw:>12,.0f} "
                  f"→ clean={fv_clean:>14,.0f} | 预期≈{expected:>12,.0f}股 | {status}")
            
        except Exception as e:
            result['errors'].append(f"{name}({code}): 验证异常 {e}")
            result['passed'] = False
    
    # ========== 验证2: get_full_tick volume 单位 ==========
    print("\n[探针2] get_full_tick成交量单位验证")
    print("-" * 70)
    
    # 只用平安银行做Tick验证
    PINGAN = '000001.SZ'
    try:
        tick = xtdata.get_full_tick([PINGAN])
        if tick is None or PINGAN not in tick:
            result['errors'].append(f"无法获取 {PINGAN} 的 full_tick")
            result['passed'] = False
        else:
            vol_raw = tick[PINGAN].get('volume', 0)
            amt_raw = tick[PINGAN].get('amount', 0)
            price = tick[PINGAN].get('lastPrice', 0)
            
            if price > 0 and vol_raw > 0 and amt_raw > 0:
                # 验证方法：如果 volume 是手，则 amount ≈ volume × price × 100
                estimated_if_hand = vol_raw * price * 100
                estimated_if_share = vol_raw * price
                
                diff_hand = abs(estimated_if_hand - amt_raw) / amt_raw
                diff_share = abs(estimated_if_share - amt_raw) / amt_raw
                
                if diff_hand < diff_share:
                    result['full_tick_volume_unit'] = '手'
                    print(f"  volume单位=手 ✅ (误差{diff_hand:.1%} vs {diff_share:.1%})")
                    print(f"  volume={vol_raw:,.0f}, amount={amt_raw:,.0f}, price={price:.2f}")
                else:
                    result['full_tick_volume_unit'] = '股'
                    result['errors'].append(f"get_full_tick volume单位=股（异常！预期为手）")
                    print(f"  volume单位=股 ⚠️ (误差{diff_share:.1%} vs {diff_hand:.1%})")
            else:
                print(f"  跳过（非交易时间或数据为空）")
    except Exception as e:
        result['errors'].append(f"full_tick验证失败: {e}")
        result['passed'] = False
    
    # ========== 最终结果 ==========
    print("\n" + "=" * 70)
    if result['passed']:
        print("[✅ 验证通过] 量纲宪法守护者检查完毕，系统可启动")
    else:
        print("[❌ 验证失败] 发现以下问题:")
        for err in result['errors']:
            print(f"  - {err}")
        print("\n[致命] 系统禁止启动，请检查QMT数据源！")
    print("=" * 70)
    
    return result


if __name__ == '__main__':
    result = verify_units()
    sys.exit(0 if result['passed'] else 1)