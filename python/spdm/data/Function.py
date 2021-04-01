from functools import cached_property

from matplotlib.pyplot import isinteractive

import numpy as np
from numpy.lib.function_base import piecewise
from scipy import constants
import scipy.interpolate
from scipy.interpolate.interpolate import PPoly

from ..util.logger import logger
from .Quantity import Quantity

# if version.parse(scipy.__version__) <= version.parse("1.4.1"):
#     from scipy.integrate import cumtrapz as cumtrapz
# else:
#     from scipy.integrate import cumulative_trapezoid as cumtrapz

logger.debug(f"Using SciPy Version: {scipy.__version__}")


class PimplFunc(object):
    def __init__(self,  *args,   ** kwargs) -> None:
        super().__init__()

    @property
    def is_periodic(self):
        return False

    @property
    def x(self) -> np.ndarray:
        return NotImplemented

    @property
    def y(self) -> np.ndarray:
        return self.apply(self.x)

    def apply(self, x=None) -> np.ndarray:
        raise NotImplementedError(self.__class__.__name__)

    @cached_property
    def derivative(self):
        return SplineFunction(self.x, self.y, is_periodic=self.is_periodic).derivative

    @cached_property
    def antiderivative(self):
        return SplineFunction(self.x, self.y, is_periodic=self.is_periodic).antiderivative

    def invert(self, x=None):
        x = self.x if x is None else x
        return PimplFunc(self.apply(x), x)


class SplineFunction(PimplFunc):
    def __init__(self, x, y=None, is_periodic=False,  ** kwargs) -> None:
        super().__init__()
        self._is_periodic = is_periodic

        if isinstance(x, PPoly) and y is None:
            self._ppoly = x
        elif not isinstance(x, np.ndarray) or y is None:
            raise TypeError((type(x), type(y)))
        else:
            if callable(y):
                y = y(x)
            elif isinstance(x, np.ndarray) and isinstance(y, np.ndarray):
                assert(x.shape == y.shape)
            elif isinstance(y, (float, int)):
                y = np.full(len(x), y)
            else:
                raise NotImplementedError(f"Illegal input {[type(a) for a in args]}")

            if is_periodic:
                self._ppoly = scipy.interpolate.CubicSpline(x, y, bc_type="periodic", **kwargs)
            else:
                self._ppoly = scipy.interpolate.CubicSpline(x, y, **kwargs)

    @property
    def x(self) -> np.ndarray:
        return self._ppoly.x

    @cached_property
    def derivative(self):
        return SplineFunction(self._ppoly.derivative())

    @cached_property
    def antiderivative(self):
        return SplineFunction(self._ppoly.antiderivative())

    def apply(self, x=None) -> np.ndarray:
        x = self.x if x is None else x
        return self._ppoly(x)


class PiecewiseFunction(PimplFunc):
    def __init__(self, x, cond, func, *args,    **kwargs) -> None:
        super().__init__()
        self._x = x
        self._cond = cond
        self._func = func

    @property
    def x(self) -> np.ndarray:
        return self._x

    def apply(self, x=None) -> np.ndarray:
        if x is None:
            x = self._x
        cond = [c(x) for c in self._cond]
        return np.piecewise(x, cond, self._func)


class Expression(PimplFunc):
    def __init__(self, ufunc, method, *inputs, out=None, **kwargs) -> None:
        super().__init__()
        self._ufunc = ufunc
        self._method = method
        self._inputs = inputs
        self._kwargs = kwargs
        self._out = out

    @property
    def is_periodic(self):
        return all([d.is_periodic for d in self._inputs if isinstance(d, Function)])

    @property
    def x(self):
        return next(d.x for d in self._inputs if isinstance(d, Function))

    @property
    def y(self) -> np.ndarray:
        return self.apply(self.x)

    def apply(self, x=None) -> np.ndarray:
        if x is None:
            x = self.x

        def wrap(x, d):
            if isinstance(d, Function):
                res = d(x).view(np.ndarray)
            elif isinstance(d, np.ndarray) and d.shape == self.x.shape:
                res = Function(self.x, d)(x).view(np.ndarray)
            else:
                res = d
            return res

        d_list = [wrap(x, d) for d in self._inputs]

        obj = next(d for d in d_list if isinstance(d, np.ndarray))

        return obj.__array_ufunc__(self._ufunc, self._method, *d_list, out=self._out)


class Function(np.ndarray):
    @staticmethod
    def __new__(cls, x, y=None, *args, is_periodic=False,   **kwargs):
        if cls is not Function:
            return object.__new__(cls, *args,  is_periodic=is_periodic, **kwargs)
        pimpl = None
        y0 = None
        x0 = None
        if y is None:
            if isinstance(x, Function):
                pimpl = x._pimpl
                y0 = x.view(np.ndarray)
                x0 = x.x
            elif isinstance(x, PimplFunc):
                pimpl = x
                y0 = pimpl.y
                x0 = pimpl.x
            elif isinstance(x, np.ndarray):
                y0 = x
        elif not isinstance(x, np.ndarray):
            raise TypeError(f"x should be np.ndarray not {type(x)}!")
        elif isinstance(y, np.ndarray):
            pimpl = None
            x0 = x
            y0 = y
        elif isinstance(y, Function):
            pimpl = y._pimpl
            y0 = pimpl.apply(x, *args, **kwargs)
            x0 = x
        elif isinstance(y, PimplFunc):
            pimpl = y
            y0 = pimpl.apply(args[0], *args[2:], **kwargs)
            x0 = x
        elif len(args) > 0 and isinstance(y, list) and isinstance(args[0], list):
            pimpl = PiecewiseFunction(x, y, *args, **kwargs)
            y0 = pimpl.apply()
            x0 = pimpl.x

        if not isinstance(y0, np.ndarray):
            raise RuntimeError((type(pimpl), [type(a) for a in args]))
        elif x0 is None or (isinstance(x0, np.ndarray) and x0.shape == y0.shape):
            obj = y0.view(cls)
            obj._pimpl = pimpl
            obj._x = x0
            obj._is_periodic = is_periodic
        else:
            obj = y0
        return obj

    def __array_finalize__(self, obj):
        self._pimpl = getattr(obj, '_pimpl', None)
        self._x = getattr(obj, '_x', None)
        self._is_periodic = getattr(obj, '_is_periodic', False)

    def __array_ufunc__(self, ufunc, method, *inputs,   **kwargs):
        return Function(Expression(ufunc, method, *inputs, **kwargs))

    def __init__(self, *args,  **kwargs):
        pass

    def __getitem__(self, key):
        d = super().__getitem__(key)
        if isinstance(d, np.ndarray) and len(d.shape) > 0:
            d = d.view(Function)
            d._pimpl = self._pimpl
            d._x = self.x[key]
        return d

    @property
    def pimpl(self):
        if self._pimpl is None:
            self._pimpl = SplineFunction(self.x, self.view(np.ndarray), is_periodic=self.is_periodic)
        return self._pimpl

    @property
    def is_periodic(self):
        return self._is_periodic

    @property
    def x(self):
        return self._x

    @cached_property
    def derivative(self):
        return Function(self.pimpl.derivative)

    @cached_property
    def antiderivative(self):
        return Function(self.pimpl.antiderivative)

    @cached_property
    def invert(self):
        return Function(self.pimpl.invert(self._x))

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

        logger.debug((x1.shape, y.shape))

        return Function(x1, y, is_periodic=self.is_periodic)

    def integrate(self, a=None, b=None):
        return self.pimpl.integrate(a or self.x[0], b or self.x[-1])

    def __call__(self,   *args, **kwargs):
        if len(args) == 0:
            args = [self._x]
        return self.pimpl.apply(*args, **kwargs)
