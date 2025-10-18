import yaml
from decimal import Decimal

print("--- MACD Market Making Config Generator ---")
print("Please enter the following values:")

config = {}
config["controller_name"] = "macd_market_making"
config["controller_type"] = "market_making"

config["connector_name"] = input("Enter the exchange name (e.g., binance_perpetual): ")
config["trading_pair"] = input("Enter the trading pair (e.g., ENSO-USDT): ")
config["total_amount_quote"] = float(input("Enter the total amount in quote asset (e.g., 1000.0): "))

buy_spreads_str = input("Enter a comma-separated list of buy spreads (e.g., 0.01,0.02): ")
config["buy_spreads"] = [float(s.strip()) for s in buy_spreads_str.split(',')]

sell_spreads_str = input("Enter a comma-separated list of sell spreads (e.g., 0.01,0.02): ")
config["sell_spreads"] = [float(s.strip()) for s in sell_spreads_str.split(',')]

buy_amounts_pct_str = input("Enter a comma-separated list of buy amount percentages (e.g., 0.5,0.5): ")
config["buy_amounts_pct"] = [float(s.strip()) for s in buy_amounts_pct_str.split(',')]

sell_amounts_pct_str = input("Enter a comma-separated list of sell amount percentages (e.g., 0.5,0.5): ")
config["sell_amounts_pct"] = [float(s.strip()) for s in sell_amounts_pct_str.split(',')]

config["executor_refresh_time"] = int(input("Enter the order refresh time in seconds (e.g., 30): "))
config["leverage"] = int(input("Enter the leverage (e.g., 20): "))
config["position_mode"] = input("Enter the position mode (ONEWAY/HEDGE): ")
config["interval"] = input("Enter the candle interval (e.g., 1m): ")
config["macd_fast"] = int(input("Enter the MACD fast period (e.g., 12): "))
config["macd_slow"] = int(input("Enter the MACD slow period (e.g., 26): "))
config["macd_signal"] = int(input("Enter the MACD signal period (e.g., 9): "))
config["volatility_factor"] = float(input("Enter the volatility factor (e.g., 0.01): "))
config["stop_loss"] = float(input("Enter the stop loss percentage (e.g., 0.02): "))
config["take_profit"] = float(input("Enter the take profit percentage (e.g., 0.01): "))
config["time_limit"] = int(input("Enter the time limit in seconds (e.g., 600): "))

file_path = "conf/controllers/macd_market_making_1.yml"
with open(file_path, "w") as f:
    yaml.dump(config, f)

print(f"\nSuccessfully created configuration file: {file_path}")
print("You can now start the main strategy.")
