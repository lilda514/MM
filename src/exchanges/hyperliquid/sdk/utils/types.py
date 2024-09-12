from __future__ import annotations

import sys

if sys.version_info >= (3, 8):
    from typing import Literal, TypedDict
    from typing_extensions import NotRequired
else:
    from typing_extensions import TypedDict, Literal, NotRequired

from typing import Any, Callable, Dict, List, NamedTuple, Optional, Tuple, Union, cast

Any = Any
Option = Optional
cast = cast
Callable = Callable
NamedTuple = NamedTuple
NotRequired = NotRequired

AssetInfo = TypedDict("AssetInfo", {"name": str, "szDecimals": int})
Meta = TypedDict("Meta", {"universe": List[AssetInfo]})
Side = Union[Literal["A"], Literal["B"]]
SIDES: List[Side] = ["A", "B"]

SpotAssetInfo = TypedDict("SpotAssetInfo", {"name": str, "tokens": List[int]})
SpotTokenInfo = TypedDict("SpotTokenInfo", {"name": str, "szDecimals": int, "weiDecimals": int})
SpotMeta = TypedDict("SpotMeta", {"universe": List[SpotAssetInfo], "tokens": List[SpotTokenInfo]})

SpotAssetCtx = TypedDict("SpotAssetCtx", {"dayNtlVlm": str, "markPx": str, "midPx": Optional[str], "prevDayPx": str, "circulatingSupply": str, "coin": str})
SpotMetaAndAssetCtxs = Tuple[SpotMeta, List[SpotAssetCtx]]

AllMidsSubscription = TypedDict("AllMidsSubscription", {"type": Literal["allMids"]})
L2BookSubscription = TypedDict("L2BookSubscription", {"type": Literal["l2Book"], "coin": str})
TradesSubscription = TypedDict("TradesSubscription", {"type": Literal["trades"], "coin": str})
UserEventsSubscription = TypedDict("UserEventsSubscription", {"type": Literal["userEvents"], "user": str})
NotificationSubscription = TypedDict("NotificationSubscription", { "type": Literal["notification"], "user": str })
WebData2Subscription = TypedDict("webData2Subscription",{ "type": Literal["webData2"], "user": str })
CandleSubscription = TypedDict("candleSubscription",{ "type": Literal["candle"], "coin": str, "interval": str })
OrderUpdatesSubscription = TypedDict("orderUpdatesSubscription",{ "type": Literal["orderUpdates"], "user": str })
UserFillsSubscription = TypedDict("userFillsSubscription",{ "type": Literal["userFills"], "user": str })
UserFundingsSubscription = TypedDict("userFundingsSubscription", { "type": Literal["userFundings"], "user": str })
UserNonFundingLedgerUpdatesSubscription = TypedDict("userNonFundingLedgerUpdatesSubscription",{ "type": Literal["userNonFundingLedgerUpdates"], "user": str })

Subscription = Union[AllMidsSubscription, L2BookSubscription, TradesSubscription, UserEventsSubscription,
                     NotificationSubscription,WebData2Subscription,CandleSubscription,OrderUpdatesSubscription,
                     UserFillsSubscription,UserFundingsSubscription,UserNonFundingLedgerUpdatesSubscription]


AllMidsData = TypedDict("AllMidsData", {"mids": Dict[str, str]})
AllMidsMsg = TypedDict("AllMidsMsg", {"channel": Literal["allMids"], "data": AllMidsData})
L2Level = TypedDict("L2Level", {"px": str, "sz": str, "n": int})
L2BookData = TypedDict("L2BookData", {"coin": str, "levels": Tuple[List[L2Level]], "time": int})
L2BookMsg = TypedDict("L2BookMsg", {"channel": Literal["l2Book"], "data": L2BookData})
PongMsg = TypedDict("PongMsg", {"channel": Literal["pong"]})
Trade = TypedDict("Trade", {"coin": str, "side": Side, "px": str, "sz": int, "hash": str, "time": int})
TradesMsg = TypedDict("TradesMsg", {"channel": Literal["trades"], "data": List[Trade]})
Fill = TypedDict(
    "Fill",
    {
        "coin": str,
        "px": str,
        "sz": str,
        "side": Side,
        "time": int,
        "startPosition": str,
        "dir": str,
        "closedPnl": str,
        "hash": str,
        "oid": int,
        "crossed": bool,
        "fee": str, # negative means rebate
        "tid": int, # unique trade id
        "feeToken":str
    },
)
# TODO: handle other types of user events
FillsData = TypedDict("FillsData", {"fills": List[Fill]}, total=False)
Liquidation = TypedDict("Liquidation",{ "lid": int,
                                        "liquidator": str,
                                        "liquidated_user": str,
                                        "liquidated_ntl_pos": str,
                                        "liquidated_account_value": str})
LiquidationData = TypedDict("LiquidationData",{"liquidation":Liquidation })
UserFunding = TypedDict("UserFunding",{ "time": int,
                                        "coin": str,
                                        "usdc": str,
                                        "szi": str,
                                        "fundingRate": str })
FundingData= TypedDict("FundingData",{"funding":UserFunding})
NonUserCancel= TypedDict("NonUserCancel",{  "coin": str, "oid": int})
NonUserCancelData= TypedDict("NonUserCancelData",{"nonUserCancel":List[NonUserCancel]})
UserEventsMsg = TypedDict("UserEventsMsg", {"channel": Literal["user"], "data": Union[FillsData,LiquidationData,FundingData,NonUserCancelData]})

UserFundingMsg = TypedDict("UserFundingMsg",{"channel":Literal["userFundings"],"data": UserFunding})

Candle = TypedDict("Candle",{ "t": int, #open millis
                              "T": int, # close millis
                              "s": str, # coin
                              "i": str, # interval
                              "o": int, # open price
                              "c": int, # close price
                              "h": int, # high price
                              "l": int, # low price
                              "v": int, # volume (base unit)
                              "n": int })# number of trades                       
CandleMsg= TypedDict("CandleMsg",{ "channel":Literal["candle"],"data": Candle })

BasicOrder = TypedDict("BasicOrder",{"coin": str,
                                     "side": str,
                                     "limitPx": str,
                                     "sz": str,
                                     "oid": int,
                                     "timestamp": int,
                                     "origSz": str,
                                     "cloid": Union[str,None]
                                     })

Order = TypedDict("Order",{"order": BasicOrder,
                           "status":str,
                           "statusTimestamp":int
                                     })
OrderUpdatesMsg = TypedDict("OrderUpdatesMsg",{"channel":Literal["orderUpdates"],"data":List[Order]},)

UserFill = TypedDict("UserFill",{
                                 "coin": str,
                                 "px": str, # price
                                 "sz": str, # size
                                 "side": Side,
                                 "time": int,
                                 "startPosition": str,
                                 "dir": str, # used for frontend display
                                 "closedPnl": str,
                                 "hash": str, # L1 transaction hash
                                 "oid": int, # order id
                                 "crossed": bool, # whether order crossed the spread (was taker)
                                 "fee": str, # negative means rebate
                                 "tid": int, # unique trade id
                                 "feeToken":str
                                 })
UserFillsMsg = TypedDict("UserFillsMsg",{"channel":Literal["userFills"],"data":List[UserFill]})


#TODO : ADD type support for webData2,userNonFundingLedgerUpdates, notification
WsMsg = Union[AllMidsMsg, L2BookMsg, TradesMsg, UserEventsMsg, PongMsg,UserFundingMsg,CandleMsg,OrderUpdatesMsg,UserFillsMsg]


class Cloid:
    def __init__(self, raw_cloid: str):
        self._raw_cloid: str = raw_cloid
        # self._validate()

    # def _validate(self):
    #     assert self._raw_cloid[:2] == "0x", "cloid is not a hex string"
    #     assert len(self._raw_cloid[2:]) == 32, "cloid is not 16 bytes"

    @staticmethod
    def from_int(cloid: int) -> Cloid:
        return Cloid(f"{cloid:#034x}")

    @staticmethod
    def from_str(cloid: str) -> Cloid:
        return Cloid(cloid)

    def to_raw(self):
        return self._raw_cloid
