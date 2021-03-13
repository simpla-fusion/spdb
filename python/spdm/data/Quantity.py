import collections
import pprint
from functools import cached_property

import numpy as np
import scipy.constants
import scipy.integrate
from scipy.interpolate import RectBivariateSpline, UnivariateSpline, interp1d

from ..util.logger import logger
from .Annotation import Annotation
from .Coordinates import Coordinates
from .Unit import Unit


class Quantity(np.ndarray):
    """
        A `Quantity` is a property that can exist as a multitude or magnitude, which illustrate discontinuity and continuity.

        A `physical quantity` is a property of a material or system that can be quantified by measurement.

        An `intensive property` is a bulk property, meaning that it is a local physical property of a system that does not depend on
        the system size or the amount of material in the system. Examples of intensive properties include temperature, T; refractive index,
        n; density, ρ; and hardness of an object, η.

        An `extensive properties` such as the mass, volume and entropy of systems are additive for subsystems because they increase and
        decrease as they grow larger and smaller, respectively.

        # psi_func = RectBivariateSpline(dim1, dim2,  ])
        # psi_func = SmoothBivariateSpline(self.r.ravel(), self.z.ravel(), psi_value.ravel())
        # psi_func = lambda *args: spl(*args, grid=False)
    """

    @staticmethod
    def __new__(cls,  value=None, *args, dtype=None, order=None, shape=None, coordinates=None,  **kwargs):

        if isinstance(value, np.ndarray):
            obj = value.view(cls)
        elif value is not None:
            obj = np.asarray(value, dtype=dtype, order=order).view(cls)
        else:
            coordinates = Coordinates(coordinates, *args, coordinates=coordinates, **kwargs) \
                if not isinstance(coordinates, Coordinates) else coordinates
            obj = np.ndarray(coordinates.dataset_shape, dtype=dtype, order=order).view(cls)
            obj._coordinates = coordinates

        if isinstance(obj, np.ndarray):
            obj = obj.view(cls)

        return obj

    def __array_finalize__(self, obj):
        if obj is None:
            return
        self._coordinates = getattr(obj, '_coordinates', None)

    def __init__(self, value=None, *args,  coordinates=None,  unit=None, annotation=None,  **kwargs):
        self._unit = Unit(unit)

        self._annotation = Annotation(annotation or {})

        if not hasattr(self, "_coordinates") or not self._coordinates:
            self._coordinates = Coordinates(*args, coordinates=coordinates, **kwargs)

    def __str__(self):
        return pprint.pformat(self.view(np.ndarray))
        # tag = getattr(self.annotation, '_name',  None) or self.__class__.__name__
        # return f"""<{tag} unit=\"{self._unit}\" coordinates=\"{self.coordinates.name}\"> {self.view(np.ndarray).__repr__()} </{tag}> """

    def put(self, value):
        return self.copy(np.asarray(value))

    def get(self):
        return self.view(np.ndarray)

    def serialize(self):
        return {
            "value": self.view(np.ndarray),
            "unit": self.unit.serialize(),
            "coordinates": self.coordinates.serialize(),
            "uncertainty": {"error_lower": getattr(self, "_error_lower", None),
                            "error_upper": getattr(self, "_error_upper", None)},
        }

    @staticmethod
    def deserialize(cls, d):
        if not isinstance(d, collections.abc.Mapping):
            return Quantity(d)
        else:
            return Quantity(d.get("value", None),
                            dtype=d.get("dtype", None),
                            order=d.get("order", None),
                            unit=d.get("unit", None),
                            coordinates=d.get("coordinates", None),
                            annotation=d.get("annotation", None))

    def __repr__(self):
        return f"<{self.__class__.__name__} unit='{ self._unit}' coordinates='{self._coordinates.__name__}'>"

    def __array_ufunc__(self, ufunc, method, *inputs, out=None, **kwargs):

        if method != "__call__":
            raise NotImplementedError((ufunc, method))
        elif not not out:
            raise NotImplementedError

        unit = Unit.calculate(ufunc, method, *[getattr(a, 'unit', None) for a in inputs])

        # FIXME (salmon 20210302): dimensional analysis

        res = super(Quantity, self).__array_ufunc__(
            ufunc, method, *
            [(in_.__array__() if hasattr(in_.__class__, '__array__') else in_) for in_ in inputs], **kwargs)

        try:
            coordinates = next((n.coordinates for n in inputs if isinstance(n, Quantity)), 'All are Nones')
        except Exception:
            coordinates = None
        # FIXME (salmon 20210302): handle coordinates
        # FIXME (salmon 20210302): handle uncertainty

        if not isinstance(res, Quantity):
            res = Quantity(res, unit=unit, coordinates=coordinates)

        return res

    def __array__(self):
        return super().__array__()

    @property
    def annotation(self):
        return self._annotation

    @property
    def unit(self):
        return self._unit

    @property
    def coordinates(self):
        return self._coordinates

    @property
    def associated(self):
        return self._associated

    @cached_property
    def as_function(self):
        axis = self._coordinates.view(np.ndarray)
        data = self.value
        try:
            res = interp1d(axis, data, kind=self.attributes.interpolator or 'linear')
        except Exception as error:
            logger.debug((error, axis, data))
            raise error
        return res

    def copy(self, other):
        if isinstance(other, Quantity):
            if self._coordinates is other._coordinates:
                np.copyto(self, other.value)
            else:
                np.copyto(self, other(self._coordinates))
        elif not isinstance(other, np.ndarray):
            self.fill(other)
        elif self.shape == other.shape:
            np.copyto(self, other)
        else:
            raise ValueError(f"Can not copy object! {type(other)} [{self.shape}, {other.shape}]  ")

    def __call__(self,   *args, **kwargs):
        if x_axis is self._coordinates or x_axis is None:
            return self
        res = self.as_function(x_axis)
        if isinstance(res, Quantity):
            if not hasattr(res, "_axis"):
                res._coordinates = x_axis
        elif isinstance(res, np.ndarray):
            if len(res.shape) == 0:
                res = res.item()
            elif res.size == 1:
                res = res[0]
            else:
                res = res.view(Quantity)
                res._coordinates = x_axis
                res._attributes = self.attributes

        return res

        # def derivative_n(self, n, *args, **kwargs):
        #     self.evaluate()
        #     return Quantity(self.as_function.derivative(n=n)(self._coordinates), axis=self._coordinates)
        # func = getattr(self, "_ufunc", None)
        # if func is None:
        # elif callable(func) or isinstance(func, types.BuiltinFunctionType):
        #     v0 = scipy.misc.derivative(func, self._coordinates[0], dx=self._coordinates[1]-self._coordinates[0], n=n, **kwargs)
        #     vn = scipy.misc.derivative(func, self._coordinates[-1], dx=self._coordinates[-1]-self._coordinates[-2], n=n, **kwargs)
        #     v = [scipy.misc.derivative(func, x, dx=0.5*(self._coordinates[i+1]-self._coordinates[i-1]),
        #                                n=n, *args, **kwargs) for i, x in enumerate(self._coordinates[1:-1])]
        #     return Quantity(np.array([v0]+v+[vn]), axis=self._coordinates)

    def diff(self, *args, **kwargs):
        """
            differential
        """
        # value = UnivariateSpline(self._coordinates, self.value).derivative()(self._coordinates)
        # return Quantity(value[:], axis=self._coordinates)
        return Quantity(np.gradient(self[:])/np.gradient(self._coordinates[:]), axis=self._coordinates)

    @cached_property
    def dln(self, *args, **kwargs):
        r"""
            .. math:: d\ln f=\frac{df}{f}
        """
        data = np.ndarray(self._coordinates.shape, dtype=self.dtype)
        data[1:] = self.diff()[1:]/self[1:]
        data[0] = 2*data[1]-data[2]

        if any(np.isnan(data)):
            raise ValueError(data)

        return Quantity(data, coordinates=self._coordinates)

    def integral(self, *args, **kwargs):
        return Quantity(scipy.integrate.cumtrapz(self.value, self.axis, initial=0.0), axis=self.axis)

    def inv_integral(self, *args, **kwargs):
        value = scipy.integrate.cumtrapz(self.value[::-1], self.axis[::-1], initial=0.0)[::-1]
        return Quantity(value, axis=self.axis)

        # if isinstance(start, np.ndarray) and isinstance(stop, np.ndarray):
        #     raise ValueError(f"Illegal arguments! start is {type(start)} ,end is {type(stop)}")
        # elif isinstance(start, np.ndarray):
        #     value =self.

        #     res = Quantity(np.array([scipy.integrate.quad(func, x, stop)[0] for x in start]), axis=start)
        # elif isinstance(stop, np.ndarray):
        #     res = Quantity(np.array([scipy.integrate.quad(func, start, x)[0] for x in stop]), axis=stop)
        # else:
        #     res = scipy.integrate.quad(func, start, stop)
        # return res
        # self.evaluate()
        # if start is None:
        #     start = self._coordinates
        # if stop is None:
        #     stop = self._coordinates
        # func = getattr(self, "_ufunc", None) or self.as_function
        # if func is None:
        #     spl = self.as_function
        #     if isinstance(start, np.ndarray) and isinstance(stop, np.ndarray):
        #         raise ValueError(f"Illegal arguments! start is {type(start)} ,end is {type(end)}")
        #     elif isinstance(start, np.ndarray):
        #         res = Quantity(np.array([spl.integral(x, stop) for x in start]), axis=start)
        #     elif isinstance(stop, np.ndarray):
        #         res = Quantity(np.array([spl.integral(start, x) for x in stop]), axis=stop)
        #     else:
        #         res = spl.integral(start, stop)
        # else:


# class QuantityGroup(Group):
#     """
#      A `QuantityGroup` is a set of `Quantity` with same `Coordiantes`.
#     """
#     def __init__(self, *args, name=None, parent=None,  coordinates=None, **kwargs):
#         self._coordinates = Coordinates(coordinates) if not isinstance(coordinates, Coordinates) else coordinates
#         def defaultfactory(*args, coordinates=self._coordinates, **kwargs):
#             return Quantity(*args, coordinates=coordinates, **kwargs)
#         super().__init__(*args, name=name, parent=parent, defaultfactory=defaultfactory, **kwargs)
# class QuantityFunction(Quantity):
#     def __init__(self, ufunc,   *args,  **kwargs):
#         super().__init__(*args, **kwargs)
#         if not callable(ufunc):
#             raise TypeError(type(ufunc))
#         elif not isinstance(ufunc, np.ufunc):
#             ufunc = np.vectorize(ufunc)
#         self._ufunc = ufunc
#     def __call__(self, x=None):
#         if x is None:
#             x = self._coordinates
#         if x is None:
#             raise ValueError(f" x is None !")
#         res = self._ufunc(x)
#         if isinstance(res, np.ndarray) and not isinstance(res, Quantity):
#             res = res.view(Quantity)
#             res._coordinates = x
#         return res
#     def __getitem__(self, idx):
#         return self._ufunc(self._coordinates[idx])
#     @property
#     def value(self):
#         if self.shape == ():
#             try:
#                 self.resize(self._coordinates.size, refcheck=True)
#                 self.reshape(self._coordinates.shape)
#             except Exception:
#                 res = self._ufunc(self._coordinates)
#             else:
#                 np.copyto(self, self._ufunc(self._coordinates))
#                 res = self.view(np.ndarray)
#         else:
#             res = self.view(np.ndarray)
#         return res
#     @cached_property
#     def derivative(self):
#         return Quantity(np.gradient(self.value)/np.gradient(self._coordinates), axis=self._coordinates)
#     @cached_property
#     def dln(self, *args, **kwargs):
#         r"""
#             .. math:: d\ln f=\frac{df}{f}
#         """
#         return Quantity(self.derivative.value/self.value, axis=self._coordinates)
#     @cached_property
#     def integral(self):
#         data = scipy.integrate.cumtrapz(self[:], self.axis[:], initial=0.0)
#         return Quantity(data, axis=self.axis)
#     @cached_property
#     def inv_integral(self):
#         value = scipy.integrate.cumtrapz(self[::-1], self.axis[::-1], initial=0.0)[::-1]
#         return Quantity(value, axis=self.axis)
# class QuantityExpression(Quantity):
#     def __init__(self,    func,   *args, func_args=None, func_kwargs=None,  **kwargs):
#         self._func = func
#         self._args = func_args or []
#         self._kwargs = func_kwargs or {}
#         super().__init__(*args, **kwargs)
#     def __str__(self):
#         return self.__repr__()
#     def __repr__(self):
#         return f"<{self.__class__.__name__} ufunc={self._func}  >"
#     def __call__(self, x_axis=None):
#         if x_axis is None:
#             x_axis = self._coordinates
#         args = []
#         for arg in self._args:
#             if isinstance(arg,  Quantity):
#                 data = arg(x_axis)
#             else:
#                 data = arg
#             if isinstance(data, Quantity):
#                 args.append(data.view(np.ndarray))
#             else:
#                 args.append(data)
#         res = self._func(*args, **self._kwargs)
#         if isinstance(res, np.ndarray) and res.shape != () and (any(np.isnan(res)) or any(np.isinf(res))):
#             raise ValueError(res)
#         if isinstance(res, np.ndarray) and not isinstance(res, Quantity):
#             res = res.view(Quantity)
#             res._coordinates = x_axis
#         return res
#     def __getitem__(self, idx):
#         args = []
#         if not hasattr(self, "_args"):
#             return self.view(np.ndarray)[idx]
#         for arg in self._args:
#             if not isinstance(arg,  np.ndarray):
#                 args.append(arg)
#             elif not isinstance(arg, Quantity):
#                 args.append(arg[idx])
#             elif arg.axis is self.axis:
#                 args.append(arg[idx])
#             else:
#                 data = arg(self._coordinates[idx])
#                 if isinstance(data, np.ndarray):
#                     args.append(data.view(np.ndarray))
#                 else:
#                     args.append(data)
#         return self._func(*args, **self._kwargs)
#     def __setitem__(self, idx, value):
#         if self.shape != self._coordinates.shape:
#             self.evaluate()
#         self.view(np.ndarray)[idx] = value
#     def evaluate(self):
#         if self.shape != self._coordinates.shape:
#             self.resize(self._coordinates.size, refcheck=False)
#             self.reshape(self._coordinates.shape)
#         np.copyto(self, self[:])
#     @property
#     def value(self):
#         return self[:]
# class Quantitys():
#     """ Collection of Quantitys with same x-axis
#     """
#     def __init__(self, cache=None, *args,  axis=None,  parent=None, **kwargs):
#         super().__init__(**kwargs)
#         if isinstance(cache, LazyProxy) :
#             self.__dict__["_cache"] = cache
#         else:
#             self.__dict__["_cache"] = (cache)
#         if isinstance(axis, str):
#             axis = self._cache[axis]
#         self.__dict__["_axis"] = axis
#     def _create(self, d=None, name=None, **kwargs):
#         if isinstance(d, Quantity) and not hasattr(d, "_axis"):
#             d._coordinates = self._coordinates
#         else:
#             d = Quantity(d, axis=self._coordinates, description={"name": name, **kwargs})
#         return d
#     def __missing__(self, key):
#         d = self._cache[key]
#         if isinstance(d, LazyProxy):
#             d = d()
#         if d in (None, [], {}, NotImplemented) or len(d) == 0:
#             return None
#         else:
#             return self.__as_object__().setdefault(key, self._create(d, name=key))
#     def __normalize__(self, value, name=None):
#         if isinstance(value, Quantity):
#             res = value(self._coordinates)
#         elif isinstance(value, np.ndarray) or callable(value):
#             res = Quantity(value, axis=self._coordinates,  description={"name": name})
#         elif isinstance(value, collections.abc.Mapping):
#             res = {k: self.__normalize__(v, k) for k, v in value.items()}
#         elif isinstance(value, list):
#             res = [self.__normalize__(v, f"{name or ''}_{idx}") for idx, v in enumerate(value)]
#         else:
#             res = value
#         return res
#     # def __setitem__(self, key, value):
#     #     super().__setitem__(key, self.__normalize__(value, key))
#     @lru_cache
#     def cache(self, key):
#         res = self._cache[key.split(".")]
#         if isinstance(res, LazyProxy):
#             res = res()
#         return res
#     def _fetch_Quantity(self, desc, prefix=[]):
#         if isinstance(desc, str):
#             path = desc
#             opts = {"label": desc}
#         elif isinstance(desc, collections.abc.Mapping):
#             path = desc.get("name", None)
#             opts = desc.get("opts", {})
#         elif isinstance(desc, tuple):
#             path, opts = desc
#
#         else:
#             raise TypeError(f"Illegal Quantity type! {desc}")
#         if isinstance(opts, str):
#             opts = {"label": opts}
#         if prefix is None:
#             prefix = []
#         elif isinstance(prefix, str):
#             prefix = prefix.split(".")
#         if isinstance(path, str):
#             path = path.split(".")
#         path = prefix+path
#         if isinstance(path, np.ndarray):
#             data = path
#         else:
#             data = self[path]
#         # else:
#         #     raise TypeError(f"Illegal data type! {prefix} {type(data)}")
#         return data, opts
#     def plot(self, Quantitys, fig_axis=None, axis=None,  prefix=None):
#         if isinstance(Quantitys, str):
#             Quantitys = Quantitys.split(",")
#         elif not isinstance(Quantitys, collections.abc.Sequence):
#             Quantitys = [Quantitys]
#         if prefix is None:
#             prefix = []
#         elif isinstance(prefix, str):
#             prefix = prefix.split(".")
#         elif not isinstance(prefix, collections.abc.Sequence):
#             prefix = [prefix]
#         axis, axis_opts = self._fetch_Quantity(axis, prefix=prefix)
#         fig = None
#         if isinstance(fig_axis, collections.abc.Sequence):
#             pass
#         elif fig_axis is None:
#             fig, fig_axis = plt.subplots(ncols=1, nrows=len(Quantitys), sharex=True)
#         elif len(Quantitys) == 1:
#             fig_axis = [fig_axis]
#         else:
#             raise RuntimeError(f"Too much Quantitys!")
#         for idx, data in enumerate(Quantitys):
#             ylabel = None
#             opts = {}
#             if isinstance(data, tuple):
#                 data, ylabel = data
#             if not isinstance(data, list):
#                 data = [data]
#             for d in data:
#                 value, opts = self._fetch_Quantity(d,  prefix=prefix)
#                 if value is not NotImplemented and value is not None and len(value) > 0:
#                     fig_axis[idx].plot(axis, value, **opts)
#                 else:
#                     logger.error(f"Can not find Quantity '{d}'")
#             fig_axis[idx].legend(fontsize=6)
#             if ylabel:
#                 fig_axis[idx].set_ylabel(ylabel, fontsize=6).set_rotation(0)
#             fig_axis[idx].labelsize = "media"
#             fig_axis[idx].tick_params(labelsize=6)
#         fig_axis[-1].set_xlabel(axis_opts.get("label", ""),  fontsize=6)
#         return fig_axis, fig