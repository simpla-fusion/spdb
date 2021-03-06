import collections
from typing import Mapping, Type

import numpy as np

from ..common.SpObject import SpObject
from ..common.logger import logger


def load_ndarray(desc, value, *args, **kwargs):
    if hasattr(value, "__array__"):
        return value.__array__()
    else:
        return NotImplemented


# SpObject.schema.update(
#     {
#         "general": ".data.General",
#         "integer": int,
#         "float": float,
#         "string": str,
#         "array": np.ndarray,
#     }
# )


class DataObject(SpObject):

    def __init__(self,  *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __repr__(self):
        return f"<{self.__class__.__name__}>"

    def serialize(self, *args, **kwargs):
        return super().serialize(*args, **kwargs)

    @classmethod
    def deserialize(cls, metadata):
        if isinstance(metadata, collections.abc.Mapping):
            n_cls = metadata.get("$class", None)
        elif isinstance(metadata, str):
            n_cls = urisplit(metadata)["schema"] or metadata
        else:
            n_cls = None

        if cls is not DataObject and not n_cls:
            n_cls = cls
        elif isinstance(n_cls, str) and not n_cls.startswith("."):
            n_cls = DataObject.schema.get(n_cls.lower(), None)

        return super().deserialize(n_cls)
