import numpy as np


class Tensor:
    def __init__(self, data, _children=(), _op=""):
        self.data = np.array(data, dtype=float)
        self.grad = np.zeros_like(self.data)
        self._backward = lambda: None
        self._prev = tuple(_children)
        self._op = _op

    def __add__(self, other):
        raise NotImplementedError

    def __mul__(self, other):
        raise NotImplementedError

    def __matmul__(self, other):
        raise NotImplementedError

    def relu(self):
        raise NotImplementedError

    def sum(self):
        raise NotImplementedError

    def mean(self):
        raise NotImplementedError

    def backward(self):
        raise NotImplementedError

    # Derived operators: you can define these in terms of the ones above.
    def __neg__(self):
        return self * -1

    def __radd__(self, other):
        return self + other

    def __sub__(self, other):
        return self + (-other)

    def __rsub__(self, other):
        return other + (-self)

    def __rmul__(self, other):
        return self * other

    def __repr__(self):
        return "Tensor(shape=%s)" % (self.data.shape,)
