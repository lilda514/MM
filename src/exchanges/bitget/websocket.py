import asyncio
from typing import Tuple, Dict, List, Any
import hashlib
import hmac
import base64

from src.tools.misc import time_ms
from src.exchanges.common.websocket import WebsocketStream
from src.exchanges.bitget.exchange import Bitget
from src.exchanges.bitget.endpoints import BitgetEndpoints
from src.exchanges.bitget.ws_handlers.orderbook import BitgetOrderbookHandler
from src.exchanges.bitget.ws_handlers.trades import BitgetTradesHandler
from src.exchanges.bitget.ws_handlers.markprice import BitgetTickerHandler
from src.exchanges.bitget.ws_handlers.ohlcv import BitgetOhlcvHandler
from src.exchanges.bitget.ws_handlers.orders import BitgetOrdersHandler
from src.exchanges.bitget.ws_handlers.position import BitgetPositionHandler


class BitgetWebsocket(WebsocketStream):
    """
    Handles Websocket connections and data management for Binance.
    """

    def __init__(self, exch: Bitget, ws_record = False) -> None:
        super().__init__(ws_record = ws_record)
        self.exch = exch
        self.endpoints = BitgetEndpoints()
        self.trading_access = self.exch.trading_access
        
        if not self.trading_access:
            self._disable_trading_methods()      

    def create_handlers(self) -> None:
        self.public_handler_map = {
            "books": BitgetOrderbookHandler(self.data),
            "trade": BitgetTradesHandler(self.data),
            "candle1m": BitgetOhlcvHandler(self.data),
            "ticker": BitgetTickerHandler(self.data),
        }
        self.public_handler_map["bookTicker"] = self.public_handler_map["depthUpdate"]
        
        if self.trading_access: 
            self.private_handler_map = {
                "orders": BitgetOrdersHandler(self.data, self.symbol),
                "positions": BitgetPositionHandler(self.data, self.symbol),
            }

    async def refresh_orderbook_data(self, timer: int = 600) -> None:
        while True:
            orderbook_data = await self.exch.get_orderbook(self.symbol)
            self.public_handler_map["depthUpdate"].refresh(orderbook_data)
            await asyncio.sleep(timer)

    async def refresh_trades_data(self, timer: int = 600) -> None:
        while True:
            trades_data = await self.exch.get_trades(self.symbol)
            self.public_handler_map["trade"].refresh(trades_data)
            await asyncio.sleep(timer)

    async def refresh_ohlcv_data(self, timer: int = 600) -> None:
        while True:
            ohlcv_data = await self.exch.get_ohlcv(self.symbol, "1m")
            self.public_handler_map["kline"].refresh(ohlcv_data)
            await asyncio.sleep(timer)

    async def refresh_ticker_data(self, timer: int = 600) -> None:
        while True:
            ticker_data = await self.exch.get_ticker(self.symbol)
            self.public_handler_map["markPriceUpdate"].refresh(ticker_data)
            await asyncio.sleep(timer)

    def public_stream_sub(self) -> Tuple[str, List[Dict[str, Any]]]:
        request = [
            {
            "op": "subscribe",
            "args": [
                {   
                    "instType": "USDT-FUTURES",
                    "channel": "ticker",
                    "instId": "BTCUSDT"
                },
                {
                    "instType": "USDT-FUTURES",
                    "channel": "candle1m",
                    "instId": "BTCUSDT"
                },
                {
                    "instType": "USDT-FUTURES",
                    "channel": "books5",
                    "instId": "BTCUSDT"
                },
                {
                    "instType": "USDT-FUTURES",
                    "channel": "trade",
                    "instId": "BTCUSDT"
                },
                ],

            }
        ]
        return (self.endpoints.public_ws.url, request)

    async def public_stream_handler(self, recv: Dict[str, Any]) -> None:
        try:
            self.public_handler_map[recv["e"]].process(recv)

        except KeyError as ke:
            if "id" not in recv:
                raise ke

        except Exception as e:
            await self.logging.error(f"Binance public ws handler: {e}")

    async def private_stream_sub(self) -> Tuple[str, List[Dict[str, Any]]]:
        
        timestamp = time_ms()//1000
        hash_signature = hmac.new(
            key=self.exch.api_secret.encode(),
            msg= f"{timestamp}GET/user/verify".encode(),
            digestmod=hashlib.sha256,
        )
        
        signature = str(base64.b64encode(hash_signature.digest()), 'utf8')

        auth_msg = {
            "op": "login",
            "args": [
                {
                    "apiKey": self.exch.api_key,
                    "passphrase":self.exch.passphrase,
                    "timestamp": f"{timestamp}",
                    "sign": signature
                }   
            ]
        }       

        sub_msg = {
            "op": "subscribe",
            "args": [
                {   
                    "instType": "USDT-FUTURES",
                    "channel":"positions",
                    "coin": "default",
                },
                {
                    "instType": "USDT-FUTURES",
                    "channel":"orders",
                    "instId": "default",
                }
            ],
        }

        return (self.endpoints.private_ws.url, [auth_msg, sub_msg])

    async def private_stream_handler(self, recv: Dict[str, Any]) -> None:
        try:
            self.private_handler_map[recv["e"]].process(recv)

        except KeyError as ke:
            if "listenKey" not in recv:
                raise ke

        except Exception as e:
            await self.logging.error(f"Binance private ws handler: {e}")


    async def start_public_stream(self) -> None:
        """
        Initializes and starts the public Websocket stream.
        """
        try:
            url, requests = self.public_stream_sub()
            await self.start_public_ws(url, self.public_stream_handler, requests, ping_timer = 20.0)
        except Exception as e:
            await self.logging.error(f"Binance Public Ws: {e}")

    async def start_private_stream(self) -> None:
        """
        Initializes and starts the private Websocket stream.
        """
        try:
            url, requests = await self.private_stream_sub()
            await self.start_private_ws(url, self.private_stream_handler, requests, ping_timer = 20.0)
        except Exception as e:
            await self.logging.error(f"Binance Private Ws: {e}")
            

    async def start(self) -> None:
        """
        Starts all necessary asynchronous tasks for Websocket stream management and data refreshing.
        """
        self.create_handlers()
        tasks = [
                self.refresh_orderbook_data(),
                self.refresh_trades_data(),
                self.refresh_ohlcv_data(),
                self.refresh_ticker_data(),
                self.start_public_stream(),]
        if self.trading_access:
            tasks += [   
                self.start_private_stream(),
                self.ping_listen_key()
                ]
        await asyncio.gather(*tasks)
