from typing import List, Dict, Optional
# from src.tools.log import LoggerInstance
from src.exchanges.common.types import Order
from src.exchanges.common.exchange import Exchange
from src.exchanges.bitget.endpoints import BitgetEndpoints
from src.exchanges.bitget.formats import BitgetFormats
from src.exchanges.bitget.client import BitgetClient
from src.exchanges.bitget.orderid import BitgetOrderIdGenerator

class Bitget(Exchange):
    def __init__(self, api_key: str, api_secret: str, passphrase: str) -> None:
        self.api_key = api_key
        self.api_secret = api_secret
        self.passphrase = passphrase

        super().__init__(
            client=BitgetClient(self.api_key, self.api_secret, self.passphrase),
            formats=BitgetFormats(),
            endpoints=BitgetEndpoints(),
            orderIdGenerator=BitgetOrderIdGenerator()
        )
        if not self.trading_access:
            self._disable_trading_methods()        
    
    async def create_order(
        self,
        order
    ) -> Dict:
        endpoint = self.endpoints.createOrder
        _format = self.formats.create_order(order)
        signature = self.client.sign(endpoint.method, self.base_endpoint.url, endpoint.url, _format)
        headers = self.client.base_headers.update({"ACCESS-SIGN": signature})
        return await self.client.request(
            url=self.base_endpoint.url + endpoint.url,
            method=endpoint.method,
            params=_format["params"],
            headers=headers,
            data=_format["body"],
            signed=True,
        )
    
    async def batch_create_orders(
        self,
        orders: List[Order]
    ) -> Dict:
        endpoint = self.endpoints.batchCreateOrders
        _format = self.formats.batch_create_orders(orders)
        signature = self.client.sign(endpoint.method, self.base_endpoint.url, endpoint.url, _format )
        headers = self.client.base_headers.update({"ACCESS-SIGN": signature})
        return await self.client.request(
            url=self.base_endpoint.url + endpoint.url,
            method=endpoint.method,
            params=_format["params"],
            headers=headers,
            data=_format["body"],
            signed=True,
        )

    async def amend_order(
        self, order
    ) -> Dict:
        endpoint = self.endpoints.amendOrder
        _format = self.formats.amend_order(order)
        signature = self.client.sign(endpoint.method, self.base_endpoint.url, endpoint.url, _format )
        headers = self.client.base_headers.update({"ACCESS-SIGN": signature})
        return await self.client.request(
            url=self.base_endpoint.url + endpoint.url,
            method=endpoint.method,
            params=_format["params"],
            headers=headers,
            data=_format["body"],
            signed=True,
        )
    
    #Unavailable on BITGET
    # async def batch_amend_orders(
    #     self,
    #     orders: List[Order]
    # ) -> Dict:
    #     endpoint = self.endpoints.batchAmendOrders
    #     headers = self.formats.batch_amend_orders(orders)
    #     return await self.client.request(
    #         url=self.base_endpoint.url + endpoint.url,
    #         method=endpoint.method,
    #         headers=self.client.base_headers,
    #         data=self.client.sign_headers(endpoint.method, headers),
    #         signed=True,
    #     )

    async def cancel_order(self, order) -> Dict:
        endpoint = self.endpoints.cancelOrder
        _format = self.formats.cancel_order(order)
        signature = self.client.sign(endpoint.method, self.base_endpoint.url, endpoint.url, _format )
        headers = self.client.base_headers.update({"ACCESS-SIGN": signature})
        return await self.client.request(
            url=self.base_endpoint.url + endpoint.url,
            method=endpoint.method,
            params=_format["params"],
            headers=headers,
            data=_format["body"],
            signed=True,
        )
    
    async def batch_cancel_orders(
        self,
        orders: List[Order]
    ) -> Dict:
        endpoint = self.endpoints.batchCancelOrders
        _format = self.formats.batch_cancel_orders(orders)
        signature = self.client.sign(endpoint.method, self.base_endpoint.url, endpoint.url, _format )
        headers = self.client.base_headers.update({"ACCESS-SIGN": signature})
        return await self.client.request(
            url=self.base_endpoint.url + endpoint.url,
            method=endpoint.method,
            params=_format["params"],
            headers=headers,
            data=_format["body"],
            signed=True,
        )
    
    async def cancel_all_orders(self, symbol: str) -> Dict:
        endpoint = self.endpoints.cancelAllOrders
        _format = self.formats.cancel_all_orders(symbol)
        signature = self.client.sign(endpoint.method, self.base_endpoint.url, endpoint.url, _format )
        headers = self.client.base_headers.update({"ACCESS-SIGN": signature})
        return await self.client.request(
            url=self.base_endpoint.url + endpoint.url,
            method=endpoint.method,
            params=_format["params"],
            headers=headers,
            data=_format["body"],
            signed=True,
        )

    async def get_orderbook(self, symbol: str) -> Dict:
        endpoint = self.endpoints.getOrderbook
        _format = self.formats.get_orderbook(symbol)
        return await self.client.request(
            url=self.base_endpoint.url + endpoint.url,
            method=endpoint.method,
            params=_format["params"],

            signed=True,
        )

    async def get_trades(self, symbol: str) -> Dict:
        endpoint = self.endpoints.getTrades
        _format = self.formats.get_trades(symbol)
        return await self.client.request(
            url=self.base_endpoint.url + endpoint.url,
            method=endpoint.method,
            params=_format["params"],

            signed=True,
        )

    async def get_ohlcv(self, symbol: str, interval: str = "1m") -> Dict:
        endpoint = self.endpoints.getOhlcv
        _format = self.formats.get_ohlcv(symbol, interval)
        return await self.client.request(
            url=self.base_endpoint.url + endpoint.url,
            method=endpoint.method,
            params=_format["params"],
            signed=True,
        )

    async def get_ticker(self, symbol: str) -> Dict:
        endpoint = self.endpoints.getTicker
        _format = self.formats.get_ticker(symbol)
        return await self.client.request(
            url=self.base_endpoint.url + endpoint.url,
            method=endpoint.method,
            params=_format["params"],
            signed=True,
        )

    async def get_open_orders(self, symbol: str) -> Dict:
        endpoint = self.endpoints.getOpenOrders
        _format = self.formats.get_open_orders(symbol)
        signature = self.client.sign(endpoint.method, self.base_endpoint.url, endpoint.url, _format )
        headers = self.client.base_headers.update({"ACCESS-SIGN": signature})
        return await self.client.request(
            url=self.base_endpoint.url + endpoint.url,
            method=endpoint.method,
            params=_format["params"],
            headers=headers,
            signed=True,
        )

    async def get_position(self, symbol: str) -> Dict:
        endpoint = self.endpoints.getPosition
        _format = self.formats.get_position(symbol)
        signature = self.client.sign(endpoint.method, self.base_endpoint.url, endpoint.url, _format )
        headers = self.client.base_headers.update({"ACCESS-SIGN": signature})
        return await self.client.request(
            url=self.base_endpoint.url + endpoint.url,
            method=endpoint.method,
            params=_format["params"],
            headers=headers,
            signed=True,
        )

    async def get_account_info(self) -> Dict:
        endpoint = self.endpoints.accountInfo
        _format = self.formats.get_account_info()
        signature = self.client.sign(endpoint.method, self.base_endpoint.url, endpoint.url, _format )
        headers = self.client.base_headers.update({"ACCESS-SIGN": signature})
        return await self.client.request(
            url=self.base_endpoint.url + endpoint.url,
            method=endpoint.method,
            params=_format["params"],
            headers=headers,
            signed=True,
        )

    async def get_exchange_info(self) -> Dict:
        endpoint = self.endpoints.exchangeInfo
        _format = self.formats.get_exchange_info()
        return await self.client.request(
            url=self.base_endpoint.url + endpoint.url,
            method=endpoint.method,
            params=_format["params"],
            signed=True,
        )
 
    async def warmup(self) -> None:
        try:
            contracts_info = await self.get_exchange_info()
            for symbol in contracts_info["data"]:
                if self.symbol == symbol["symbol"]:
                    self.data["tick_size"] = 10**-float(symbol["pricePlace"])
                    self.data["lot_size"] = 10**-float(symbol["volumePlace"])
                    break

        except Exception as e:
            self.logging.error(f"Exchange warmup: {e}")

        finally:
            self.logging.info(f"Binance exchange warmup sequence complete.")
