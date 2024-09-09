from __future__ import annotations
from typing import Union


class HlOrderIdGenerator():

    def __init__(self) -> None:
        return
        
    def setLevels(self,no_levels):
        self.no_levels = no_levels
        self.levelDict = {int(i*10**7): 0 for i in range(1, no_levels + 1)} | {int(-i*10**7): 0 for i in range(1, no_levels + 1)} | {0:0}

    
    def generate_order_id(self, level: int = 0):   
        level_num = int(level*10**7)
        prev_order_num = self.levelDict[level_num]
        self.levelDict[level_num] += (1 if level_num >= 0 else -1)
        return Cloid.from_int(level_num + ((prev_order_num+1) if level_num >= 0 else prev_order_num-1))
    
    def match_level(self,clientOrderId: Union[Cloid,str]):
        if isinstance(clientOrderId, Cloid):
            decoded_id = clientOrderId.to_int()
        else:
           decoded_id = Cloid.from_str(clientOrderId).to_int()
        return decoded_id//10**7
    
class Cloid:
    def __init__(self, raw_cloid: str):
        self._raw_cloid: str = raw_cloid
        # self._validate()

    # def _validate(self):
    #     assert self._raw_cloid[:2] == "0x", "cloid is not a hex string"
    #     assert len(self._raw_cloid[2:]) == 32, "cloid is not 16 bytes"

    @staticmethod
    def from_int(cloid: int) -> Cloid:
        # Convert to 128-bit two's complement representation
        if cloid < 0:
            cloid += (1 << 128)  # Compute two's complement for negative numbers
        hex_str = f"{cloid:#034x}"        
        return Cloid(hex_str)

    @staticmethod
    def from_str(cloid: str) -> Cloid:
        return Cloid(cloid)

    def to_raw(self):
        return self._raw_cloid
    
    def to_int(self):
        # Convert from hexadecimal string to integer
        num = int(self._raw_cloid, 16)
        if num >= (1 << 127):
            num -= (1 << 128)  # Convert from two's complement if the number is negative
        return num
    
    def __str__(self):
        return f"{self._raw_cloid} ({self.to_int()})"

    
