# -*- coding: utf-8 -*-
from src.exchanges.common.types import (
    SideConverter,
    OrderTypeConverter,
    TimeInForceConverter,
    PositionDirectionConverter 
    )

class HlSideConverter(SideConverter):
    def __init__(self) -> None:
        super().__init__(BUY = "B", SELL = "A")

class HlOrderTypeConverter(OrderTypeConverter):
    def __init__(self) -> None:
        super().__init__(
                         LIMIT="Limit", 
                         MARKET="Market",
                         STOP_LIMIT="Stop Limit",
                         TAKE_PROFIT_LIMIT="Take Profit Limit",
                         STOP_MARKET="Stop Market",
                         TAKE_PROFIT_MARKET= "Take Profit Market" 
                         )

class HlTimeInForceConverter(TimeInForceConverter):
    def __init__(self):
        super().__init__(GTC= "Gtc", FOK= "", POST_ONLY = "Alo", IOC = "Ioc")

#Cannot be used?
class HlPositionDirectionConverter(PositionDirectionConverter):
    def __init__(self):
        super().__init__(LONG= "Long" , SHORT = "Short")
        
