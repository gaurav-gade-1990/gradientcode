import math


class Value:
    def __init__(self, data, _children=(), _op=""):
        self.data = float(data)
        self.grad = 0.0
        self._backward = lambda: None
        self._prev = tuple(_children)
        self._op = _op

    def __add__(self, other):
        raise NotImplementedError

    def __mul__(self, other):
        raise NotImplementedError

    def __pow__(self, k):
        raise NotImplementedError

    def tanh(self):
        raise NotImplementedError

    def relu(self):
        raise NotImplementedError

    def exp(self):
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

    def __truediv__(self, other):
        return self * other ** -1

    def __rtruediv__(self, other):
        return other * self ** -1

    def __repr__(self):
        return "Value(data=%g, grad=%g)" % (self.data, self.grad)
