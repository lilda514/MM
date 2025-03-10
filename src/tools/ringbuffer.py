import numpy as np
from numba.types import int32, float64, boolean
from numba.experimental import jitclass
from numba import njit
import numba

# spec = [
#         ('_arr', float64[:, :]),
#         ('_left_index', int32),
#         ('_right_index', int32),
#         ('_capacity',int32),
#         ('_columns', int32),
#         ('_allow_overwrite', boolean),
#         ]

# @jitclass(spec)
class RingBufferjit():
    def __init__(self, capacity=0,columns = 1, allow_overwrite=True,):
        """
		Create a new ring buffer with the given capacity and element type

		Parameters
		----------
		capacity: int
			The maximum capacity of the ring buffer
		dtype: data-type, optional
			Desired type of buffer elements. Use a type like (float, 2) to
			produce a buffer with shape (N, 2)
		allow_overwrite: bool
			If false, throw an IndexError when trying to append to an already
			full buffer
        """
        self._columns = columns
        self._arr = np.empty((capacity,columns), dtype = np.float64 )
        self._left_index = 0
        self._right_index = 0
        self._capacity = capacity
        self._allow_overwrite = allow_overwrite
    
    
    def _unwrap(self):
        """ Copy the data from this buffer into unwrapped form """
        return np.concatenate((
			self._arr[self._left_index:min(self._right_index, self._capacity)],
			self._arr[:max(self._right_index - self._capacity, 0)]
		))
    
    def _fix_indices(self):
        """
		Enforce our invariant that 0 <= self._left_index < self._capacity
        """
        if self._left_index >= self._capacity:
            self._left_index -= self._capacity
            self._right_index -= self._capacity
        elif self._left_index < 0:
            self._left_index += self._capacity
            self._right_index += self._capacity

    @property
    def is_full(self):
        """ True if there is no more space in the buffer """
        return self.__len() == self._capacity

    # numpy compatibility
    def __array__(self):
        return self._unwrap()
    
    @property
    def dtype(self):
        return self._arr.dtype

    @property
    def shape(self):
        return (self.__len(),) + self._arr.shape[1:]


    # these mirror methods from deque
    @property
    def maxlen(self):
        return self._capacity

    def append(self, value):
        if self.is_full:
            if not self._allow_overwrite:
                raise IndexError('append to a full RingBuffer with overwrite disabled')
            elif not self.__len():
                return
            else:
                self._left_index += 1
        
        value = np.asarray(value, dtype=np.float64)
        self._arr[self._right_index % self._capacity] = value
        self._right_index += 1
        self._fix_indices()

    def appendleft(self, value):
        if self.is_full:
            if not self._allow_overwrite:
                raise IndexError('append to a full RingBuffer with overwrite disabled')
            elif not self.__len():
                return
            else:
                self._right_index -= 1

        self._left_index -= 1
        self._fix_indices()
        self._arr[self._left_index] = value
    
    def pop(self):
        if self.__len() == 0:
            raise IndexError("pop from an empty RingBuffer")
        self._right_index -= 1
        self._fix_indices()
        res = self._arr[self._right_index % self._capacity]
        return res
    
    def popleft(self):
        if self.__len() == 0:
            raise IndexError("pop from an empty RingBuffer")
        res = self._arr[self._left_index]
        self._left_index += 1
        self._fix_indices()
        return res
    
    def extend(self, values):
        lv = self.__len(values)
        if self.__len() + lv > self._capacity:
            if not self._allow_overwrite:
                raise IndexError('extend a RingBuffer such that it would overflow, with overwrite disabled')
            elif not self.__len():
                return
        if lv >= self._capacity:
            # wipe the entire array! - this may not be threadsafe
            self._arr[...] = values[-self._capacity:]
            self._right_index = self._capacity
            self._left_index = 0
            return

        ri = self._right_index % self._capacity
        sl1 = np.s_[ri:min(ri + lv, self._capacity)]
        sl2 = np.s_[:max(ri + lv - self._capacity, 0)]
        self._arr[sl1] = values[:sl1.stop - sl1.start]
        self._arr[sl2] = values[sl1.stop - sl1.start:]
        self._right_index += lv

        self._left_index = max(self._left_index, self._right_index - self._capacity)
        self._fix_indices()
    
    def extendleft(self, values):
        lv = self.__len(values)
        if self.__len() + lv > self._capacity:
            if not self._allow_overwrite:
                raise IndexError('extend a RingBuffer such that it would overflow, with overwrite disabled')
            elif not self.__len():
                return
        if lv >= self._capacity:
            # wipe the entire array! - this may not be threadsafe
            self._arr[...] = values[:self._capacity]
            self._right_index = self._capacity
            self._left_index = 0
            return

        self._left_index -= lv
        self._fix_indices()
        li = self._left_index
        sl1 = np.s_[li:min(li + lv, self._capacity)]
        sl2 = np.s_[:max(li + lv - self._capacity, 0)]
        self._arr[sl1] = values[:sl1.stop - sl1.start]
        self._arr[sl2] = values[sl1.stop - sl1.start:]

        self._right_index = min(self._right_index, self._left_index + self._capacity)

    # implement Sequence methods
    def __len(self):
        return self._right_index - self._left_index


    def __getitem__(self, item):
        # handle simple (b[1]) and basic (b[np.array([1, 2, 3])]) fancy indexing specially
        if not isinstance(item, numba.types.UniTuple):
            item_arr = np.asarray(item)
            if item_arr.dtype.type is np.int32 or item_arr.dtype.type is np.int64 :
                item_arr = (item_arr + self._left_index) % self._capacity
                return self._arr[item_arr]

        # for everything else, get it right at the expense of efficiency
        return self._unwrap()[item]

    def __iter__(self):
        # alarmingly, this is comparable in speed to using itertools.chain
        return iter(self._unwrap())

    # Everything else
    def __repr__(self):
        return '<RingBuffer of {!r}>'.format(np.asarray(self))
