# -*- coding: utf-8 -*-
"""
Created on Wed May 22 14:38:55 2024

@author: dalil
"""

import asyncio
from typing import  List, Tuple, Dict

from src.exchanges.common.websocket import WebsocketStream
from src.exchanges.hyperliquid.endpoints import HyperliquidEndpoints

from src.exchanges.hyperliquid.ws_handlers.candle import HlCandleHandler
from src.exchanges.hyperliquid.ws_handlers.orderbook import HlOrderBookHandler
from src.exchanges.hyperliquid.ws_handlers.orders import HlOrdersHandler
from src.exchanges.hyperliquid.ws_handlers.position import HlPositionHandler
from src.exchanges.hyperliquid.ws_handlers.ticker import HlTickerHandler
from src.exchanges.hyperliquid.ws_handlers.trades import HlTradesHandler
from src.exchanges.hyperliquid.exchange import Hyperliquid


class HlWebsocket(WebsocketStream):
    
    def __init__(self, exch: Hyperliquid) -> None:
        super().__init__()
        self.exch = exch
        self.is_mainnet = exch.is_mainnet
        self.endpoints = HyperliquidEndpoints

    def create_handlers(self) -> None:
        position_handler = HlPositionHandler(self.data, self.exch.account_address, logging = self.logging.createChild("positionHandler"))
        self.public_handler_map = {
            "l2Book" : HlOrderBookHandler(self.data["orderbook"]),
            "trades": HlTradesHandler(self.data["trades"]),
            "webData2":position_handler,
            "orderUpdates":HlOrdersHandler(self.data,logging = self.logging.createChild("orderHandler")),
            "userFills":position_handler,
            "candle":HlCandleHandler(self.data["ohlcv"]),
            "activeAssetCtx": HlTickerHandler(self.data["ticker"],self.symbol)
            }

    async def refresh_orderbook_data(self, timer: int = 600) -> None:
        while True:
            orderbook_data = await self.exch.get_orderbook(self.symbol)
            self.public_handler_map["l2Book"].refresh(orderbook_data)
            await asyncio.sleep(timer)

    async def refresh_trades_data(self, timer: int = 600) -> None:
        pass

    async def refresh_ohlcv_data(self, timer: int = 600) -> None:
        while True:
            ohlcv_data = await self.exch.get_ohlcv(self.symbol)
            self.public_handler_map["candle"].refresh(ohlcv_data)
            await asyncio.sleep(timer)

    async def refresh_ticker_data(self, timer: int = 600) -> None:
        while True:
            ticker_data = await self.exch.get_ticker()
            self.public_handler_map["activeAssetCtx"].refresh(ticker_data)
            await asyncio.sleep(timer)
    
    async def refresh_position_data(self, timer: int = 600 ) -> None:
        while True:
            position_data = await self.exch.get_position()
            self.public_handler_map["webData2"].refresh(position_data)
            await asyncio.sleep(timer)    
            
    def public_stream_sub(self) -> Tuple[str, List[Dict]]:
        subs = [
            {"type": "trades", "coin": self.symbol},
            {"type": "l2Book", "coin": self.symbol},
            {"type": "candle", "coin": self.symbol, "interval": "1m"},
            {"type": "webData2", "user": self.exch.account_address},
            {"type": "activeAssetCtx", "coin": self.symbol},
            { "type": "userFills", "user": self.exch.account_address },
            { "type": "orderUpdates", "user": self.exch.account_address }
        ]

        request = [{"method": "subscribe", "subscription": sub} for sub in subs]

        return (self.endpoints["pub_ws"] if self.is_mainnet else self.endpoints["test_ws"], request)

    async def public_stream_handler(self, recv: Dict) -> None:
        try:
            topic = recv["channel"]
            if topic == "orderUpdates" or topic == "userFills":
                self.logging.debug(recv)
            self.public_handler_map[topic].process(recv)

        except KeyError as ke:
            if topic == "subscriptionResponse":
                if recv["data"]["method"] == "subscribe":
                    self.logging.info(f"Subscription successful to: {recv['data']['subscription']['type']}")
                elif recv["data"]["method"] == "unsubscribe":
                    self.logging.info(f"Unsubscribed from: {recv['data']['subscription']['type']}")         
            else:
                raise ke

        except Exception as e:
            raise e

    async def start_public_stream(self) -> None:
        """
        Initializes and starts the public Websocket stream.
        """
        try:
            url, requests = self.public_stream_sub()
            await self.start_public_ws(url, self.public_stream_handler, requests)
        except Exception as e:
            await self.logging.error( f"Public stream: {e}")
            
    async def private_stream_sub(self) -> Tuple[str, List[Dict]]:
        """
        Everything public on Hl
        """
        pass

    async def private_stream_handler(self, recv: Dict) -> None:
        """
        Everything public on Hl
        """
        pass


    async def start(self):
        self.create_handlers()
        await asyncio.gather(
            self.refresh_orderbook_data(),
            self.refresh_ohlcv_data(),
            self.refresh_ticker_data(),
            self.refresh_position_data(),
            self.start_public_stream(),
        )
    # marketdatalogger = logging.getLogger(__name__)
    # marketdatalogger.setLevel(logging.DEBUG)
    # date = datetime.today()
    # datestring = date.strftime("%Y-%m-%d")
    # cwd = os.getcwd()
    # logbasepath = os.path.join(cwd, f'logs/{datestring}')
    # os.makedirs(logbasepath,exist_ok = True)
    # marketdatalogger.propagate = False  # Prevent propagation to the root logger
    # handler_map = {"l2Book" : logging.FileHandler(f'{logbasepath}/l2Book.log'),
    #                "trades": logging.FileHandler(f'{logbasepath}/trades.log'),
    #                "userEvents":logging.FileHandler(f'{logbasepath}/userEvents.log'),
    #                "orderUpdates":logging.FileHandler(f'{logbasepath}/orderUpdates.log'),
    #                "userFills":logging.FileHandler(f'{logbasepath}/userFills.log'),
    #                "allMids":logging.FileHandler(f'{logbasepath}/allMids.log'),
    #                "candle":logging.FileHandler(f'{logbasepath}/candle.log'),
    #                "userHistoricalOrders": logging.FileHandler(f'{logbasepath}/userHistoricalOrders.log'),
    #                }
    
    # general_formatter = logging.Formatter('%(message)s')
    # for key in handler_map:
    #     currentHandler = handler_map[key]
    #     currentHandler.setFormatter(general_formatter)
    #     handler_map[key] = currentHandler
    
    # def __init__(self,base_url=None, skip_ws=False, SharedState=None):
        
    #     # All Info() methods available for use in this class
        
    #     #super().__init__(base_url,skip_ws)
    #     self.ss = SharedState
    #     self.data = self.ss.data
    #     self.coin_to_asset = {asset_info["name"]: asset for (asset, asset_info) in enumerate(self.info.meta()["universe"])}
    #     # spot assets start at 10000
    #     for spot_pair in self.info.spot_meta()["tokens"]:
    #         self.coin_to_asset[spot_pair["name"]] = spot_pair["index"] + 10000
    
    # def generate_subscription_request(self, topics : List[str], **kwargs) -> List[Tuple[str, Callable[[str],Any]]]:  
    #     """
    # Constructs and returns list containing a tuples of subscriptions and their corresponding "on message" handlers

    # Parameters
    # ----------
    # topics : List[str]
    #     A list of topics to subscribe to. Supported topics include "Trades", "Orderbook", "BBA", and "Kline".
    
    # **kwargs : dict
    #     Additional keyword arguments for specific subscriptions, such as the interval for "Kline" topics.

    # Returns
    # -------
    # List[Tuple[str, Callable[[str],...]]]
    #     A tuple containing the WebSocket URL (str) and a list of stream topics (List[str]).
        
    # Notes
    # -----
    # - The "candle" topic requires an "interval" keyword argument.
    # - The URL and topics are constructed based on the Binance WebSocket API documentation.
    # """  
    #     subList = list()  
    #     coin = kwargs.get('coin')
    #     address = kwargs.get('address')
    #     interval = kwargs.get('interval')
        
    #     for topic in topics:
            
    #         if topic == "l2Book":
    #             if coin:
    #                 subscription: Subscription = { "type": "l2Book", "coin": str(coin) }
    #                 subList.append((subscription, self.book_handler))
                
    #         elif topic == "trades":
    #             if coin:
    #                 subscription: Subscription = { "type": "trades", "coin": str(coin) }
    #                 subList.append((subscription, self.trades_handler))
                 
    #         elif topic == "user":
    #             if address:
    #                 subList.append(({ "type": "user", "user": str(address) }, self.userEvents_handler))
                        
    #         elif topic == "candle":
    #             if coin and interval:
    #                 subList.append(({ "type": "candle", "coin": str(coin), "interval": str(interval) }, self.candle_handler))
                           
    #         elif topic == "allMids":
    #             subList.append(({ "type": "allMids" }, self.allMids_handler))
                           
    #         elif topic == "orderUpdates":
    #             if address:
    #                 subList.append(({ "type": "orderUpdates", "user": str(address) },self.orderUpdates_handler))
                            
    #         elif topic == "userFills":
    #             if address:
    #                 subList.append(({ "type": "userFills", "user": str(address) },self.userFills_handler))
                    
    #         elif topic == "webData2":
    #             if address:
    #                 subList.append(({ "type": "webData2", "user": str(address) }, self.webData2_handler))
                
    #         elif topic == "userFundings":
    #             if address:
    #                 subList.append(({ "type": "userFundings", "user": str(address) },self.userFundings_handler))
                
    #         elif topic == "userNonFundingLedgerUpdates":
    #             if address:
    #                 subList.append(({ "type": "userNonFundingLedgerUpdates", "user": str(address) }, self.userNFLUpdates_handler))  
                
    #         elif topic == "notification":
    #             if address:
    #                 subList.append(({ "type": "notification", "user": str(address) }, self.notification_handler))
            
    #         elif topic == "userHistoricalOrders":
    #             if address:  
    #                 subList.append(({ "type": "userHistoricalOrders", "user": str(address) }, self.userHistoricalOrders_handler))
    #     return subList
                
    # def book_handler(self,msg):

    #     self._set_handlers(self.handler_map['l2Book'])
    #     self.marketdatalogger.debug(msg)
        
    # def trades_handler(self,msg):

    #     self._set_handlers(self.handler_map['trades'])
    #     self.marketdatalogger.debug(msg)
        
    # def userEvents_handler(self,msg):

    #     self._set_handlers(self.handler_map['userEvents'])
    #     self.marketdatalogger.debug(msg)
        
    # def candle_handler(self,msg):

    #     self._set_handlers(self.handler_map['candle'])
    #     self.marketdatalogger.debug(msg)
        
    # def allMids_handler(self,msg):

    #     self._set_handlers(self.handler_map['allMids'])
    #     self.marketdatalogger.debug(msg)
        
    # def orderUpdates_handler(self,msg):

    #     self._set_handlers(self.handler_map['orderUpdates'])
    #     self.marketdatalogger.debug(msg)
        
    # def userFills_handler(self,msg):

    #     self._set_handlers(self.handler_map['userFills'])
    #     self.marketdatalogger.debug(msg)
    
    # def userHistoricalOrders_handler(self,msg):
    #     self._set_handlers(self.handler_map['userHistoricalOrders'])
    #     self.marketdatalogger.debug(msg)
       
    # def webData2_handler(self):
    #     pass
    # def userFundings_handler(self):
    #     pass
    # def userNFLUpdates_handler(self):
    #     pass
    # def notification_handler(self):
    #     pass
    # def _set_handlers(self, handler):
    #     # Remove all existing handlers
    #     if self.marketdatalogger.hasHandlers():
    #         self.marketdatalogger.handlers.clear()
        
    #     # Add the new handler
    #     self.marketdatalogger.addHandler(handler)
        
    # def close_logs(self):
    #     for _,handler in self.handler_map.items():
    #         handler.close()
    