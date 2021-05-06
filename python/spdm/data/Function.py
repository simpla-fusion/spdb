import collections
from functools import cached_property
from typing import Any, Callable, Optional, Sequence, Union

import numpy as np
import scipy
import scipy.interpolate

from ..util.logger import logger

logger.debug(f"SciPy: Version {scipy.__version__}")


class Function:

    def __new__(cls, x, y=None, *args, **kwargs):
        if cls is not Function:
            return object.__new__(cls)

        if isinstance(x, collections.abc.Sequence):
            obj = PiecewiseFunction(x, y, *args, **kwargs)
        elif not isinstance(x, np.ndarray):
            raise TypeError(f"x should be np.ndarray not {type(x)}!")
        else:
            obj = object.__new__(cls)

        return obj

    def __init__(self,
                 x: np.ndarray,
                 y: Union[np.ndarray, float, Callable],
                 is_periodic=False):
        self._is_periodic = is_periodic
        self._x = x
        self._y = y
        # elif isinstance(y, np.ndarray) and x.shape == y.shape:
        #     obj = object.__new__(cls)

    @property
    def is_periodic(self):
        return self._is_periodic

    @property
    def x(self):
        return self._x

    def duplicate(self):
        return Function(self._x, self.__array__(), is_periodic=self._is_periodic)

    def __array_ufunc__(self, ufunc, method, *inputs,   **kwargs):
        return Expression(ufunc, method, *inputs, **kwargs)

    def __array__(self) -> np.ndarray:
        if self._y is None:
            self._y = self.__call__()
        elif not isinstance(self._y, np.ndarray):
            self._y = np.asarray(self._y)
        return self._y

    def __repr__(self) -> str:
        return self.__array__().__repr__()

    def __getitem__(self, idx):
        return self.__array__()[idx]

    def __setitem__(self, idx, value):
        raise NotImplementedError()

    def __len__(self):
        return len(self._x)

    @cached_property
    def _ppoly(self):
        d = self.__array__()
        if len(d.shape) == 0:
            d = np.full(self._x.shape, d)
        if self._x.shape != d.shape:
            raise RuntimeError(f"{self._x.shape }!={d.shape}")
        if self.is_periodic:
            ppoly = scipy.interpolate.CubicSpline(self._x, d, bc_type="periodic")
        else:
            ppoly = scipy.interpolate.CubicSpline(self._x, d)
        return ppoly

    def __call__(self, *args, **kwargs):
        if len(args) == 0:
            args = [self._x]

        if callable(self._y):
            res = self._y(*args, **kwargs)
        else:
            res = self._ppoly(*args, **kwargs)

        return res.view(np.ndarray)

    @cached_property
    def derivative(self):
        return Function(self._x, self._ppoly.derivative())

    @cached_property
    def antiderivative(self):
        return Function(self._x, self._ppoly.antiderivative())

    @cached_property
    def invert(self):
        return Function(self.__array__(), self._x, is_periodic=self.is_periodic)

    def pullback(self, *args, **kwargs):
        if len(args) == 0:
            raise ValueError(f"missing arguments!")
        elif len(args) == 2 and args[0].shape == args[1].shape:
            x0, x1 = args
            y = self(x0)
        elif isinstance(args[0], Function) or callable(args[0]):
            logger.warning(f"FIXME: not complete")
            x1 = args[0](self.x)
            y = self.view(np.ndarray)
        elif isinstance(args[0], np.ndarray):
            x1 = args[0]
            y = self(x1)
        else:
            raise TypeError(f"{args}")

        return Function(x1, y, is_periodic=self.is_periodic)

    def integrate(self, a=None, b=None):
        return self._ppoly.integrate(a or self.x[0], b or self.x[-1])


# __op_list__ = ['abs', 'add', 'and',
#                #  'attrgetter',
#                'concat',
#                # 'contains', 'countOf',
#                'delitem', 'eq', 'floordiv', 'ge',
#                # 'getitem',
#                'gt',
#                'iadd', 'iand', 'iconcat', 'ifloordiv', 'ilshift', 'imatmul', 'imod', 'imul',
#                'index', 'indexOf', 'inv', 'invert', 'ior', 'ipow', 'irshift',
#                #    'is_', 'is_not',
#                'isub',
#                # 'itemgetter',
#                'itruediv', 'ixor', 'le',
#                'length_hint', 'lshift', 'lt', 'matmul',
#                #    'methodcaller',
#                'mod',
#                'mul', 'ne', 'neg', 'not', 'or', 'pos', 'pow', 'rshift',
#                #    'setitem',
#                'sub', 'truediv', 'truth', 'xor']

_uni_ops = {
    '__neg__': np.negative,
}
for name, op in _uni_ops.items():
    setattr(Function,  name, lambda s, _op=op: _op(s))

_bi_ops = {

    # Add arguments element-wise.
    "__add__": np.add,
    # (x1, x2, / [, out, where, casting, …]) Subtract arguments, element-wise.
    "__sub__": np.subtract,
    # multiply(x1, x2, / [, out, where, casting, …])  Multiply arguments element-wise.
    "__mul__": np.multiply,
    # (x1, x2, / [, out, casting, order, …])   Matrix product of two arrays.
    "__matmul__": np.matmul,
    # (x1, x2, / [, out, where, casting, …])   Returns a true division of the inputs, element-wise.
    "__truediv__": np.divide,
    # Return x to the power p, (x**p).
    "__pow__": np.power
}


for name, op in _bi_ops.items():
    setattr(Function,  name, lambda s, other, _op=op: _op(s, other))


class PiecewiseFunction(Function):
    def __init__(self, cond, func, *args,    **kwargs) -> None:
        super().__init__(None, None, *args,    **kwargs)
        self._cond = cond
        self._func = func

    def __array__(self) -> np.ndarray:
        raise NotImplementedError()

    def __call__(self, x) -> np.ndarray:
        cond = [c(x) for c in self._cond]
        return np.piecewise(x, cond, self._func)


class Expression(Function):
    def __init__(self, ufunc, method, *inputs,  **kwargs) -> None:

        self._ufunc = ufunc
        self._method = method
        self._inputs = inputs
        self._kwargs = kwargs

        x = next(d.x for d in self._inputs if isinstance(d, Function))
        y = None
        is_periodic = not any([not d.is_periodic for d in self._inputs if isinstance(d, Function)])
        super().__init__(x, y, is_periodic=is_periodic)

    def __call__(self, x: Optional[Union[float, np.ndarray]] = None, *args, **kwargs) -> np.ndarray:
        if x is None:
            x = self._x

        def wrap(x, d):
            if isinstance(d, Function):
                res = d(x).view(np.ndarray)
            elif not isinstance(d, np.ndarray) or len(d.shape) == 0:
                res = d
            elif d.shape == self.x.shape:
                res = Function(self.x, d)(x).view(np.ndarray)
            else:
                raise ValueError(f"{self.x.shape} {d.shape}")

            return res

        if self._method != "__call__":
            op = getattr(self._ufunc, self._method)
            # raise RuntimeError((self._ufunc, self._method))
            res = op(*[wrap(x, d) for d in self._inputs])
        try:
            res = self._ufunc(*[wrap(x, d) for d in self._inputs])
        except Warning as error:
            raise ValueError(
                f"\n {self._ufunc}  {[type(a) for a in self._inputs]}  {[a.shape for a in self._inputs if isinstance(a,Function)]} {error} \n ")
        return res
