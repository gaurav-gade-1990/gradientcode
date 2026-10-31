import numpy as np


def _unbroadcast(grad, shape):
    """Sum grad over the axes that broadcasting stretched, so it has shape `shape`."""
    extra = grad.ndim - len(shape)
    if extra > 0:
        grad = grad.sum(axis=tuple(range(extra)))
    axes = tuple(i for i, s in enumerate(shape) if s == 1 and grad.shape[i] != 1)
    if axes:
        grad = grad.sum(axis=axes, keepdims=True)
    return grad.reshape(shape)


class Tensor:
    def __init__(self, data, _children=(), _op=""):
        self.data = np.array(data, dtype=float)
        self.grad = np.zeros_like(self.data)
        self._backward = lambda: None
        self._prev = tuple(_children)
        self._op = _op

    def __add__(self, other):
        other = other if isinstance(other, Tensor) else Tensor(other)
        out = Tensor(self.data + other.data, (self, other), "+")

        def _backward():
            self.grad = _unbroadcast(out.grad, self.data.shape)
            other.grad = _unbroadcast(out.grad, other.data.shape)
        out._backward = _backward
        return out

    def __mul__(self, other):
        other = other if isinstance(other, Tensor) else Tensor(other)
        out = Tensor(self.data * other.data, (self, other), "*")

        def _backward():
            self.grad = _unbroadcast(other.data * out.grad, self.data.shape)
            other.grad = _unbroadcast(self.data * out.grad, other.data.shape)
        out._backward = _backward
        return out

    def __matmul__(self, other):
        out = Tensor(self.data @ other.data, (self, other), "@")

        def _backward():
            # Overwrites instead of accumulating: a Tensor used twice keeps only one path.
            self.grad = out.grad @ other.data.T
            other.grad = self.data.T @ out.grad
        out._backward = _backward
        return out

    def relu(self):
        out = Tensor(np.maximum(self.data, 0.0), (self,), "relu")

        def _backward():
            self.grad += (self.data > 0) * out.grad
        out._backward = _backward
        return out

    def sum(self):
        out = Tensor(self.data.sum(), (self,), "sum")

        def _backward():
            self.grad += np.ones_like(self.data) * out.grad
        out._backward = _backward
        return out

    def mean(self):
        out = Tensor(self.data.mean(), (self,), "mean")

        def _backward():
            self.grad += np.ones_like(self.data) * out.grad / self.data.size
        out._backward = _backward
        return out

    def backward(self):
        order, seen = [], set()

        def build(t):
            if t not in seen:
                seen.add(t)
                for c in t._prev:
                    build(c)
                order.append(t)
        build(self)
        self.grad = np.ones_like(self.data)
        for t in reversed(order):
            t._backward()

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
