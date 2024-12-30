# import string
# import numpy as np
# from typing import Union

from src.exchanges.common.orderid import OrderIdGenerator

class BitgetOrderIdGenerator(OrderIdGenerator):
    def __init__(self) -> None:
        pass
    # def generate_random_str(self, length: int) -> str:
    #     return ''.join(np.random.choice(self.legal_chars, length).tolist())
    
    # def decode(self, orderId: Union[str,int]) -> None:
    #     pass 
    def setLevels(self,no_levels):
        self.no_levels = no_levels
        self.levelDict = {int(i*10**7): 0 for i in range(1, no_levels + 1)} | {int(-i*10**7): 0 for i in range(1, no_levels + 1)} | {0:0}

    
    def generate_order_id(self, level: int = 0):   
        level_num = int(level*10**7)
        prev_order_num = self.levelDict[level_num]
        self.levelDict[level_num] += (1 if level_num >= 0 else -1)
        return level_num + ((prev_order_num+1) if level_num >= 0 else prev_order_num-1)
    
    def match_level(self,clientOrderId: str):
        return int(clientOrderId)//10**7