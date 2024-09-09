from hyperliquid.utils.types import *

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


Notification = TypedDict("Notification",{Literal["notification"]:str})
NotificationMsg = TypedDict("NotificationMsg",{"channel":Literal["notification"],"data":Notification })


#WebData2Msg = TypedDict("WebData2Msg",) Skip for now

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



UserFunding = TypedDict("UserFunding",{ "time": int,
                                        "coin": str,
                                        "usdc": str,
                                        "szi": str,
                                        "fundingRate": str })
UserFundingMsg = TypedDict("UserFundingMsg",{"channel":Literal["userFundings"],"data": UserFunding})
 
#UserEvents
Liquidation = TypedDict("Liquidation",{ "lid": int,
                                        "liquidator": str,
                                        "liquidated_user": str,
                                        "liquidated_ntl_pos": str,
                                        "liquidated_account_value": str})

LiquidationData = TypedDict("LiquidationData",{"liquidation":Liquidation })
FundingData= TypedDict("FundingData",{"funding":UserFunding})
NonUserCancel= TypedDict("NonUserCancel",{  "coin": str, "oid": int})
NonUserCancelData= TypedDict("NonUserCancelData",{"nonUserCancel":List[NonUserCancel]})
