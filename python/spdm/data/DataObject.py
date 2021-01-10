import collections
import inspect
import pathlib
import pprint
import re
import os
import numpy as np
from spdm.util.AttributeTree import AttributeTree
from spdm.util.logger import logger
from spdm.util.sp_export import sp_find_module
from spdm.util.SpObject import SpObject
from spdm.util.dict_util import format_string_recursive
from ..util.dict_util import DictTemplate, deep_merge_dict

from .Node import Node


def load_ndarray(desc, value, *args, **kwargs):
    if isinstance(value, np.ndarray):
        return value
    else:
        return NotImplemented


class DataObject(SpObject):

    associations = {
        "general": ".data.General",
        "integer": int,
        "float": float,
        "string": str,
        "ndarray": np.ndarray,

        "file": ".data.File",
        "file.general": ".data.file.GeneralFile",
        "file.bin": ".data.file.Binary",
        "file.hdf5": ".data.file.HDF5",
        "file.netcdf": ".data.file.netCDF",
        "file.namelist": ".data.file.namelist",
        "file.xml": ".data.file.XML",
        "file.json": ".data.file.JSON",
        "file.yaml": ".data.file.YAML",
        "file.txt": ".data.file.TXT",
        "file.csv": ".data.file.CSV",
        "file.numpy": ".data.file.NumPy",
        "file.geqdsk": ".data.file.GEQdsk",
        "file.mdsplus": ".data.db.MDSplus#MDSplusDocument",
    }

    def __new__(cls,   _metadata=None, *args, **kwargs):
        if cls is not DataObject and _metadata is None:
            return SpObject.__new__(cls)

        if isinstance(_metadata, str):
            n_cls = _metadata
            _metadata = {"$class": n_cls}
        elif isinstance(_metadata, collections.abc.Mapping):
            n_cls = _metadata.get("$class", "general")
        else:
            n_cls = cls

        if isinstance(n_cls, str):
            n_cls = n_cls.replace("/", ".").lower()
            if n_cls[0] != '.':
                n_cls = DataObject.associations.get(n_cls, n_cls)
                _metadata = collections.ChainMap({"$class": n_cls}, _metadata)

        return SpObject.__new__(cls, _metadata, *args, **kwargs)

    @staticmethod
    def create(data,  _metadata=None, *args, envs=None, **kwargs):

        if isinstance(_metadata, AttributeTree):
            _metadata = _metadata.__as_native__()

        if not isinstance(data, collections.abc.Mapping):
            pass
        elif "$class" in data:
            _metadata = deep_merge_dict(data, _metadata or {})
            data = None

        if isinstance(envs, object) and hasattr(envs.__class__, "apply"):
            _metadata = envs.apply(_metadata)

        if isinstance(_metadata, collections.abc.Mapping) and data is None:
            data = (envs or {}).get(_metadata.get("$ref", None), None) or _metadata.get("default", None)

        if isinstance(data, collections.abc.Mapping):
            data = {k: DataObject.create(v, envs=envs) for k, v in data.items()}
        elif isinstance(data, list):
            data = [DataObject.create(v, envs=envs) for v in data]
        
        if _metadata is None:
            return data

        if isinstance(_metadata, str):
            _metadata = {"$class": _metadata}
        elif isinstance(_metadata, AttributeTree):
            _metadata = _metadata.__as_native__()
        elif not isinstance(_metadata, collections.abc.Mapping):
            raise TypeError(type(_metadata))

        n_cls = _metadata.get("$class", "")
        n_cls = n_cls.replace("/", ".").lower()
        n_cls = DataObject.associations.get(n_cls, n_cls)

       
        if inspect.isclass(n_cls) and data is not None:
            return n_cls(data)
        elif isinstance(data, DataObject) and data.metadata["$class"] == n_cls:
            return data
        elif not n_cls:
            return data
        else:
            res = DataObject(collections.ChainMap({"$class": n_cls}, _metadata), *args,  **kwargs)
            if data is not None:
                res.update(data)
            return res

    def __init__(self, _metadata=None, *args,  **kwargs):
        super().__init__(*args, **kwargs)

    def __repr__(self):
        return f"<{self.__class__.__name__}>"

    def serialize(self, *args, **kwargs):
        return super().serialize(*args, **kwargs)

    @classmethod
    def deserialize(cls, *args, **kwargs):
        return super().deserialize(cls, *args, **kwargs)

    @property
    def root(self):
        return Node(self)

    @property
    def entry(self):
        return self.root.entry

    @property
    def value(self):
        return NotImplemented

    def update(self, value):
        raise NotImplementedError
