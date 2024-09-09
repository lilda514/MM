# -*- coding: utf-8 -*-
"""
Created on Mon Jun 17 18:19:22 2024

@author: dalil
"""

from src.exchanges.common.numstrconverter import NumStrConverter

class HlSideConverter(NumStrConverter):
    
    # Market buy = side B
    # Market sell = side A
    side_to_float = {'A':1,'B':-1}
    float_to_side = {1:'A', -1:'B'}

    super().__init__(side_to_float,float_to_side)
