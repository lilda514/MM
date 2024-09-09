import string
import numpy as np
from typing import Union

from src.exchanges.common.orderid import OrderIdGenerator

class BinanceOrderIdGenerator(OrderIdGenerator):
    legal_chars = np.array([i for i in string.ascii_letters + string.digits + "-_.:"])

    def __init__(self) -> None:
        super().__init__(36)

    def generate_random_str(self, length: int) -> str:
        return ''.join(np.random.choice(self.legal_chars, length).tolist())
    
    def decode(self, orderId: Union[str,int]) -> None:
        pass