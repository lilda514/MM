from hyperliquid.aexchange import aExchange
from hyperliquid.ainfo import aInfo
from hyperliquid.utils.signing import OrderRequest

from src.exchanges.common.types import Side, OrderType, TimeInForce, Order
from src.exchanges.hyperliquid.endpoints import HyperliquidEndpoints
from src.exchanges.hyperliquid.types import HlSideConverter, HlOrderTypeConverter, HlTimeInForceConverter, HlPositionDirectionConverter
from src.exchanges.hyperliquid.orderid import HlOrderIdGenerator, Cloid
from src.tools.misc import time_ms
from src.tools.log import LoggerInstance

from typing import Dict, Union, List
import eth_account
import asyncio

class Hyperliquid(aExchange,aInfo):
    """
    We are still using the provided SDK for this exchange so need to wrap provided methods with our own
    for integration with market making module.
    """  
    def __init__(self, secret_key: str, is_mainnet = True):
        
        self.type_converter = HlOrderTypeConverter()
        self.side_converter = HlSideConverter()
        self.tif_converter = HlTimeInForceConverter()
        self.pos_dir_converter = HlPositionDirectionConverter()
        self.endpoints = HyperliquidEndpoints
        self.orderid = HlOrderIdGenerator()
        
        super().__init__(
            wallet = eth_account.Account.from_key(str(secret_key)),
            base_url = self.endpoints["main1"] if is_mainnet else self.endpoints["test1"],
            account_address = eth_account.Account.from_key(str(secret_key)).address,
            )
    def load_required_refs(self, logging: LoggerInstance, symbol: str, data: Dict) -> None:
        """
        Loads required references such as logging, symbol, and data.

        Parameters
        ----------
        logging : Logger
            The Logger instance for logging events and messages.

        symbol : str
            The trading symbol.

        data : Dict
            A Dictionary holding various shared state data.
        """
        self.logging = logging
        logger_name = self.logging.name
        separated_names = logger_name.split(".")
        self.logging.setFilters(separated_names[-2] + "." + "EXCH") #Topic is "{Exchange_name}.exchange"
        self.logging.setHandlers()
        self.symbol = symbol
        self.data = data
    
    async def format_orders(self, orders: List[Order]) -> List[Dict]:
        
        orderlist = []
        
        for order in orders:
            orderdict : OrderRequest = {
                                    "coin": order.symbol,
                                    "is_buy": True if  order.side == Side.BUY else False,
                                    "sz": order.size,
                                    "limit_px": None,
                                    "order_type": dict() ,
                                    "reduce_only": order.reduceOnly,
                                    }
            if isinstance(order.clientOrderId, Cloid):
                orderdict["cloid"] = order.clientOrderId
            
            match order.orderType:
                case OrderType.MARKET:
                    orderdict["order_type"] = {"limit":{"tif":"Ioc"}}
                    orderdict["limit_px"] = await self._slippage_price(order.symbol, orderdict["is_buy"], self.DEFAULT_SLIPPAGE)
                    orderdict["reduce_only"] = False if order.reduceOnly is None else order.reduceOnly
                
                case OrderType.LIMIT:
                    
                    orderdict["order_type"] = {"limit":{"tif": self.tif_converter.to_str(order.timeInForce)}}
                    orderdict["limit_px"] = order.price
                
                case OrderType.STOP_LIMIT:
                    if order.trig_px != None:
                        orderdict["order_type"] = {"trigger":{"isMarket":False,"triggerPx":order.trig_px, "tpsl":"sl"}}
                        orderdict["limit_px"] = order.price
                
                case OrderType.TAKE_PROFIT_LIMIT:
                    if order.trig_px != None:
                        orderdict["order_type"] = {"trigger":{"isMarket":False, "triggerPx":order.trig_px,"tpsl":"tp"}}
                        orderdict["limit_px"] = order.price
                
                case OrderType.STOP_MARKET:
                    if order.trig_px != None:
                        orderdict["order_type"] = {"trigger":{"isMarket":True, "triggerPx":order.trig_px,"tpsl":"sl"}}
                        orderdict["limit_px"] = order.price
                
                case OrderType.TAKE_PROFIT_MARKET:
                    if order.trig_px != None:
                        orderdict["order_type"] = {"trigger":{"isMarket":True, "triggerPx":order.trig_px,"tpsl":"tp"}}
                        orderdict["limit_px"] = order.price
                        
            orderlist.append(orderdict)
        return orderlist
        
    async def create_order(self, order: Order) -> Dict:
        result = await self.bulk_orders(await self.format_orders([order]))

        return {
                order.clientOrderId.to_raw(): (False if "error" in response else True, response) 
                for response in result["response"]["data"]["statuses"]
                }
    
    async def batch_create_orders(self, orders: List[Order]) -> Dict:
        
        if not isinstance(orders, list):
            orders = list(orders)
        #THIS ASSUMES THE RESPONSES WILL ALWAYS BE IN THE SAME ORDER THEY WERE SENT IN ORDERS CAREFUL!!!
        result = await self.bulk_orders(await self.format_orders(orders))
        return {
                orders[index].clientOrderId.to_raw(): (False if "error" in response else True, response) 
                for index,response in enumerate(result["response"]["data"]["statuses"])
                }
        
    async def amend_order(self, new_order: Order) -> Dict:
        """
        Abstract method to amend an existing order.

        Parameters
        ----------
        order: Order
            The order to modify/amend.

        Returns
        -------
        Dict
            The response from the exchange.
        """
        neworder = await self.format_orders([new_order])
        
        #THIS ASSUMES THE RESPONSES WILL ALWAYS BE IN THE SAME ORDER THEY WERE SENT IN ORDERS CAREFUL!!!
        result = await self.bulk_modify_orders_new({"oid": new_order.orderId ,"order" : neworder[0]})
        return {
                new_order.clientOrderId.to_raw(): (False if "error" in response else True, response) 
                for response in result["response"]["data"]["statuses"]
                }
    
    async def batch_amend_orders(self, new_orders: List[Order]) -> Dict:
        """
        Abstract method to amend an existing order.

        Parameters
        ----------
        new_orders: List[Order]
            List of orders to modify/amend.

        Returns
        -------
        Dict
            The response from the exchange.
        """
        if not isinstance(new_orders, list):
            new_orders = list(new_orders)
        new_orders_list = await self.format_orders(new_orders)
        amend_list = [{"oid":order_object.orderId,"order": order} for order_object,order in zip(new_orders,new_orders_list)]   
        result = await self.bulk_modify_orders_new(amend_list)
        
        #THIS ASSUMES THE RESPONSES WILL ALWAYS BE IN THE SAME ORDER THEY WERE SENT IN ORDERS CAREFUL!!!
        return {
                new_orders[index].clientOrderId.to_raw(): (False if "error" in response else True, response) 
                for index,response in enumerate(result["response"]["data"]["statuses"])
                }
            

    async def cancel_order(self, order: Union[Order,int], symbol: str = None) -> Dict:
        """
        Abstract method to cancel an existing order.

        Parameters
        ----------
        order: Order
            The order to cancel.

        Returns
        -------
        Dict
            The response from the exchange.
        """
        if isinstance(order,Order):
            
            result = await self.bulk_cancel_by_cloid([{"coin": order.symbol, "cloid": order.clientOrderId}])
            #THIS ASSUMES THE RESPONSES WILL ALWAYS BE IN THE SAME ORDER THEY WERE SENT IN ORDERS CAREFUL!!!
            return {
                    order.clientOrderId.to_raw(): (False if "error" in response else True, response) 
                    for response in result["response"]["data"]["statuses"]
                    }
        
        elif isinstance(order, int):
            result = await self.bulk_cancel([{"coin": symbol, "oid": order}])
            #THIS ASSUMES THE RESPONSES WILL ALWAYS BE IN THE SAME ORDER THEY WERE SENT IN ORDERS CAREFUL!!!
            return {
                    order : (False if "error" in response else True, response) 
                    for response in result["response"]["data"]["statuses"]
                    }
    
    async def batch_cancel_orders(self, orders: List[Union[Order,int]]) -> Dict:
        
        if not isinstance(orders, list):
            orders = list(orders)
        
        to_cancel = [{"coin":order.symbol,
                      "oid":order.orderId} 
                     for order in orders ]
        result = await self.bulk_cancel(to_cancel)    
        
        #THIS ASSUMES THE RESPONSES WILL ALWAYS BE IN THE SAME ORDER THEY WERE SENT IN ORDERS CAREFUL!!!
        return {
                orders[index].clientOrderId.to_raw(): (False if "error" in response else True, response) 
                for index,response in enumerate(result["response"]["data"]["statuses"])
                }
    
        
    async def cancel_all_orders(self, symbol: str) -> Dict:
        """
        Abstract method to cancel all existing orders for a symbol.

        Parameters
        ----------
        symbol : str
            The trading symbol.

        Returns
        -------
        Dict
            The response from the exchange.
        """
        open_orders_list = []
        for open_order in await self.open_orders(self.account_address):
            if open_order["coin"] != symbol:
                continue
            open_orders_list.append({"coin": symbol, "oid":open_order["oid"]})
        
        result = await self.bulk_cancel(open_orders_list)
        return{
            open_orders_list[index]["oid"]: (False if "error" in response else True, response) 
            for index,response in enumerate(result["response"]["data"]["statuses"])
            }

    async def get_ohlcv(self, symbol: str, interval: Union[int, str] = "1m") -> Dict:
        """
        Abstract method to get OHLCV (Open, High, Low, Close, Volume) data.

        Parameters
        ----------
        symbol : str
            The trading symbol.

        interval : Union[int, str]
            The interval for the OHLCV data.

        Returns
        -------
        Dict
            The OHLCV data from the exchange.
        """
        candle_no = 5000
        start_time = time_ms()
        min_to_ms = 60*1000
        match interval:
            case "1m":
                time_delta = min_to_ms
            case "3m":
                time_delta = 3*min_to_ms
            case "5m":
                time_delta = 5*min_to_ms
            case "15m":
                time_delta = 15*min_to_ms
            case "30m":
                time_delta = 30*min_to_ms
            case "1h":
                time_delta = 60*min_to_ms
            case "2h":
                time_delta = 2*min_to_ms
            case "4h":
                time_delta = 4*60*min_to_ms
            case "8h":
                time_delta = 8*60*min_to_ms
            case "12h":
                time_delta = 12*60*min_to_ms
            case "1d":
                time_delta = 24*60*min_to_ms
        return await self.candles_snapshot(symbol, interval, start_time - candle_no*time_delta, start_time)
        
    async def get_trades(self, symbol: str) -> Dict:
        """
        Abstract method to get recent trades.

        Parameters
        ----------
        symbol : str
            The trading symbol.

        Returns
        -------
        Dict
            The trades data from the exchange.
        
        No such post request on hyperliquid
        """
        pass

    async def get_orderbook(self, symbol: str) -> Dict:
        """
        Abstract method to get an orderbook snapshot.

        Parameters
        ----------
        symbol : str
            The trading symbol.

        Returns
        -------
        Dict
            The order book data from the exchange.
        """
        return await self.l2_snapshot(symbol)

    async def get_ticker(self) -> Dict:
        """
        Abstract method to get ticker data.

        Parameters
        ----------
        symbol : str
            The trading symbol.

        Returns
        -------
        Dict
            The ticker data from the exchange.
        """
        return await self.metaAndAssetCtxs()

        
    async def get_open_orders(self) -> Dict:
        """
        Abstract method to get open orders.

        Parameters
        ----------
        symbol : str
            The trading symbol.

        Returns
        -------
        Dict
            The open orders data from the exchange.
        """
        return await self.frontend_open_orders(self.account_address)

    async def get_position(self) -> Dict:
        """
        Abstract method to get current position data.

        Parameters
        ----------
        symbol : str
            The trading symbol.

        Returns
        -------
        Dict
            The position data from the exchange.
        """
        usr_state = await self.user_state(self.account_address)
    
        return usr_state["assetPositions"]
    
    async def L1_rate_limit(self,account_addr = None) -> Dict:
        return await self.post("/info", {"type": "userRateLimit","user":account_addr if account_addr is not None else self.account_address})
    
    async def warmup(self)-> None:
        
        #There is no tick size on hyperliquid, this is simply for conformity with other exchanges and integration with rest of system
        self.data["tick_size"] = 1.23
        
        metaAndAssetCtxs = await self.get_ticker()
        meta = metaAndAssetCtxs[0]["universe"]
        for asset in meta:
            if asset["name"] == self.symbol: 
                sz_dec = float(asset["szDecimals"])
                self.data["lot_size"] =  10**-sz_dec
                self.data["max_leverage"] = float(asset["maxLeverage"])
                break

        self.logging.info("Hyperliquid warmup sequence complete.")

    async def shutdown(self) -> None:
        """
        Initiates the shutdown sequence for the exchange.

        This method performs the following tasks:

        1. Cancels all open orders for the specified symbol by sending multiple asynchronous cancellation requests.
        2. Creates a new market order to close the current position, if any, for the specified symbol.

        The method handles exceptions as follows:

        - If a KeyError is raised, it logs an informational message indicating that no position was found and skips the order creation step.
        - If any other exception is raised, it logs an error message with the exception details and re-raises the exception.

        The method ensures that a final log message is written to indicate the completion of the shutdown sequence.

        Raises
        ------
        Exception
            If an unexpected error occurs during the shutdown process.
        """
        try:
            tasks = []

            for attempt in range(3):
                self.logging.debug(
                   f"Cancel all, attempt {attempt}"
                )
                tasks.append(self.cancel_all_orders(self.symbol))

            if self.data["position"].size:
                delta_neutralizer_orderid = self.orderid.generate_order_id()

                for attempt in range(3):
                    self.logging.debug(
                        f"Delta neutralizer, attempt {attempt}"
                    )
                    tasks.append(
                        self.create_order(
                            Order(
                                symbol=self.symbol,
                                side=(
                                    Side.BUY
                                    if self.data["position"].size < 0.0
                                    else Side.SELL
                                ),
                                orderType=OrderType.MARKET,
                                size=self.data["position"].size,
                                reduceOnly=True,
                                clientOrderId=delta_neutralizer_orderid,
                            )
                        )
                    )

            await asyncio.gather(*tasks)

        except KeyError:
            self.logging.info("No position found, skipping...")

        except Exception as e:
            self.logging.error(f"Shutdown sequence: {e}")
            raise e

        finally:
            await self.session.close()
            self.logging.info("Shutdown sequence complete.")
