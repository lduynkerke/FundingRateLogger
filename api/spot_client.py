"""
MEXC Spot API client module.

This module provides functionality for interacting with the MEXC spot market API.
It handles retrieving OHLCV (candlestick) data for spot trading pairs with proper
error handling and logging.

The module extends the base client functionality to work specifically with
the spot market endpoints of the MEXC exchange.
"""

from typing import List
from api.base_client import BaseMEXCClient


class MEXCSpotClient(BaseMEXCClient):
    """
    Client for MEXC spot market data (public endpoints).
    """

    def __init__(self, config: dict):
        super().__init__(config=config, market="spot")

    def get_spot_ohlcv(self, symbol: str, interval: str = "1m", limit: int = 1) -> List[list]:
        """
        Fetches OHLCV (candlestick) data for a given spot symbol.

        :param symbol: Symbol name (e.g., 'BTCUSDT').
        :type symbol: str
        :param interval: Interval string like '1m', '5m'.
        :type interval: str
        :param limit: Number of candles to retrieve.
        :type limit: int
        :return: List of [timestamp, open, high, low, close, volume]
        :rtype: list[list]
        """
        self.logger.debug(f"Fetching OHLCV data for {symbol}, interval={interval}, limit={limit}")
        
        try:
            endpoint = f"{self.base_url}/api/v3/klines"
            params = {"symbol": symbol, "interval": interval, "limit": limit}
            result = self._get(endpoint, params=params)
            
            if isinstance(result, dict) and 'success' in result:
                if result.get('success') is False:
                    error_code = result.get('code', 'unknown')
                    error_msg = result.get('message', 'No error message provided')
                    self.logger.error(f"Error fetching OHLCV data for {symbol}: code={error_code}, message={error_msg}")
                    return []
                
                # If success is True, return the data field
                data = result.get('data', [])
                self.logger.debug(f"Successfully fetched OHLCV data for {symbol}")
                return data
            
            self.logger.debug(f"Successfully fetched {len(result) if isinstance(result, list) else 'unknown'} OHLCV candles for {symbol}")
            return result
        except Exception as e:
            self.logger.error(f"Error fetching OHLCV data for {symbol}: {e}")
            raise
