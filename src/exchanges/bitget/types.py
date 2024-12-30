from src.exchanges.common.types import PositionDirectionConverter, SideConverter, TimeInForceConverter, OrderTypeConverter, ReduceOnlyConverter


class BitgetSideConverter(SideConverter):
    def __init__(self) -> None:
        super().__init__(
            BUY="buy", 
            SELL="sell"
        )

class BitgetOrderTypeConverter(OrderTypeConverter):
    def __init__(self) -> None:
        super().__init__(
            LIMIT="limit", 
            MARKET="market", 
        )

class BitgetTimeInForceConverter(TimeInForceConverter):
    def __init__(self) -> None:
        super().__init__(
            GTC="gtc", 
            FOK="fok", 
            POST_ONLY="post_only",
            IOC="ioc",
        )

class BitgetPositionDirectionConverter(PositionDirectionConverter):
    def __init__(self) -> None:
        super().__init__(
            LONG="long", 
            SHORT="short"
        )

class BitgetReduceOnlyConverter(ReduceOnlyConverter):
    def __init__(self) -> None:
        super().__init__(
            TRUE="YES", 
            FALSE="NO"
        )