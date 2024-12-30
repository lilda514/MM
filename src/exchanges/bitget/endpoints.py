from src.exchanges.common.endpoints import Endpoints


class BitgetEndpoints(Endpoints):
    def __init__(self) -> None:
        super().__init__()

        self.load_base(
            main="https://api.bitget.com",
            public_ws="wss://ws.bitget.com/v2/ws/public",
            private_ws="wss://ws.bitget.com/v2/ws/private",
        )

        self.load_required(
            createOrder={"method": "POST", "url": "/api/v2/mix/order/place-order"},
            amendOrder={"method": "POST", "url": "/api/v2/mix/order/modify-order"},
            cancelOrder={"method": "POST", "url": "/api/v2/mix/order/cancel-order"},
            cancelAllOrders={"method": "POST", "url": "/api/v2/mix/order/cancel-all-orders"},
            getOrderbook={"method": "GET", "url": "/api/v2/mix/market/merge-depth"},
            getTrades={"method": "GET", "url": "/api/v2/mix/market/fills"},
            getOhlcv={"method": "GET", "url": "/api/v2/mix/market/candles"},
            getTicker={"method": "GET", "url": "/api/v2/mix/market/tickers"},
            getOpenOrders={"method": "GET", "url": "/api/v2/mix/order/orders-pending"},
            getPosition={"method": "GET", "url": "/api/v2/mix/position/single-position"},
            wsLogin={"method":"GET", "url": "/user/verify"}
        )

        self.load_additional(
            batchCreateOrders={"method": "POST", "url": "/api/v2/mix/order/batch-place-order"},
            # batchAmendOrders={"method": "PUT", "url": "/fapi/v1/batchOrders"},
            batchCancelOrders={"method": "POST", "url": "/api/v2/mix/order/batch-cancel-orders"},
            exchangeInfo={"method": "GET", "url": "/api/v2/mix/market/contracts"},
            accountInfo={"method": "GET", "url": "/api/v2/mix/account/accounts"},
            setLeverage={"method": "POST", "url": "/api/v2/mix/account/set-leverage"},
            setMarginMode={"method": "POST", "url": "/api/v2/mix/account/set-margin-mode"}
        )
