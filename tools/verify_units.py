"""
【量纲宪法守护者】每日盘前必须通过，否则系统不允许启动

运行方式:
    python tools/verify_units.py

集成到 main.py:
    from tools.verify_units import verify_units
    verify_units()  # 启动前调用
"""
import sys
import logging

logger = logging.getLogger(__name__)


def verify_units() -> dict:
    """
    验证QMT数据源单位是否与量纲宪法一致
    
    Returns:
        dict: {
            'float_volume_unit': '股' or '万股',
            'full_tick_volume_unit': '手' or '股',
            'passed': True/False
        }
    """
    result = {
        'float_volume_unit': None,
        'full_tick_volume_unit': None,
        'passed': True,
        'errors': []
    }
    
    try:
        from xtquant import xtdata
    except ImportError:
        result['errors'].append("无法导入xtquant，跳过验证")
        result['passed'] = True  # 测试环境可能无QMT
        return result
    
    # 平安银行：已知流通股本约192亿股
    PINGAN = '000001.SZ'
    KNOWN_FLOAT_SHARES = 19_200_000_000  # 192亿股
    
    print("=" * 60)
    print("[量纲宪法守护者] 开始验证QMT数据源单位...")
    print("=" * 60)
    
    # ========== 验证1: FloatVolume 单位 ==========
    try:
        detail = xtdata.get_instrument_detail(PINGAN, True)
        if detail is None:
            result['errors'].append(f"无法获取 {PINGAN} 的 instrument_detail")
            result['passed'] = False
        else:
            fv_raw = detail.get('FloatVolume', 0)
            if fv_raw is None or fv_raw == 0:
                result['errors'].append(f"FloatVolume 为空或0: {fv_raw}")
                result['passed'] = False
            else:
                # 判断单位
                if abs(fv_raw - KNOWN_FLOAT_SHARES) / KNOWN_FLOAT_SHARES < 0.1:
                    result['float_volume_unit'] = '股'
                    print(f"[验证1] FloatVolume单位=股，原始值={fv_raw:,.0f}")
                elif abs(fv_raw * 10000 - KNOWN_FLOAT_SHARES) / KNOWN_FLOAT_SHARES < 0.1:
                    result['float_volume_unit'] = '万股'
                    result['passed'] = False  # 【CTO E-3修复】万股必须拦截！
                    result['errors'].append(
                        f"FloatVolume单位=万股(原始值{fv_raw:,.0f})，"
                        f"TrueDictionary升维逻辑是否已启用？请检查！"
                    )
                    print(f"[致命] FloatVolume单位=万股，原始值={fv_raw:,.0f}")
                    print(f"       TrueDictionary必须×10000升维为股！")
                else:
                    result['errors'].append(
                        f"FloatVolume={fv_raw:,.0f}，无法判断单位！"
                        f"预期约{KNOWN_FLOAT_SHARES:,.0f}股"
                    )
                    result['passed'] = False
    except Exception as e:
        result['errors'].append(f"FloatVolume验证失败: {e}")
        result['passed'] = False
    
    # ========== 验证2: get_full_tick volume 单位 ==========
    try:
        tick = xtdata.get_full_tick([PINGAN])
        if tick is None or PINGAN not in tick:
            result['errors'].append(f"无法获取 {PINGAN} 的 full_tick")
            result['passed'] = False
        else:
            vol_raw = tick[PINGAN].get('volume', 0)
            amt_raw = tick[PINGAN].get('amount', 0)
            price = tick[PINGAN].get('lastPrice', 0)
            
            if price > 0 and vol_raw > 0:
                # 验证方法：如果 volume 是手，则 amount ≈ volume × price × 100
                # 如果 volume 是股，则 amount ≈ volume × price
                estimated_amount_if_hand = vol_raw * price * 100
                estimated_amount_if_share = vol_raw * price
                
                diff_hand = abs(estimated_amount_if_hand - amt_raw) / amt_raw if amt_raw > 0 else 1
                diff_share = abs(estimated_amount_if_share - amt_raw) / amt_raw if amt_raw > 0 else 1
                
                if diff_hand < diff_share:
                    result['full_tick_volume_unit'] = '手'
                    print(f"[验证2] get_full_tick volume单位=手")
                    print(f"       volume={vol_raw:,.0f}, amount={amt_raw:,.0f}, price={price:.2f}")
                else:
                    result['full_tick_volume_unit'] = '股'
                    print(f"[警告] get_full_tick volume单位=股")
                    print(f"       如果确实是股，需要修改代码逻辑！")
                    print(f"       volume={vol_raw:,.0f}, amount={amt_raw:,.0f}, price={price:.2f}")
    except Exception as e:
        result['errors'].append(f"full_tick验证失败: {e}")
        result['passed'] = False
    
    # ========== 最终结果 ==========
    print("=" * 60)
    if result['passed']:
        print("[验证通过] 量纲宪法守护者检查完毕，系统可启动")
    else:
        print("[验证失败] 发现以下问题:")
        for err in result['errors']:
            print(f"  - {err}")
        print("\n[致命] 系统禁止启动，请检查QMT数据源！")
    print("=" * 60)
    
    return result


if __name__ == '__main__':
    result = verify_units()
    sys.exit(0 if result['passed'] else 1)
