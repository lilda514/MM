from src.exchanges.common.types import PositionDirectionConverter, SideConverter, TimeInForceConverter, OrderTypeConverter


class BinanceSideConverter(SideConverter):
    def __init__(self) -> None:
        super().__init__(
            BUY="BUY", 
            SELL="SELL"
        )

class BinanceOrderTypeConverter(OrderTypeConverter):
    def __init__(self) -> None:
        super().__init__(
            LIMIT="LIMIT", 
            MARKET="MARKET", 
            STOP_LIMIT="STOP", 
            TAKE_PROFIT_LIMIT="TAKE_PROFIT"
        )

class BinanceTimeInForceConverter(TimeInForceConverter):
    def __init__(self) -> None:
        super().__init__(
            GTC="GTC", 
            FOK="FOK", 
            POST_ONLY="GTX",
            IOC = "IOC"
        )

class BinancePositionDirectionConverter(PositionDirectionConverter):
    def __init__(self) -> None:
        super().__init__(
            LONG="LONG", 
            SHORT="SHORT"
        )