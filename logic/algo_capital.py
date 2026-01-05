"""
娓歌祫甯綅鍒嗘瀽妯″潡
鍒嗘瀽榫欒檸姒滄父璧勩€佽拷韪搷浣滄ā寮忋€佽瘑鍒煡鍚嶆父锟?"""

import pandas as pd
from logic.data_manager import DataManager


class CapitalAnalyzer:
    """娓歌祫甯綅鍒嗘瀽妯″潡""

    # 鐭ュ悕娓歌祫甯綅鍒楄〃锛堝寘鍚父瑙佸彉浣擄級
    FAMOUS_CAPITALISTS = {
        "绔犵洘涓?[
            "涓俊璇佸埜鑲′唤鏈夐檺鍏徃鏉窞寤跺畨璺瘉鍒歌惀涓氶儴",
            "鍥芥嘲鍚涘畨璇佸埜鑲′唤鏈夐檺鍏徃涓婃捣姹熻嫃璺瘉鍒歌惀涓氶儴",
            "鍥芥嘲鍚涘畨璇佸埜鑲′唤鏈夐檺鍏徃涓婃捣鍒嗗叕锟?,
            "鍥芥嘲鍚涘畨璇佸埜鑲′唤鏈夐檺鍏徃涓婃捣姹熻嫃锟?,
            "涓俊璇佸埜鏉窞寤跺畨锟?,
            "鍥芥嘲鍚涘畨涓婃捣姹熻嫃锟?
        ],
        "鏂规柊锟?: [
            "鍏翠笟璇佸埜鑲′唤鏈夐檺鍏徃闄曡タ鍒嗗叕锟?,
            "涓俊璇佸埜鑲′唤鏈夐檺鍏徃瑗垮畨鏈遍泙澶ц璇佸埜钀ヤ笟锟?,
            "鍏翠笟璇佸埜闄曡タ鍒嗗叕锟?,
            "涓俊璇佸埜瑗垮畨鏈遍泙澶ц",
            "鍏翠笟璇佸埜鑲′唤鏈夐檺鍏徃闄曡タ"
        ],
        "寰愮繑": [
            "鍥芥嘲鍚涘畨璇佸埜鑲′唤鏈夐檺鍏徃涓婃捣绂忓北璺瘉鍒歌惀涓氶儴",
            "鍏夊ぇ璇佸埜鑲′唤鏈夐檺鍏徃瀹佹尝瑙ｆ斁鍗楄矾璇佸埜钀ヤ笟锟?,
            "鍥芥嘲鍚涘畨涓婃捣绂忓北锟?,
            "鍏夊ぇ璇佸埜瀹佹尝瑙ｆ斁鍗楄矾",
            "鍥芥嘲鍚涘畨涓婃捣绂忓北璺瘉锟?
        ],
        "璧佃€佸摜": [
            "涓浗閾舵渤璇佸埜鑲′唤鏈夐檺鍏徃缁嶅叴璇佸埜钀ヤ笟锟?,
            "鍗庢嘲璇佸埜鑲′唤鏈夐檺鍏徃娴欐睙鍒嗗叕锟?,
            "閾舵渤璇佸埜缁嶅叴",
            "鍗庢嘲璇佸埜娴欐睙鍒嗗叕锟?,
            "涓浗閾舵渤璇佸埜缁嶅叴"
        ],
        "涔斿府锟?: [
            "涓俊璇佸埜鑲′唤鏈夐檺鍏徃涓婃捣娣捣涓矾璇佸埜钀ヤ笟锟?,
            "鍥芥嘲鍚涘畨璇佸埜鑲′唤鏈夐檺鍏徃涓婃捣鍒嗗叕锟?,
            "涓俊璇佸埜涓婃捣娣捣涓矾",
            "鍥芥嘲鍚涘畨涓婃捣鍒嗗叕锟?
        ],
        "鎴愰兘锟?: [
            "鍗庢嘲璇佸埜鑲′唤鏈夐檺鍏徃鎴愰兘铚€閲戣矾璇佸埜钀ヤ笟锟?,
            "鍥芥嘲鍚涘畨璇佸埜鑲′唤鏈夐檺鍏徃鎴愰兘鍖椾竴鐜矾璇佸埜钀ヤ笟锟?,
            "鍗庢嘲璇佸埜鎴愰兘铚€閲戣矾",
            "鍥芥嘲鍚涘畨鎴愰兘鍖椾竴鐜矾",
            "鍗庢嘲璇佸埜鎴愰兘"
        ],
        "浣涘北锟?: [
            "鍏夊ぇ璇佸埜鑲′唤鏈夐檺鍏徃浣涘北缁挎櫙璺瘉鍒歌惀涓氶儴",
            "闀挎睙璇佸埜鑲′唤鏈夐檺鍏徃浣涘北椤哄痉鏂板畞璺瘉鍒歌惀涓氶儴",
            "鍏夊ぇ璇佸埜浣涘北缁挎櫙锟?,
            "闀挎睙璇佸埜浣涘北椤哄痉鏂板畞锟?,
            "鍏夊ぇ璇佸埜浣涘北"
        ],
        "鐟為工锟?: [
            "涓浗涓噾璐㈠瘜璇佸埜鏈夐檺鍏徃娣卞湷鍒嗗叕锟?,
            "鍗庢嘲璇佸埜鑲′唤鏈夐檺鍏徃娣卞湷鐩婄敯璺崳瓒呭晢鍔′腑蹇冭瘉鍒歌惀涓氶儴",
            "涓噾璐㈠瘜娣卞湷",
            "鍗庢嘲璇佸埜娣卞湷鐩婄敯锟?,
            "涓浗涓噾璐㈠瘜娣卞湷"
        ],
        "浣滄墜鏂颁竴": [
            "鍥芥嘲鍚涘畨璇佸埜鑲′唤鏈夐檺鍏徃鍗椾含澶钩鍗楄矾璇佸埜钀ヤ笟锟?,
            "鍗庢嘲璇佸埜鑲′唤鏈夐檺鍏徃鍗椾含姹熶笢涓矾璇佸埜钀ヤ笟锟?,
            "鍥芥嘲鍚涘畨鍗椾含澶钩鍗楄矾",
            "鍗庢嘲璇佸埜鍗椾含姹熶笢涓矾",
            "鍥芥嘲鍚涘畨鍗椾含"
        ],
        "灏忛硠锟?: [
            "涓浗閾舵渤璇佸埜鑲′唤鏈夐檺鍏徃鍖椾含涓叧鏉戝ぇ琛楄瘉鍒歌惀涓氶儴",
            "涓俊璇佸埜鑲′唤鏈夐檺鍏徃鍖椾含鎬婚儴璇佸埜钀ヤ笟锟?,
            "閾舵渤璇佸埜鍖椾含涓叧鏉戝ぇ锟?,
            "涓俊璇佸埜鍖椾含鎬婚儴",
            "閾舵渤璇佸埜鍖椾含"
        ]
    }

    @staticmethod
    def analyze_longhubu_capital(date=None):
        """
        分析龙虎榜游资
        返回当日龙虎榜中的游资席位分析
        """
        try:
            import akshare as ak
            from datetime import datetime

            # 鑾峰彇榫欒檸姒滄暟锟?            try:
                if date:
                    if isinstance(date, str):
                        date_str = date
                    else:
                        date_str = date.strftime("%Y%m%d")
                    lhb_df = ak.stock_lhb_detail_em(date=date_str)
                    print(f"鑾峰彇 {date_str} 鐨勯緳铏庢鏁版嵁锛屽叡 {len(lhb_df)} 鏉¤锟?)
                else:
                    # 鑾峰彇鏈€杩戝嚑澶╃殑鏁版嵁
                    today = datetime.now()
                    lhb_df = ak.stock_lhb_detail_em(date=today.strftime("%Y%m%d"))
                    print(f"鑾峰彇浠婃棩榫欒檸姒滄暟鎹紝锟?{len(lhb_df)} 鏉¤锟?)
                    
                    # 濡傛灉浠婃棩鏃犳暟鎹紝灏濊瘯鑾峰彇鏄ㄥぉ锟?                    if lhb_df.empty:
                        yesterday = today - pd.Timedelta(days=1)
                        lhb_df = ak.stock_lhb_detail_em(date=yesterday.strftime("%Y%m%d"))
                        print(f"浠婃棩鏃犳暟鎹紝鑾峰彇鏄ㄦ棩榫欒檸姒滄暟鎹紝锟?{len(lhb_df)} 鏉¤锟?)
            except Exception as e:
                print(f"鑾峰彇榫欒檸姒滄暟鎹け锟? {e}")
                return {
                    '鏁版嵁鐘讹拷?: '鑾峰彇榫欒檸姒滄暟鎹け锟?,
                    '閿欒淇℃伅': str(e),
                    '璇存槑': '鍙兘鏄綉缁滈棶棰樻垨鏁版嵁婧愰檺鍒讹紝璇风◢鍚庨噸锟?
                }

            if lhb_df is None or lhb_df.empty:
                print("榫欒檸姒滄暟鎹负锟?)
                return {
                    '鏁版嵁鐘讹拷?: '鏃犳暟锟?,
                    '璇存槑': '鏆傛棤榫欒檸姒滄暟鎹紝鍙兘浠婃棩鏃犻緳铏庢鎴栨暟鎹湭鏇存柊銆傚缓璁€夋嫨鍏朵粬鏃ユ湡鏌ョ湅锟?
                }
            
            # 鎵撳嵃鍒楀悕锛屽府鍔╄皟锟?            print(f"榫欒檸姒滄暟鎹垪锟? {lhb_df.columns.tolist()}")
            print(f"锟?鏉℃暟鎹ず锟?\n{lhb_df.head(3)}")

            # 鍒嗘瀽娓歌祫甯綅
            capital_analysis = []
            capital_stats = {}
            matched_count = 0

            # 鎵撳嵃鎵€鏈夎惀涓氶儴鍚嶇О锛屽府鍔╄皟锟?            unique_seats = lhb_df['钀ヤ笟閮ㄥ悕锟?].unique()
            print(f"鍏辨壘锟?{len(unique_seats)} 涓笉鍚岀殑钀ヤ笟锟?)
            print(f"钀ヤ笟閮ㄥ垪锟? {unique_seats[:10]}...")  # 鍙墦鍗板墠10锟?
            for _, row in lhb_df.iterrows():
                seat_name = str(row['钀ヤ笟閮ㄥ悕锟?])
                
                # 妫€鏌ユ槸鍚︿负鐭ュ悕娓歌祫甯綅锛堜娇鐢ㄦā绯婂尮閰嶏級
                for capital_name, seats in CapitalAnalyzer.FAMOUS_CAPITALISTS.items():
                    # 绮剧‘鍖归厤
                    if seat_name in seats:
                        matched = True
                    # 妯＄硦鍖归厤锛氭鏌ユ槸鍚﹀寘鍚叧閿瘝
                    else:
                        matched = any(keyword in seat_name for keyword in seats)
                    
                    if matched:
                        matched_count += 1
                        # 缁熻娓歌祫鎿嶄綔
                        if capital_name not in capital_stats:
                            capital_stats[capital_name] = {
                                '涔板叆娆℃暟': 0,
                                '鍗栧嚭娆℃暟': 0,
                                '涔板叆閲戦': 0,
                                '鍗栧嚭閲戦': 0,
                                '鎿嶄綔鑲＄エ': []
                            }

                        # 鍒ゆ柇涔板崠鏂瑰悜
                        buy_amount = row.get('涔板叆閲戦', 0)
                        sell_amount = row.get('鍗栧嚭閲戦', 0)
                        
                        if buy_amount > 0:
                            capital_stats[capital_name]['涔板叆娆℃暟'] += 1
                            capital_stats[capital_name]['涔板叆閲戦'] += buy_amount
                        elif row['鍗栧嚭閲戦'] > 0:
                            capital_stats[capital_name]['鍗栧嚭娆℃暟'] += 1
                            capital_stats[capital_name]['鍗栧嚭閲戦'] += row['鍗栧嚭閲戦']

                        # 璁板綍鎿嶄綔鑲＄エ
                        stock_info = {
                            '浠ｇ爜': row['浠ｇ爜'],
                            '鍚嶇О': row['鍚嶇О'],
                            '鏃ユ湡': row['涓婃锟?],
                            '涔板叆閲戦': row['涔板叆閲戦'],
                            '鍗栧嚭閲戦': row['鍗栧嚭閲戦'],
                            '鍑€涔板叆': row['涔板叆閲戦'] - row['鍗栧嚭閲戦']
                        }
                        capital_stats[capital_name]['鎿嶄綔鑲＄エ'].append(stock_info)

                        capital_analysis.append({
                            '娓歌祫鍚嶇О': capital_name,
                            '钀ヤ笟閮ㄥ悕锟?: row['钀ヤ笟閮ㄥ悕锟?],
                            '鑲＄エ浠ｇ爜': row['浠ｇ爜'],
                            '鑲＄エ鍚嶇О': row['鍚嶇О'],
                            '涓婃锟?: row['涓婃锟?],
                            '涔板叆閲戦': row['涔板叆閲戦'],
                            '鍗栧嚭閲戦': row['鍗栧嚭閲戦'],
                            '鍑€涔板叆': row['涔板叆閲戦'] - row['鍗栧嚭閲戦']
                        })

            # 璁＄畻娓歌祫缁熻
            capital_summary = []
            for capital_name, stats in capital_stats.items():
                net_flow = stats['涔板叆閲戦'] - stats['鍗栧嚭閲戦']
                total_trades = stats['涔板叆娆℃暟'] + stats['鍗栧嚭娆℃暟']

                # 鍒ゆ柇鎿嶄綔椋庢牸
                if stats['涔板叆閲戦'] > stats['鍗栧嚭閲戦'] * 2:
                    style = "婵€杩涗拱锟?
                elif stats['鍗栧嚭閲戦'] > stats['涔板叆閲戦'] * 2:
                    style = "婵€杩涘崠锟?
                elif net_flow > 0:
                    style = "鍋忓锟?
                else:
                    style = "鍋忕┖锟?

                capital_summary.append({
                    '娓歌祫鍚嶇О': capital_name,
                    '涔板叆娆℃暟': stats['涔板叆娆℃暟'],
                    '鍗栧嚭娆℃暟': stats['鍗栧嚭娆℃暟'],
                    '鎬绘搷浣滄锟?: total_trades,
                    '涔板叆閲戦': stats['涔板叆閲戦'],
                    '鍗栧嚭閲戦': stats['鍗栧嚭閲戦'],
                    '鍑€娴佸叆': net_flow,
                    '鎿嶄綔椋庢牸': style,
                    '鎿嶄綔鑲＄エ锟?: len(stats['鎿嶄綔鑲＄エ'])
                })

            # 鎸夊噣娴佸叆鎺掑簭
            capital_summary.sort(key=lambda x: x['鍑€娴佸叆'], reverse=True)

            print(f"鍒嗘瀽瀹屾垚锛氬尮閰嶅埌 {matched_count} 鏉℃父璧勬搷浣滆褰曪紝娑夊強 {len(capital_stats)} 涓父锟?)

            return {
                '鏁版嵁鐘讹拷?: '姝ｅ父',
                '娓歌祫缁熻': capital_summary,
                '娓歌祫鎿嶄綔璁板綍': capital_analysis,
                '鍖归厤璁板綍锟?: matched_count,
                '娓歌祫鏁伴噺': len(capital_stats),
                '榫欒檸姒滄€昏褰曟暟': len(lhb_df),
                '璇存槑': f'锟?{len(lhb_df)} 鏉￠緳铏庢璁板綍涓紝鎵惧埌 {matched_count} 鏉℃父璧勬搷浣滆锟?
            }

            return {
                '鏁版嵁鐘讹拷?: '姝ｅ父',
                '娓歌祫鍒嗘瀽鍒楄〃': capital_analysis,
                '娓歌祫缁熻姹囷拷?: capital_summary,
                '娲昏穬娓歌祫锟?: len(capital_stats),
                '鎬绘搷浣滄锟?: len(capital_analysis)
            }

        except Exception as e:
            return {
                '鏁版嵁鐘讹拷?: '鑾峰彇澶辫触',
                '閿欒淇℃伅': str(e),
                '璇存槑': '鍙兘鏄綉缁滈棶棰樻垨鏁版嵁婧愰檺锟?
            }

    @staticmethod
    def track_capital_pattern(capital_name, days=30):
        """
        杩借釜娓歌祫鎿嶄綔妯″紡
        鍒嗘瀽鐗瑰畾娓歌祫鍦ㄦ寚瀹氭椂闂村唴鐨勬搷浣滆锟?        """
        try:
            import akshare as ak

            if capital_name not in CapitalAnalyzer.FAMOUS_CAPITALISTS:
                return {
                    '鏁版嵁鐘讹拷?: '鏈煡娓歌祫',
                    '璇存槑': f'鏈壘鍒版父锟? {capital_name}'
                }

            # 鑾峰彇璇ユ父璧勭殑甯綅鍒楄〃
            seats = CapitalAnalyzer.FAMOUS_CAPITALISTS[capital_name]
            print(f"娓歌祫 {capital_name} 鐨勫腑浣嶅垪锟? {seats}")

            # 鑾峰彇鍘嗗彶榫欒檸姒滄暟锟?            end_date = pd.Timestamp.now()
            start_date = end_date - pd.Timedelta(days=days)

            all_operations = []
            checked_dates = 0
            matched_dates = 0

            # 鑾峰彇姣忔棩榫欒檸姒滄暟锟?            current_date = start_date
            while current_date <= end_date:
                date_str = current_date.strftime("%Y%m%d")
                checked_dates += 1

                try:
                    lhb_df = ak.stock_lhb_detail_em(date=date_str)

                    if not lhb_df.empty:
                        print(f"{date_str}: 鑾峰彇锟?{len(lhb_df)} 鏉￠緳铏庢璁板綍")
                        
                        # 绛涢€夎娓歌祫鐨勬搷浣滐紙浣跨敤妯＄硦鍖归厤锟?                        for _, row in lhb_df.iterrows():
                            seat_name = str(row['钀ヤ笟閮ㄥ悕锟?])
                            
                            # 绮剧‘鍖归厤鎴栨ā绯婂尮锟?                            if seat_name in seats or any(keyword in seat_name for keyword in seats):
                                matched_dates += 1
                                all_operations.append({
                                    '鏃ユ湡': row['涓婃锟?],
                                    '鑲＄エ浠ｇ爜': row['浠ｇ爜'],
                                    '鑲＄エ鍚嶇О': row['鍚嶇О'],
                                    '涔板叆閲戦': row.get('涔板叆閲戦', 0),
                                    '鍗栧嚭閲戦': row.get('鍗栧嚭閲戦', 0),
                                    '鍑€涔板叆': row.get('涔板叆閲戦', 0) - row.get('鍗栧嚭閲戦', 0),
                                    '钀ヤ笟閮ㄥ悕锟?: seat_name
                                })
                                print(f"  鍖归厤锟? {seat_name} - {row['鍚嶇О']}({row['浠ｇ爜']})")
                except Exception as e:
                    print(f"{date_str}: 鑾峰彇鏁版嵁澶辫触 - {e}")
                    pass

                current_date += pd.Timedelta(days=1)

            print(f"妫€鏌ヤ簡 {checked_dates} 澶╋紝锟?{matched_dates} 澶╂壘鍒版搷浣滆褰曪紝锟?{len(all_operations)} 鏉℃搷锟?)

            # 濡傛灉娌℃湁鎿嶄綔璁板綍锛屾樉绀烘墍鏈夋壘鍒扮殑钀ヤ笟閮ㄥ悕锟?            if not all_operations:
                # 鑾峰彇鏈€杩戝嚑澶╃殑榫欒檸姒滄暟鎹紝鏀堕泦鎵€鏈夎惀涓氶儴鍚嶇О
                found_seats = []
                sample_date = start_date
                
                for _ in range(min(5, days)):  # 鏈€澶氭锟?锟?                    date_str = sample_date.strftime("%Y%m%d")
                    try:
                        lhb_df = ak.stock_lhb_detail_em(date=date_str)
                        if not lhb_df.empty:
                            all_seats = lhb_df['钀ヤ笟閮ㄥ悕锟?].unique()
                            found_seats.extend(all_seats)
                            print(f"{date_str}: 鎵惧埌 {len(all_seats)} 涓惀涓氶儴")
                            if len(found_seats) >= 50:  # 鏀堕泦瓒冲澶氱殑钀ヤ笟锟?                                break
                    except:
                        pass
                    sample_date += pd.Timedelta(days=1)
                
                # 鍘婚噸骞舵帓锟?                found_seats = sorted(list(set(found_seats)))
                
                return {
                    '鏁版嵁鐘讹拷?: '鏃犳搷浣滆锟?,
                    '璇存槑': f'{capital_name} 鍦ㄦ渶锟?{days} 澶╁唴鏃犳搷浣滆褰曘€傚彲鑳藉師鍥狅細1) 璇ユ父璧勮繎鏈熸湭涓婃 2) 甯綅鍚嶇О涓嶅尮锟?3) 鏁版嵁婧愰檺鍒躲€傝鏌ョ湅涓嬫柟璋冭瘯淇℃伅涓殑瀹為檯钀ヤ笟閮ㄥ悕绉拌繘琛屽姣旓拷?,
                    '妫€鏌ュぉ锟?: checked_dates,
                    '鍖归厤澶╂暟': matched_dates,
                    '娓歌祫甯綅': seats,
                    '瀹為檯钀ヤ笟锟?: found_seats[:30]  # 鍙繑鍥炲墠30锟?                }

            # 鍒嗘瀽鎿嶄綔妯″紡
            df_ops = pd.DataFrame(all_operations)

            # 1. 鎿嶄綔棰戠巼
            operation_frequency = len(all_operations) / days

            # 2. 涔板崠鍋忓ソ
            total_buy = df_ops['涔板叆閲戦'].sum()
            total_sell = df_ops['鍗栧嚭閲戦'].sum()
            buy_ratio = total_buy / (total_buy + total_sell) if (total_buy + total_sell) > 0 else 0

            # 3. 鍗曟鎿嶄綔閲戦
            avg_operation_amount = df_ops['鍑€涔板叆'].abs().mean()

            # 4. 鎿嶄綔鎴愬姛鐜囷紙鍚庣画3澶╂定璺岋級
            success_count = 0
            total_count = 0

            db = DataManager()
            for op in all_operations:
                try:
                    symbol = op['鑲＄エ浠ｇ爜']
                    op_date = op['鏃ユ湡']

                    # 鑾峰彇鍘嗗彶鏁版嵁
                    start_date_str = op_date
                    end_date_str = (pd.Timestamp(op_date) + pd.Timedelta(days=5)).strftime("%Y%m%d")

                    df = db.get_history_data(symbol, start_date=start_date_str, end_date=end_date_str)

                    if not df.empty and len(df) > 3:
                        # 璁＄畻鎿嶄綔锟?澶╃殑娑ㄨ穼锟?                        op_price = df.iloc[0]['close']
                        future_price = df.iloc[3]['close']
                        future_return = (future_price - op_price) / op_price * 100

                        if future_return > 0:
                            success_count += 1
                        total_count += 1
                except:
                    pass

            db.close()

            success_rate = (success_count / total_count * 100) if total_count > 0 else 0

            # 5. 鍒ゆ柇鎿嶄綔椋庢牸
            if buy_ratio > 0.7:
                style = "婵€杩涗拱鍏ュ瀷"
            elif buy_ratio < 0.3:
                style = "婵€杩涘崠鍑哄瀷"
            elif avg_operation_amount > 50000000:
                style = "澶ц祫閲戞搷浣滃瀷"
            else:
                style = "鍧囪　鎿嶄綔锟?

            return {
                '鏁版嵁鐘讹拷?: '姝ｅ父',
                '娓歌祫鍚嶇О': capital_name,
                '鍒嗘瀽澶╂暟': days,
                '鎿嶄綔娆℃暟': len(all_operations),
                '鎿嶄綔棰戠巼': round(operation_frequency, 2),
                '鎬讳拱鍏ラ噾锟?: total_buy,
                '鎬诲崠鍑洪噾锟?: total_sell,
                '涔板叆姣斾緥': round(buy_ratio * 100, 1),
                '骞冲潎鎿嶄綔閲戦': round(avg_operation_amount, 0),
                '鎿嶄綔鎴愬姛锟?: round(success_rate, 1),
                '鎿嶄綔椋庢牸': style,
                '鎿嶄綔璁板綍': all_operations
            }

        except Exception as e:
            return {
                '鏁版嵁鐘讹拷?: '鍒嗘瀽澶辫触',
                '閿欒淇℃伅': str(e),
                '璇存槑': '鍙兘鏄綉缁滈棶棰樻垨鏁版嵁婧愰檺锟?
            }

    @staticmethod
    def predict_capital_next_move(capital_name):
        """
        棰勬祴娓歌祫涓嬩竴姝ユ搷锟?        鍩轰簬鍘嗗彶鎿嶄綔妯″紡棰勬祴
        """
        try:
            # 鑾峰彇娓歌祫鎿嶄綔妯″紡
            pattern_result = CapitalAnalyzer.track_capital_pattern(capital_name, days=30)

            if pattern_result['鏁版嵁鐘讹拷?] != '姝ｅ父':
                return pattern_result

            # 鑾峰彇鏈€杩戞搷锟?            recent_operations = pattern_result['鎿嶄綔璁板綍'][-5:]  # 鏈€锟?娆℃搷锟?
            # 鍒嗘瀽鏈€杩戞搷浣滃€惧悜
            recent_buy = sum(op['涔板叆閲戦'] for op in recent_operations)
            recent_sell = sum(op['鍗栧嚭閲戦'] for op in recent_operations)

            # 棰勬祴
            predictions = []

            if recent_buy > recent_sell * 2:
                predictions.append({
                    '棰勬祴绫诲瀷': '缁х画涔板叆',
                    '姒傜巼': '锟?,
                    '璇存槑': f'{capital_name} 鏈€杩戝ぇ骞呬拱鍏ワ紝鍙兘缁х画鍔犱粨'
                })
            elif recent_sell > recent_buy * 2:
                predictions.append({
                    '棰勬祴绫诲瀷': '缁х画鍗栧嚭',
                    '姒傜巼': '锟?,
                    '璇存槑': f'{capital_name} 鏈€杩戝ぇ骞呭崠鍑猴紝鍙兘缁х画鍑忎粨'
                })
            else:
                predictions.append({
                    '棰勬祴绫诲瀷': '瑙傛湜鎴栧皬骞呮搷锟?,
                    '姒傜巼': '锟?,
                    '璇存槑': f'{capital_name} 鏈€杩戞搷浣滃潎琛★紝鍙兘瑙傛湜'
                })

            # 鏍规嵁鎴愬姛鐜囬锟?            if pattern_result['鎿嶄綔鎴愬姛锟?] > 60:
                predictions.append({
                    '棰勬祴绫诲瀷': '鍏虫敞鍏舵搷锟?,
                    '姒傜巼': '锟?,
                    '璇存槑': f'{capital_name} 鍘嗗彶鎴愬姛鐜囬珮锛屽缓璁叧娉ㄥ叾鎿嶄綔'
                })

            return {
                '鏁版嵁鐘讹拷?: '姝ｅ父',
                '娓歌祫鍚嶇О': capital_name,
                '棰勬祴鍒楄〃': predictions
            }

        except Exception as e:
            return {
                '鏁版嵁鐘讹拷?: '棰勬祴澶辫触',
                '閿欒淇℃伅': str(e),
                '璇存槑': '鍙兘鏄暟鎹棶锟?
            }