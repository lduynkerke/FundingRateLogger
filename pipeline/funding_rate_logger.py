"""
Funding rate data collection and logging pipeline.

This module implements the core functionality for monitoring cryptocurrency funding rates
and collecting market data around funding events. It handles:

1. Identifying upcoming funding rate payout times
2. Finding the highest funding rate symbols before each payout
3. Collecting OHLCV data at different timeframes around funding events
4. Saving the collected data to CSV files for later analysis

The module is designed to be called periodically and will automatically determine
when to collect data based on proximity to funding times.
"""

import csv
import os
from pathlib import Path
from typing import List, Dict
from datetime import datetime, timedelta, timezone
from api.contract_client import MEXCContractClient
from utils.funding_rate_cache import cache_top_symbols, load_cached_symbols, cleanup_old_caches
from utils.config_loader import load_config
from utils.logger import get_logger

CACHE_DIR = Path("cache/funding_rates")

def fetch_top_symbols(client: MEXCContractClient, top_n: int = 3, min_funding_minutes: int = 15, max_funding_minutes: int = 30) -> list[str]:
    """
    Fetches the top symbols with highest absolute funding rates that have funding within the specified time window.

    :param client: Initialized MEXCContractClient.
    :type client: MEXCContractClient
    :param top_n: Number of top symbols to return.
    :type top_n: int
    :param min_funding_minutes: Minimum minutes until funding (exclusive lower bound).
    :type min_funding_minutes: int
    :param max_funding_minutes: Maximum minutes until funding (inclusive upper bound).
    :type max_funding_minutes: int
    :return: List of top symbols with funding in the specified window.
    :rtype: list[str]
    """
    logger = get_logger()
    logger.info(f"Fetching top {top_n} symbols with highest funding rates and funding between {min_funding_minutes}-{max_funding_minutes} minutes")
    try:
        now = datetime.now(timezone.utc)
        symbols = client.get_available_perpetual_symbols()
        
        fetch_count = min(top_n * 5, len(symbols))  # Get 3x more to have enough after filtering
        top_rates = client.get_top_funding_rates(symbols, top_n=fetch_count)
        
        symbols_with_imminent_funding = []
        for entry in top_rates:
            symbol = entry['symbol']
            
            next_settle_time = entry.get('nextSettleTime', 0)
            
            # If nextSettleTime is not in the entry, we need to fetch it separately
            if next_settle_time == 0:
                logger.debug(f"nextSettleTime not found in entry for {symbol}, fetching separately")
                next_settle_time = client.get_next_funding_time(symbol)
            
            if next_settle_time > 0:
                next_settle_time_sec = next_settle_time / 1000
                time_until_funding_sec = next_settle_time_sec - now.timestamp()
                time_until_funding_min = time_until_funding_sec / 60
                
                logger.debug(f"Symbol {symbol} next funding time: {datetime.fromtimestamp(next_settle_time_sec, timezone.utc).isoformat()}, minutes until funding: {time_until_funding_min:.2f}")
                
                # Check if funding is within the 15-30 minute window
                if min_funding_minutes < time_until_funding_min <= max_funding_minutes:
                    symbols_with_imminent_funding.append(symbol)
                    logger.info(f"Symbol {symbol} will be funded in {time_until_funding_min:.2f} minutes (within {min_funding_minutes}-{max_funding_minutes} minute window)")
                    
                    if len(symbols_with_imminent_funding) >= top_n:
                        break
        
        logger.info(f"Successfully fetched {len(symbols_with_imminent_funding)} symbols with imminent funding: {', '.join(symbols_with_imminent_funding)}")
        return symbols_with_imminent_funding
    except Exception as e:
        logger.error(f"Error fetching top symbols: {e}")
        return []

def log_funding_snapshot(client: MEXCContractClient, config: Dict) -> None:
    """
    Logs funding rate snapshot and OHLCV data if within the 15-30 minute window before a funding event.

    This function implements a two-phase data collection strategy:
    1. At 15-30 minutes before funding: Identifies and caches the top symbols with highest funding rates
    2. At 15-30 minutes after funding: Retrieves the cached symbols and collects OHLCV data for them
    
    The function should be called periodically (e.g., every 5 minutes) and will automatically
    determine when to perform each action based on proximity to funding times.
    
    This approach allows the system to identify high-funding-rate symbols early, then focus
    data collection efforts on just those symbols as the funding time approaches.

    :param client: Initialized MEXCContractClient.
    :type client: MEXCContractClient
    :param config: Configuration dictionary containing funding settings.
    :type config: dict
    :return: None
    """
    logger = get_logger()
    now = datetime.now(timezone.utc)
    logger.debug(f"Checking funding snapshot at {now.isoformat()}")
    
    try:
        funding_times = get_next_funding_times(now)
        next_funding = min(funding_times, key=lambda ft: abs((ft - now).total_seconds()))
        logger.debug(f"Next reference funding time: {next_funding.isoformat()}")

        # Check if we're in the appropriate time window (not in first 30 minutes or last 15 minutes of an hour)
        current_minute = now.minute
        if current_minute < 30 or current_minute > 45:
            logger.info(f"Current time {now.isoformat()} is not in the 15-30 minute window before a whole hour (minute: {current_minute})")
            logger.info("Skipping top symbols fetch as we're either in the first 30 minutes or last 15 minutes of an hour")
        else:
            # Fetch top symbols with funding only in the 15-30 minutes window before funding
            symbols_in_window = fetch_top_symbols(
                client, 
                top_n=config.get('top_n', 5),
                min_funding_minutes=15,
                max_funding_minutes=30
            )
            
            if symbols_in_window:
                cache_top_symbols(symbols_in_window, next_funding, cache_dir=CACHE_DIR)
                logger.info(f"Cached {len(symbols_in_window)} symbols at {now.isoformat()} for {next_funding.isoformat()}: {', '.join(symbols_in_window)}")
            else:
                logger.info("No symbols found with funding within the 15-30 minutes window")
        
        # Check for post-funding data collection (15-30 minutes after funding)
        for funding_time in funding_times:
            delta = (now - funding_time).total_seconds() / 60
            
            if 15 <= delta <= 30:
                logger.info(f"15-minute window after funding at {funding_time.isoformat()}, collecting data")
                cached_symbols = load_cached_symbols(funding_time, cache_dir=CACHE_DIR)
                if cached_symbols:
                    logger.info(f"Loaded cached symbols for {funding_time.isoformat()}: {', '.join(cached_symbols)}")
                    for symbol in cached_symbols:
                        collect_and_save_data(client, symbol, funding_time, config)
                    logger.info(f"Data collection completed for {funding_time.isoformat()} at {now.isoformat()}")
                else:
                    logger.info(f"No cached symbols found for {funding_time.isoformat()}")
    except Exception as e:
        logger.error(f"Error in log_funding_snapshot: {e}")
        raise

def collect_and_save_data(client: MEXCContractClient, symbol: str, funding_time: datetime, config: Dict) -> None:
    """
    Collects OHLCV candles and saves them to CSV for a given symbol and funding time.
    
    This function retrieves price data at multiple timeframes around a funding event:
    - Daily candles: For longer-term context (configurable days back from funding time)
    - Hourly candles: For medium-term context (configurable hours back from funding time)
    - 5m candles: For short-term context before funding (configurable hours before funding)
    - 1m candles: For detailed price action around funding (configurable minutes before and after)
    
    All timeframes are configurable through the config.yaml file under the funding.time_windows section.
    The collected data is saved to a CSV file with a timestamp in the filename.
    
    :param client: Initialized MEXCContractClient.
    :type client: MEXCContractClient
    :param symbol: Contract symbol (e.g., 'BTC_USDT').
    :type symbol: str
    :param funding_time: The datetime of the funding rate payout.
    :type funding_time: datetime
    :param config: Configuration dictionary containing funding settings, especially time_windows.
    :type config: dict
    :return: None
    """
    logger = get_logger()
    logger.info(f"Collecting data for {symbol} at funding time {funding_time.isoformat()}")
    
    try:
        time_windows = config.get('time_windows', {})
        
        days_back = time_windows.get('daily_days_back', 3)
        hourly_back = time_windows.get('hourly_hours_back', 4)
        five_min_hours_before = time_windows.get('five_min_hours_before', 1)
        one_min_minutes_before = time_windows.get('one_min_minutes_before', 10)
        one_min_minutes_after = time_windows.get('one_min_minutes_after', 10)
        
        funding_ts = int(funding_time.timestamp())
        
        daily_end = funding_ts
        daily_start = daily_end - days_back * 24 * 3600
        
        hourly_end = funding_ts
        hourly_start = funding_ts - hourly_back * 3600
        
        five_min_end = funding_ts
        five_min_start = five_min_end - five_min_hours_before * 3600
        
        one_min_end = funding_ts + one_min_minutes_after * 60
        one_min_start = funding_ts - one_min_minutes_before * 60

        logger.debug(f"Fetching daily candles for {symbol}: {daily_start} to {daily_end}")
        candles_daily = client.get_futures_ohlcv(symbol, 'Day1', daily_start, daily_end)
        if isinstance(candles_daily, dict) and 'time' in candles_daily:
            candles_daily_len = len(candles_daily.get('time', []))
            logger.debug(f"Fetched {candles_daily_len} daily candles")
        else:
            logger.debug(f"Fetched {len(candles_daily) if isinstance(candles_daily, list) else 0} daily candles")
        
        logger.debug(f"Fetching hourly candles for {symbol}: {hourly_start} to {hourly_end}")
        candles_1h = client.get_futures_ohlcv(symbol, 'Min60', hourly_start, hourly_end)
        if isinstance(candles_1h, dict) and 'time' in candles_1h:
            candles_1h_len = len(candles_1h.get('time', []))
            logger.debug(f"Fetched {candles_1h_len} hourly candles")
        else:
            logger.debug(f"Fetched {len(candles_1h) if isinstance(candles_1h, list) else 0} hourly candles")
        
        logger.debug(f"Fetching 5m candles for {symbol}: {five_min_start} to {five_min_end}")
        candles_5m = client.get_futures_ohlcv(symbol, 'Min5', five_min_start, five_min_end)
        if isinstance(candles_5m, dict) and 'time' in candles_5m:
            candles_5m_len = len(candles_5m.get('time', []))
            logger.debug(f"Fetched {candles_5m_len} 5m candles")
        else:
            logger.debug(f"Fetched {len(candles_5m) if isinstance(candles_5m, list) else 0} 5m candles")
        
        logger.debug(f"Fetching 1m candles for {symbol}: {one_min_start} to {one_min_end}")
        candles_1m = client.get_futures_ohlcv(symbol, 'Min1', one_min_start, one_min_end)
        if isinstance(candles_1m, dict) and 'time' in candles_1m:
            candles_1m_len = len(candles_1m.get('time', []))
            logger.debug(f"Fetched {candles_1m_len} 1m candles")
        else:
            logger.debug(f"Fetched {len(candles_1m) if isinstance(candles_1m, list) else 0} 1m candles")

        data = {'daily': candles_daily, '1h': candles_1h, '5m': candles_5m, '1m': candles_1m}
        save_data_to_csv(symbol, funding_time, data)
        logger.info(f"Successfully collected and saved data for {symbol}")
    except Exception as e:
        logger.error(f"Error collecting data for {symbol}: {e}")
        raise

def get_next_funding_times(reference_time: datetime = None) -> list[datetime]:
    """
    Computes the funding payout times in UTC for today and nearby boundary times.

    Funding typically happens at 00:00, 08:00, and 16:00 UTC daily. This function
    also includes 16:00 of the previous day and 00:00 of the next day to handle
    boundary cases.

    :param reference_time: Optional datetime to base computation on. Defaults to now.
    :type reference_time: datetime
    :return: List of datetime objects representing payout times sorted by difference to current hour (low to high).
    :rtype: list[datetime]
    """
    if reference_time is None:
        reference_time = datetime.now(timezone.utc)

    today = reference_time.date()
    funding_hours = list(range(24))  # 0 to 23 hours

    times = [datetime(today.year, today.month, today.day, h, 0, 0, tzinfo=timezone.utc)
             for h in funding_hours]

    prev_day = today - timedelta(days=1)
    next_day = today + timedelta(days=1)

    # Add last hour of previous day and first hour of next day to handle boundary cases
    times.append(datetime(prev_day.year, prev_day.month, prev_day.day, 23, 0, 0, tzinfo=timezone.utc))
    times.append(datetime(next_day.year, next_day.month, next_day.day, 0, 0, 0, tzinfo=timezone.utc))
    
    current_hour = reference_time.hour
    
    def sort_key(dt):
        hour_diff = abs(dt.hour - current_hour)
        
        if dt < reference_time and reference_time - dt <= timedelta(hours=1) or dt >= reference_time:
            return hour_diff
        else:
            # If the datetime is more than one hour in the past, put it at the end
            return float('inf')
            
    return sorted(times, key=sort_key)


def is_within_window(target_time: datetime, window_minutes: int = 10) -> bool:
    """
    Checks if the current UTC time is within ±window_minutes of a target time.

    :param target_time: The target datetime to compare to now.
    :type target_time: datetime
    :param window_minutes: Number of minutes for the symmetric time window.
    :type window_minutes: int
    :return: True if within window, False otherwise.
    :rtype: bool
    """
    now = datetime.now(timezone.utc)
    delta = abs((now - target_time).total_seconds()) / 60
    return delta <= window_minutes

def save_data_to_csv(symbol: str, funding_time: datetime, candle_data: Dict[str, List[list] | dict]) -> None:
    """
    Saves the collected candle data to a CSV file in the /data directory.

    :param symbol: Contract symbol.
    :type symbol: str
    :param funding_time: The datetime of the funding rate payout.
    :type funding_time: datetime
    :param candle_data: Dictionary with '1m', '5m', and '1h' candle data (either lists or dicts).
    :type candle_data: dict
    :return: None
    """
    logger = get_logger()
    timestamp_str = funding_time.strftime('%Y-%m-%d_%H:00')
    
    # Create data directory if it doesn't exist
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    file_path = data_dir / f"{symbol}_{timestamp_str}.csv"
    
    logger.debug(f"Saving data to {file_path}")
    
    try:
        total_candles = 0
        for candles in candle_data.values():
            if isinstance(candles, dict) and 'time' in candles:
                total_candles += len(candles.get('time', []))
            elif isinstance(candles, list):
                total_candles += len(candles)
        
        logger.info(f"Writing {total_candles} candles to CSV for {symbol}")
        
        with file_path.open('w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Symbol', 'FundingTime', 'Interval', 'Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])

            for interval, candles in candle_data.items():
                # Handle dictionary format
                if isinstance(candles, dict) and 'time' in candles:
                    time_values = candles.get('time', [])
                    open_values = candles.get('open', [])
                    high_values = candles.get('high', [])
                    low_values = candles.get('low', [])
                    close_values = candles.get('close', [])
                    vol_values = candles.get('vol', [])
                    
                    for i in range(len(time_values)):
                        if i < len(open_values) and i < len(high_values) and i < len(low_values) and i < len(close_values) and i < len(vol_values):
                            timestamp = int(time_values[i]) // 1000 if isinstance(time_values[i], str) else time_values[i] // 1000
                            writer.writerow([
                                symbol,
                                funding_time.isoformat(),
                                interval,
                                datetime.fromtimestamp(timestamp, timezone.utc).isoformat(),
                                open_values[i],
                                high_values[i],
                                low_values[i],
                                close_values[i],
                                vol_values[i]
                            ])
                # Handle list format
                elif isinstance(candles, list):
                    for candle in candles:
                        timestamp = int(candle[0]) // 1000 if isinstance(candle[0], str) else candle[0] // 1000
                        writer.writerow([
                            symbol,
                            funding_time.isoformat(),
                            interval,
                            datetime.fromtimestamp(timestamp, timezone.utc).isoformat(),
                            *candle[1:]
                        ])
        
        logger.info(f"Successfully saved data to {file_path}")
    except Exception as e:
        logger.error(f"Error saving data to CSV for {symbol}: {e}")
        raise
