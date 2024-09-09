import numpy as np
from numba import njit
from numba.types import Array
from typing import Union
import math


@njit(error_model="numpy", cache=True)
def round_ceil(
    num: Union[float, Array], step_size: Union[float, int]
) -> Union[float, int]:
    """
    Rounds a number or array of numbers up to the nearest multiple of a given step size.

    Parameters
    ----------
    num : Union[float, Array]
        The number or array of numbers to be rounded.

    step_size : Union[float, int]
        The step size to round up to the nearest multiple of.

    Returns
    -------
    Union[float, int]
        The rounded number or array of numbers.

    Examples
    --------
    >>> round_ceil(5.1, 0.5)
    5.5
    >>> round_ceil(np.array([2.3, 4.6, 6.1]), 2)
    np.array([4, 6, 8])
    """
    return np.round(
        step_size * np.ceil(num / step_size), int(np.ceil(-np.log10(step_size)))
    )


@njit(error_model="numpy", cache=True)
def round_floor(
    num: Union[float, Array], step_size: Union[float, int]
) -> Union[float, int]:
    """
    Rounds a number or array of numbers down to the nearest multiple of a given step size.

    Parameters
    ----------
    num : Union[float, Array]
        The number or array of numbers to be rounded.

    step_size : Union[float, int]
        The step size to round down to the nearest multiple of.

    Returns
    -------
    Union[float, int]
        The rounded number or array of numbers.

    Examples
    --------
    >>> round_floor(5.8, 0.5)
    5.5
    >>> round_floor(np.array([2.7, 4.2, 6.9]), 2)
    np.array([2, 4, 6])
    """
    return np.round(
        step_size * np.floor(num / step_size), int(np.ceil(-np.log10(step_size)))
    )


@njit(error_model="numpy", cache=True)
def round_discrete(
    num: Union[float, Array], step_size: Union[float, int]
) -> Union[float, int]:
    """
    Rounds a number or array of numbers to the nearest multiple of a given step size.

    Parameters
    ----------
    num : Union[float, Array]
        The number or array of numbers to be rounded.

    step_size : Union[float, int]
        The step size to round to the nearest multiple of.

    Returns
    -------
    Union[float, int]
        The rounded number or array of numbers.

    Examples
    --------
    >>> round_discrete(5.3, 0.5)
    5.5
    >>> round_discrete(np.array([2.4, 4.5, 7.7]), 2)
    np.array([2., 4., 8.])
    """
    return np.round(
        step_size * np.round(num / step_size), int(np.ceil(-np.log10(step_size)))
    )


@njit(error_model="numpy", cache=True,fastmath=True) # 214 ns ± 9.93 ns
def hl_round_floor(
        num: float , sig_figs: int = 5,decimals: int = 6
) -> float:
    """
    Rounds a floating point number so it has no more than "decimals" decimals and at most "sig_figs" significant figures
    Then floors the last decimal. Not compatible with arrays

    Parameters
    ----------
    num : float
        The number or array of numbers to be rounded.

    sig_figs : int
        The maximum number of significant figures.
    
    decimals : int
        The maximum number of decimals.

    Returns
    -------
   float
        The rounded number 
    Examples
    --------
    >>> hl_round_floor(1.9014664, 5, 6)
    1.9014
    """

    scale_sig_figs = math.pow(10,(sig_figs - int(math.floor(math.log10(abs(num)))) - 1))
    rounded_sig_figs = math.floor(num * scale_sig_figs) / scale_sig_figs

    return round(rounded_sig_figs, decimals)

@njit(error_model="numpy", cache=True,fastmath=True) # 214 ns ± 9.93 ns
def hl_round_ceil(
        num: float , sig_figs: int = 5,decimals: int = 6
) -> float:
    """
    Rounds a floating point number so it has no more than "decimals" decimals and at most "sig_figs" significant figures
    Then ceils the last decimal. Not compatible with arrays

    Parameters
    ----------
    num : float
        The number or array of numbers to be rounded.

    sig_figs : int
        The maximum number of significant figures.
    
    decimals : int
        The maximum number of decimals.

    Returns
    -------
   float
        The rounded number 
    Examples
    --------
    >>> hl_round_floor(1.9014664, 5, 6)
    1.9015
    """

    scale_sig_figs = math.pow(10,(sig_figs - int(math.floor(math.log10(abs(num)))) - 1))
    rounded_sig_figs = math.ceil(num * scale_sig_figs) / scale_sig_figs

    return round(rounded_sig_figs, decimals)