from decimal import Decimal
from typing import List, Tuple
import logging

from hummingbot.connector.exchange.paper_trade import create_paper_trade_market
from hummingbot.connector.connector_base import ConnectorBase
from hummingbot.strategy.api_asset_price_delegate import APIAssetPriceDelegate
from hummingbot.strategy.market_trading_pair_tuple import MarketTradingPairTuple
from hummingbot.strategy.order_book_asset_price_delegate import OrderBookAssetPriceDelegate
from hummingbot.strategy.perpetual_market_making import PerpetualMarketMakingStrategy
from hummingbot.strategy.perpetual_market_making.perpetual_market_making_config_map import (
    perpetual_market_making_config_map as c_map,
)
from hummingbot.strategy.perpetual_market_making.optimal_params_calculator import OptimalParamsCalculator

logger = logging.getLogger(__name__)


async def start(self):
    try:
        leverage = c_map.get("leverage").value
        position_mode = c_map.get("position_mode").value
        order_amount = c_map.get("order_amount").value
        order_refresh_time = c_map.get("order_refresh_time").value
        auto_optimize_params = c_map.get("auto_optimize_params").value
        
        # 如果啟用自動參數優化，計算最優參數
        if auto_optimize_params:
            logger.info("🔧 啟用自動參數優化，正在計算最優參數...")
            try:
                # 獲取自動優化相關參數
                raw_trading_pair = c_map.get("market").value
                target_fill_prob = float(c_map.get("auto_optimize_target_fill_prob").value)
                stop_loss_risk_prob = float(c_map.get("auto_optimize_stop_loss_risk_prob").value)
                profit_factor = float(c_map.get("auto_optimize_profit_factor").value)
                max_holding_days = float(c_map.get("auto_optimize_max_holding_days").value)
                data_source = c_map.get("auto_optimize_data_source").value
                kline_interval = c_map.get("auto_optimize_kline_interval").value
                
                # 轉換交易對格式 (從 BTC-USDT 到 BTC_USDT 給 Gate.io API)
                if data_source == "gateio":
                    gateio_pair = raw_trading_pair.replace("-", "_")
                    
                    calculator = OptimalParamsCalculator()
                    optimal_params = calculator.calculate_from_gateio(
                        currency_pair=gateio_pair,
                        interval=kline_interval,
                        target_order_fill_prob=target_fill_prob,
                        order_refresh_time_sec=int(order_refresh_time),
                        stop_loss_risk_prob=stop_loss_risk_prob,
                        max_holding_time_days=max_holding_days,
                        profit_factor=profit_factor
                    )
                    
                    # 使用計算出的最優參數
                    bid_spread = optimal_params["bid_spread"] / Decimal('100')
                    ask_spread = optimal_params["ask_spread"] / Decimal('100')
                    long_profit_taking_spread = optimal_params["long_profit_taking_spread"] / Decimal('100')
                    short_profit_taking_spread = optimal_params["short_profit_taking_spread"] / Decimal('100')
                    stop_loss_spread = optimal_params["stop_loss_spread"] / Decimal('100')
                    
                    logger.info(f"✅ 自動優化完成！使用的參數:")
                    logger.info(f"   📈 Bid Spread: {optimal_params['bid_spread']:.4f}%")
                    logger.info(f"   📉 Ask Spread: {optimal_params['ask_spread']:.4f}%")
                    logger.info(f"   💰 Long Profit Taking: {optimal_params['long_profit_taking_spread']:.4f}%")
                    logger.info(f"   💰 Short Profit Taking: {optimal_params['short_profit_taking_spread']:.4f}%")
                    logger.info(f"   🛑 Stop Loss: {optimal_params['stop_loss_spread']:.4f}%")
                    logger.info(f"   📊 日化波動率: {optimal_params['daily_volatility_pct']:.2f}% (基於 {kline_interval} K線)")
                    
                else:
                    # 使用當前市場數據計算波動率 (TODO: 實現從當前市場數據計算波動率)
                    logger.warning("⚠️  current_market 數據源尚未實現，將使用手動設置的參數")
                    bid_spread = c_map.get("bid_spread").value / Decimal('100')
                    ask_spread = c_map.get("ask_spread").value / Decimal('100')
                    long_profit_taking_spread = c_map.get("long_profit_taking_spread").value / Decimal('100')
                    short_profit_taking_spread = c_map.get("short_profit_taking_spread").value / Decimal('100')
                    stop_loss_spread = c_map.get("stop_loss_spread").value / Decimal('100')
                    
            except Exception as e:
                logger.error(f"❌ 自動參數優化失敗: {e}")
                logger.info("📝 將使用手動設置的參數")
                bid_spread = c_map.get("bid_spread").value / Decimal('100')
                ask_spread = c_map.get("ask_spread").value / Decimal('100')
                long_profit_taking_spread = c_map.get("long_profit_taking_spread").value / Decimal('100')
                short_profit_taking_spread = c_map.get("short_profit_taking_spread").value / Decimal('100')
                stop_loss_spread = c_map.get("stop_loss_spread").value / Decimal('100')
        else:
            # 使用手動設置的參數
            bid_spread = c_map.get("bid_spread").value / Decimal('100')
            ask_spread = c_map.get("ask_spread").value / Decimal('100')
            long_profit_taking_spread = c_map.get("long_profit_taking_spread").value / Decimal('100')
            short_profit_taking_spread = c_map.get("short_profit_taking_spread").value / Decimal('100')
            stop_loss_spread = c_map.get("stop_loss_spread").value / Decimal('100')
        time_between_stop_loss_orders = c_map.get("time_between_stop_loss_orders").value
        stop_loss_slippage_buffer = c_map.get("stop_loss_slippage_buffer").value / Decimal('100')
        stop_loss_use_maker_orders = c_map.get("stop_loss_use_maker_orders").value
        stop_loss_maker_timeout = c_map.get("stop_loss_maker_timeout").value
        stop_loss_auto_fallback = c_map.get("stop_loss_auto_fallback").value
        minimum_spread = c_map.get("minimum_spread").value / Decimal('100')
        price_ceiling = c_map.get("price_ceiling").value
        price_floor = c_map.get("price_floor").value
        order_levels = c_map.get("order_levels").value
        order_level_amount = c_map.get("order_level_amount").value
        order_level_spread = c_map.get("order_level_spread").value / Decimal('100')
        exchange = c_map.get("derivative").value.lower()
        raw_trading_pair = c_map.get("market").value
        filled_order_delay = c_map.get("filled_order_delay").value
        order_optimization_enabled = c_map.get("order_optimization_enabled").value
        ask_order_optimization_depth = c_map.get("ask_order_optimization_depth").value
        bid_order_optimization_depth = c_map.get("bid_order_optimization_depth").value
        price_source = c_map.get("price_source").value
        price_type = c_map.get("price_type").value
        price_source_exchange = c_map.get("price_source_derivative").value
        price_source_market = c_map.get("price_source_market").value
        price_source_custom_api = c_map.get("price_source_custom_api").value
        custom_api_update_interval = c_map.get("custom_api_update_interval").value
        order_refresh_tolerance_pct = c_map.get("order_refresh_tolerance_pct").value / Decimal('100')
        order_override = c_map.get("order_override").value

        trading_pair: str = raw_trading_pair
        base, quote = trading_pair.split("-")
        maker_assets: Tuple[str, str] = (base, quote)
        market_names: List[Tuple[str, List[str]]] = [(exchange, [trading_pair])]
        await self.initialize_markets(market_names)
        maker_data = [self.markets[exchange], trading_pair] + list(maker_assets)
        self.market_trading_pair_tuples = [MarketTradingPairTuple(*maker_data)]
        asset_price_delegate = None
        if price_source == "external_market":
            asset_trading_pair: str = price_source_market
            ext_market = create_paper_trade_market(
                price_source_exchange, [asset_trading_pair]
            )
            self.markets[price_source_exchange]: ConnectorBase = ext_market
            asset_price_delegate = OrderBookAssetPriceDelegate(ext_market, asset_trading_pair)
        elif price_source == "custom_api":
            ext_market = create_paper_trade_market(
                exchange, [raw_trading_pair]
            )
            asset_price_delegate = APIAssetPriceDelegate(ext_market, price_source_custom_api,
                                                         custom_api_update_interval)

        strategy_logging_options = PerpetualMarketMakingStrategy.OPTION_LOG_ALL

        self.strategy = PerpetualMarketMakingStrategy()
        self.strategy.init_params(
            market_info=MarketTradingPairTuple(*maker_data),
            leverage=leverage,
            position_mode=position_mode,
            bid_spread=bid_spread,
            ask_spread=ask_spread,
            order_amount=order_amount,
            long_profit_taking_spread=long_profit_taking_spread,
            short_profit_taking_spread=short_profit_taking_spread,
            stop_loss_spread=stop_loss_spread,
            time_between_stop_loss_orders=time_between_stop_loss_orders,
            stop_loss_slippage_buffer=stop_loss_slippage_buffer,
            stop_loss_use_maker_orders=stop_loss_use_maker_orders,
            stop_loss_maker_timeout=stop_loss_maker_timeout,
            stop_loss_auto_fallback=stop_loss_auto_fallback,
            order_levels=order_levels,
            order_level_spread=order_level_spread,
            order_level_amount=order_level_amount,
            order_refresh_time=order_refresh_time,
            order_refresh_tolerance_pct=order_refresh_tolerance_pct,
            filled_order_delay=filled_order_delay,
            order_optimization_enabled=order_optimization_enabled,
            ask_order_optimization_depth=ask_order_optimization_depth,
            bid_order_optimization_depth=bid_order_optimization_depth,
            asset_price_delegate=asset_price_delegate,
            price_type=price_type,
            price_ceiling=price_ceiling,
            price_floor=price_floor,
            logging_options=strategy_logging_options,
            minimum_spread=minimum_spread,
            hb_app_notification=True,
            order_override=order_override,
        )
        
        # 🔧 如果啟用自動參數優化，設置相關配置
        if auto_optimize_params:
            try:
                update_interval = c_map.get("auto_optimize_update_interval").value
                auto_optimize_config = {
                    "interval": c_map.get("auto_optimize_kline_interval").value,
                    "target_order_fill_prob": float(c_map.get("auto_optimize_target_fill_prob").value),
                    "order_refresh_time_sec": int(order_refresh_time),
                    "stop_loss_risk_prob": float(c_map.get("auto_optimize_stop_loss_risk_prob").value),
                    "max_holding_time_days": float(c_map.get("auto_optimize_max_holding_days").value),
                    "profit_factor": float(c_map.get("auto_optimize_profit_factor").value)
                }
                
                calculator = OptimalParamsCalculator()
                self.strategy.enable_auto_optimize(
                    calculator=calculator,
                    update_interval_minutes=update_interval,
                    config=auto_optimize_config
                )
                
                logger.info("🚀 合約造市策略已啟動，包含自動參數優化功能")
                logger.info(f"📊 自動優化配置:")
                logger.info(f"   📈 K線間隔: {auto_optimize_config['interval']}")
                logger.info(f"   🎯 目標成交機率: {auto_optimize_config['target_order_fill_prob']*100:.1f}%")
                logger.info(f"   🔄 更新間隔: {update_interval} 分鐘")
                logger.info(f"   🛑 止損風險機率: {auto_optimize_config['stop_loss_risk_prob']*100:.2f}%")
                logger.info(f"   💰 止盈倍數: {auto_optimize_config['profit_factor']:.1f}x")
                logger.info(f"   📅 最大持倉天數: {auto_optimize_config['max_holding_time_days']:.1f} 天")
                
            except Exception as e:
                logger.error(f"❌ 自動參數優化設置失敗: {e}")
                logger.info("📝 策略將使用手動設置的固定參數")
        else:
            logger.info("📝 合約造市策略已啟動，使用手動設置的固定參數")
    except Exception as e:
        self.notify(str(e))
        self.logger().error("Unknown error during initialization.", exc_info=True)
