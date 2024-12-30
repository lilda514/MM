# -*- coding: utf-8 -*-
from src.tools.misc import time_ms

from typing import Dict, Optional

class Side:
    BUY = 1
    SELL = -1


class OrderType:
    LIMIT = 0
    MARKET = 1
    STOP_LIMIT = 2
    TAKE_PROFIT_LIMIT = 3
    STOP_MARKET = 4
    TAKE_PROFIT_MARKET = 5


class TimeInForce:
    GTC = 0
    FOK = 1
    POST_ONLY = 2
    IOC = 3


class PositionDirection:
    LONG = 1
    SHORT = -1

class OrderStatus:
    IN_FLIGHT = 0
    TO_BE_TRIGGERED = 1
    IN_THE_BOOK = 2
    TO_CANCEL = 3
    RECENTLY_CANCELLED = 4

class ReduceOnly:
    TRUE = True
    FALSE = False    

class Order:
    def __init__(
        self,
        symbol: str,
        side: Side,
        size: float,
        orderType: OrderType = None,
        timeInForce: TimeInForce = None,
        timestamp: float = 0.0, 
        currentStatus: Optional[OrderStatus] = OrderStatus.IN_FLIGHT,
        price: Optional[float] = None,
        orderId: Optional[str] = None,
        clientOrderId: Optional[str] = None,
        triggerPrice: Optional[float] = None,
        reduceOnly: Optional[bool] = False
    ) -> None:
        self._symbol = symbol
        self._side = side
        self._orderType = orderType
        self._timeInForce = timeInForce
        self._size = size
        self._current_status = currentStatus
        self._price = price
        self._orderId = orderId
        self._clientOrderId = clientOrderId
        self._trigger_price = triggerPrice
        self._reduce_only = reduceOnly
        self._timestamp = timestamp

    @property
    def symbol(self):
        return self._symbol

    @property
    def side(self):
        return self._side

    @property
    def orderType(self):
        return self._orderType

    @property
    def timeInForce(self):
        return self._timeInForce

    @property
    def price(self):
        return self._price

    @property
    def size(self):
        return self._size
    
    @property
    def currentStatus(self):
        return self._current_status

    @property
    def orderId(self):
        return self._orderId

    @property
    def clientOrderId(self):
        return self._clientOrderId
    
    @property
    def triggerPrice(self):
        return self._trigger_price
    
    @property
    def reduceOnly(self):
        return self._reduce_only
    
    @property
    def timestamp(self):
        return self._timestamp
    
    def __repr__(self) -> str:
        return (
            f"Order(symbol={self.symbol}, side={self.side}, orderType={self.orderType}, "
            f"timeInForce={self.timeInForce}, price={self.price}, size={self.size}, "
            f"orderId={self.orderId}, clientOrderId={self.clientOrderId})"
        )

    def __str__(self):
        return (
            f"Order: symbol={self.symbol}, side={self.side}, orderType={self.orderType}, "
            f"timeInForce={self.timeInForce}, price={self.price}, size={self.size}, "
            f"orderId={self.orderId}, clientOrderId={self.clientOrderId}"
        )

    def __eq__(self, other):
        if isinstance(other, Order):
            return (
                self.symbol == other.symbol
                and self.side == other.side
                and self.orderType == other.orderType
                and self.timeInForce == other.timeInForce
                and self.price == other.price
                and self.size == other.size
                # and self.orderId == other.orderId
                # and self.clientOrderId == other.clientOrderId
            )
        return False

    def __bool__(self):
        return any(
            [
                self._symbol,
                self._side,
                self._orderType,
                self._timeInForce,
                self._price,
                self._size,
                self._orderId,
                self._clientOrderId,
                self._current_status,
                self._timestamp
            ]
        )

    def __hash__(self):
        return hash(
            (
                self._symbol,
                self._side,
                self._orderType,
                self._timeInForce,
                self._price,
                self._size,
                self._orderId,
                self._clientOrderId,
                self._current_status,
                self._timestamp
            )
        )

    def to_dict(self):
        return {
            "symbol": self._symbol,
            "side": self._side,
            "orderType": self._orderType,
            "timeInForce": self._timeInForce,
            "size": self._size,
            "price": self._price,
            "orderId": self._orderId,
            "clientOrderId": self._clientOrderId,
        }

    @classmethod
    def from_dict(cls, data: Dict):
        return cls(
            symbol=data.get("symbol"),
            side=data.get("side"),
            orderType=data.get("orderType"),
            timeInForce=data.get("timeInForce"),
            size=data.get("size"),
            price=data.get("price"),
            orderId=data.get("orderId"),
            clientOrderId=data.get("clientOrderId"),
        )
        
    def changeStatus(self, new_status: OrderStatus):
        self._current_status = new_status
        return self._current_status

class Position:
    def __init__(
        self,
        symbol: str = None,
        side: Side = None,
        entryPrice: float = None,
        size: float = 0.0,
        uPnl: float = 0.0,
        openTime: float = None
    ) -> None:
        self._symbol = symbol
        self._side = side
        self._entryPrice = entryPrice
        self._size = size
        self._uPnl = uPnl
        self._updateCounter = 0
        self._openTime = openTime 

    @property
    def symbol(self):
        return self._symbol

    @property
    def side(self):
        return self._side

    @property
    def entryPrice(self):
        return self._entryPrice

    @property
    def size(self):
        return self._size

    @property
    def uPnl(self):
        return self._uPnl
    
    @property
    def updateCounter(self):
        return self._updateCounter
    
    @property
    def openTime(self):
        return self._openTime

    def __repr__(self) -> str:
        return (
            f"Position(symbol={self._symbol}, side={self._side}, price={self._entryPrice}, "
            f"size={self._size}, uPnl={self._uPnl}, open time={self._openTime})"
        )

    def __str__(self) -> str:
        return (
            f"Position(symbol={self._symbol}, side={self._side}, price={self._entryPrice}, "
            f"size={self._size}, uPnl={self._uPnl}, open time={self._openTime})"
        )

    def __bool__(self) -> bool:
        return any(
            attr is not None
            for attr in [self._symbol, self._side, self._entryPrice, self._size, self._uPnl]
        )

    def to_dict(self) -> dict:
        """
        Converts the Position object to a dictionary.
        """
        return {
            "symbol": self._symbol,
            "side": self._side,
            "entryPrice": self._entryPrice,
            "size": self._size,
            "uPnl": self._uPnl,
        }

    def update(
        self,
        symbol: str = None,
        side: Side = None,
        entryPrice: float = None,
        size: float = None,
        uPnl: float = None,
        timestamp: int = None
    ) -> None:
        """
        Updates the attributes of the Position object with the provided values.

        Parameters
        ----------
        symbol : str, optional
            The symbol to update.

        side : Side, optional
            The side to update.

        price : float, optional
            The price to update.

        size : float, optional
            The size to update.

        uPnl : float, optional
            The unrealized PnL to update.

        """
        #Increment the counter by 1 if we increased our position on the same side, but reset to 0 if switched sides.
        self._updateCounter += 1 if side == self._side else -self._updateCounter
        
        #If we open a new position restart the timer
        self._openTime = timestamp if (side != self._side and timestamp is not None) else self._openTime

        if symbol is not None:
            self._symbol = symbol

        if side is not None:
            self._side = side

        if entryPrice is not None:
            self._entryPrice = entryPrice

        if size is not None:
            self._size = size

        if uPnl is not None:
            self._uPnl = uPnl
            

    def reset(self) -> None:
        """
        Resets all attributes of the Position object.
        """
        # self._symbol = None
        self._side = None
        self._price = None
        self._size = 0.0
        self._uPnl = 0.0
        self._updateCounter = 0
        self._openTime = time_ms()
    
class StrNumConverter:
    """
    A base class for converting between numerical values and their string representations.

    This class provides methods to convert a numerical value to its string representation
    and vice versa. If the value or name is not found, it returns default unknown values.
    """

    DEFAULT_UNKNOWN_STR = "UNKNOWN"
    DEFAULT_UNKNOWN_NUM = 0

    def __init__(self, str_to_int: Dict[str, int]) -> None:
        self.str_to_int = str_to_int
        self.int_to_str = {v: k for k, v in self.str_to_int.items()}

    def to_str(self, value: int) -> str:
        """
        Converts a numerical value to its str representation.

        Parameters
        ----------
        value : int
            The numerical value to convert.

        Returns
        -------
        str
            The str representation of the numerical value.
            If the value is not found, returns "UNKNOWN".
        """
        return self.int_to_str.get(value, self.DEFAULT_UNKNOWN_STR)

    def to_num(self, name: str) -> int:
        """
        Converts a str name to its numerical representation.

        Parameters
        ----------
        name : str
            The str name to convert.

        Returns
        -------
        int
            The numerical representation of the str name.
            If the name is not found, returns -1.
        """
        return self.str_to_int.get(name, self.DEFAULT_UNKNOWN_NUM)


class SideConverter(StrNumConverter):
    """
    A converter class for trade sides, converting between string and numerical representations.

    Parameters
    ----------
    BUY : str
        The string representation for the "buy" side.

    SELL : str
        The string representation for the "sell" side.

    Attributes
    ----------
    str_to_num : dict
        A dictionary mapping string representations to numerical values.

    num_to_str : dict
        A dictionary mapping numerical values to string representations.
    """

    def __init__(self, BUY: str, SELL: str) -> None:
        super().__init__(str_to_int={f"{BUY}": Side.BUY, f"{SELL}": Side.SELL})


class OrderTypeConverter(StrNumConverter):
    """
    A converter class for order types, converting between string and numerical representations.

    Parameters
    ----------
    LIMIT : str
        The string representation for the "limit" order type.

    MARKET : str
        The string representation for the "market" order type.

    STOP_LIMIT : str, optional
        The string representation for the "stop limit" order type. Default is None.

    TAKE_PROFIT_LIMIT : str, optional
        The string representation for the "take profit limit" order type. Default is None.

    Attributes
    ----------
    str_to_num : dict
        A dictionary mapping string representations to numerical values.

    num_to_str : dict
        A dictionary mapping numerical values to string representations.
    """

    def __init__(
        self,
        LIMIT: str,
        MARKET: str,
        STOP_LIMIT: str = None,
        TAKE_PROFIT_LIMIT: str = None,
        STOP_MARKET: str = None,
        TAKE_PROFIT_MARKET: str = None,
    ) -> None:
        super().__init__(
            str_to_int={
                f"{LIMIT}": OrderType.LIMIT,
                f"{MARKET}": OrderType.MARKET,
                f"{STOP_LIMIT}": OrderType.STOP_LIMIT,
                f"{TAKE_PROFIT_LIMIT}": OrderType.TAKE_PROFIT_LIMIT,
                f"{STOP_MARKET}":OrderType.STOP_MARKET,
                f"{TAKE_PROFIT_MARKET}":OrderType.TAKE_PROFIT_MARKET,
            }
        )

class TimeInForceConverter(StrNumConverter):
    """
    A converter class for time-in-force policies, converting between string and numerical representations.

    Parameters
    ----------
    GTC : str
        The string representation for "good till canceled".

    FOK : str
        The string representation for "fill or kill".

    POST_ONLY : str
        The string representation for "post only".

    Attributes
    ----------
    str_to_num : dict
        A dictionary mapping string representations to numerical values.

    num_to_str : dict
        A dictionary mapping numerical values to string representations.
    """

    def __init__(self, GTC: str, FOK: str, POST_ONLY: str, IOC: str) -> None:
        super().__init__(
            str_to_int={
                f"{GTC}": TimeInForce.GTC,
                f"{FOK}": TimeInForce.FOK,
                f"{POST_ONLY}": TimeInForce.POST_ONLY,
                f"{IOC}": TimeInForce.IOC
            }
        )


class PositionDirectionConverter(StrNumConverter):
    """
    A converter class for position directions, converting between string and numerical representations.

    Parameters
    ----------
    LONG : str
        The string representation for the "long" position direction.

    SHORT : str
        The string representation for the "short" position direction.

    Attributes
    ----------
    str_to_num : dict
        A dictionary mapping string representations to numerical values.

    num_to_str : dict
        A dictionary mapping numerical values to string representations.
    """

    def __init__(self, LONG: str, SHORT: str) -> None:
        super().__init__(
            str_to_int={
                f"{LONG}": PositionDirection.LONG,
                f"{SHORT}": PositionDirection.SHORT,
            }
        )

class ReduceOnlyConverter(StrNumConverter):
    """
    A converter class for position directions, converting between string and numerical representations.

    Parameters
    ----------
    TRUE : str
        The string representation if an order is to be reduce only.

    FALSE : str
        The string representation if an order is NOT to be reduce only.

    Attributes
    ----------
    str_to_num : dict
        A dictionary mapping string representations to numerical values.

    num_to_str : dict
        A dictionary mapping numerical values to string representations.
    """

    def __init__(self, TRUE: str, FALSE: str) -> None:
        super().__init__(
            str_to_int={
                f"{TRUE}": ReduceOnly.TRUE,
                f"{FALSE}": ReduceOnly.FALSE,
            }
        )