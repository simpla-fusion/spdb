import collections
import copy
import pprint
import uuid

import numpy as np
from spdm.util.LazyProxy import LazyProxy
from spdm.util.logger import logger
from .Entry import Entry


class _TAG_:
    pass


class _NEXT_TAG_(_TAG_):
    pass


class _LAST_TAG_(np.ndarray, _TAG_):
    @staticmethod
    def __new__(cls,   *args,   **kwargs):
        return np.asarray(-1).view(cls)

    def __init__(self, *args, **kwargs) -> None:
        pass


_next_ = _NEXT_TAG_()
_last_ = _LAST_TAG_()


class Node:
    """
        @startuml

        class Node{
            name    : String
            parent  : Node
            value   : Group or Data
        }

        class Group{
            children : Node[*]
        }

        Node *--  Node  : parent

        Node o--  Group : value
        Node o--  Data  : value

        Group *-- "*" Node

        @enduml
    """

    class Mapping:
        def __init__(self, data=None, *args,  parent=None, **kwargs):
            self._parent = parent
            self._data = data or dict()

        def serialize(self):
            return {k: (v.serialize() if hasattr(v, "serialize") else v) for k, v in self.items()}

        @staticmethod
        def deserialize(cls, d, parent=None):
            res = cls(parent)
            res.update(d)
            return res

        def __repr__(self) -> str:
            return pprint.pformat(getattr(self, "_data", None))

        def __getitem__(self, key):
            return self._data[key]

        def __setitem__(self, key, value):
            self.insert(value, key)

        def __delitem__(self, k):
            del self._data[k]

        def __len__(self):
            return len(self._data)

        def __contain__(self, k):
            return k in self._data

        def __iter__(self):
            for node in self._data.values():
                if hasattr(node, "__value__"):
                    yield node.__data__
                else:
                    yield node

        def __merge__(self, d,  recursive=True):
            return NotImplemented

        def __ior__(self, other):
            return self.__merge__(other, recursive=True)

        """
            @startuml
            [*] --> Group

            Group       --> Mapping         : update(dict),insert(value,str),at(str)
            Group       --> Sequence        : update(list),insert(value,int),[_next_]

            Mapping     --> Mapping         : insert(value,key), at(key),
            Mapping     --> Sequence        : [_next_],

            Sequence    --> Sequence        : insert(value), at(int),
            Sequence    --> Illegal         : insert(value,str),get(str)

            Illegal     --> [*]             : Error

            @enduml
        """

        def update(self, other, *args, **kwargs):
            if other is None:
                return
            elif isinstance(other, collections.abc.Mapping):
                for k, v in other.items():
                    self.insert(v, k, *args, **kwargs)
            elif isinstance(other, collections.abc.Sequence):
                for v in other:
                    self.insert(v, None, *args, **kwargs)
            else:
                raise TypeError(f"Not supported operator! update({type(self)},{type(other)})")

        def insert(self, value, key=None, *args, **kwargs):
            res = self._data.get(key, None) or self._data.setdefault(
                key, self._parent.__new_node__(name=key, parent=self))
            res.__update__(value, *args, **kwargs)
            return res

        # def at(self, key):
        #     return self.__getitem__(key)

    class Sequence:
        def __init__(self, data=None,   *args, parent=None, **kwargs) -> None:
            self._parent = parent
            self._data = data or list()

        def serialize(self):
            return [(v.serialize() if hasattr(v, "serialize") else v) for v in self]

        @staticmethod
        def deserialize(cls, d, parent=None):
            return cls(d, parent)

        def __repr__(self) -> str:
            return pprint.pformat(getattr(self, "_data", None))

        def __getitem__(self, key):
            return self._data[key]

        def __setitem__(self, key, value):
            self.insert(value, key)

        def __delitem__(self, k):
            del self._data[k]

        def __len__(self, k):
            return len(self._data)

        def __contain__(self, k):
            return k in self._data

        def __iter__(self):
            for node in self._data:
                if hasattr(node, "__value__"):
                    yield node.__value__
                else:
                    yield node

        def insert(self, value, key=None, *args, **kwargs):
            if isinstance(key, int):
                res = self._data.__getitem__(key)
            else:
                self._data.append(self._parent.__new_node__(name=key, parent=self))
                res = self._data.__getitem__(-1)

            res.__update__(value, *args, **kwargs)
            return res

        # def at(self, key):
        #     if isinstance(key, (int, slice)):
        #         return self.__getitem__(key)
        #     else:
        #         raise KeyError(key)

        def update(self, other, *args, **kwargs):
            if isinstance(other, collections.abc.Sequence):
                for v in other:
                    self.insert(v, *args, **kwargs)
            else:
                raise TypeError(f"Not supported operator! update({type(self)},{type(other)})")

    def __init__(self, value=None, *args,  name=None, parent=None, **kwargs):

        self._name = name or uuid.uuid1()

        self._parent = parent

        self._data = None

        if isinstance(value, Node):
            self._data = value._data
        elif isinstance(value, (Node.Mapping, Node.Sequence, type(None), LazyProxy)):
            self._data = value
        else:
            self.__update__(value)

    def __repr__(self) -> str:
        return pprint.pformat(self._data) if not isinstance(self._data, str) else f"'{self._data}'"

    def __new_node__(self, *args, **kwargs):
        return self.__class__(*args,  **kwargs)

    def copy(self):
        if isinstance(Node, (Node.Mapping, Node.Sequence)):
            return self.__new_node__(self._data.copy())
        else:
            return self.__new_node__(copy.copy(self._data))

    def serialize(self):
        return self._data.serialize() if hasattr(self._data, "serialize") else self._data

    @staticmethod
    def deserialize(cls, d):
        return cls(d)

    @property
    def __name__(self):
        return self._name

    @property
    def __value__(self):
        if isinstance(self._data, LazyProxy):
            return self._data.__fetch__()
        else:
            return self._data

    @property
    def __parent__(self):
        return self._parent

    @property
    def __metadata__(self):
        return self._metadata

    def __hash__(self) -> int:
        return hash(self._name)

    def __clear__(self):
        self._data = None

    """
        @startuml
        [*] --> Empty
        Empty       --> Sequence        : as_sequence, __update__(list), __setitem__(int,v),__getitem__(int)
        Empty       --> Mapping         : as_mapping , __update__(dict), __setitem__(str,v),__getitem__(str)
        Empty       --> Empty           : clear


        Item        --> Item            : "__value__"
        Item        --> Empty           : clear
        Item        --> Sequence        : __setitem__(_next_,v),__getitem__(_next_),as_sequence
        Item        --> Illegal         : as_mapping

        Sequence    --> Empty           : clear
        Sequence    --> Sequence        : as_sequence
        Sequence    --> Illegal         : as_mapping

        Mapping     --> Empty           : clear
        Mapping     --> Mapping         : as_mapping
        Mapping     --> Sequence        :  __setitem__(_next_,v),__getitem__(_next_),as_sequence


        Illegal     --> [*]             : Error

        @enduml
    """

    def __as_mapping__(self, value=None,  force=True):
        if isinstance(self._data, Node.Mapping):
            if value is not None:
                self._data.update(value)
        elif self._data is None and force:
            self._data = self.__class__.Mapping(value, parent=self)
        else:
            raise ValueError(f"{type(self._data)} is not a Mapping!")
        return self._data

    def __as_sequence__(self, value=None, force=False):
        if isinstance(self._data, Node.Sequence):
            if value is not None:
                self._data.update(value)
        elif self._data is None and force:
            self._data = self.__class__.Sequence(value, parent=self)
        else:
            raise ValueError(f"{type(self._data)} is not a Sequence!")
        return self._data

    def __update__(self, value, * args,   **kwargs):
        value = self.__pre_process__(value, *args, **kwargs)

        if isinstance(value, collections.abc.Mapping):
            self.__as_mapping__(value, force=True)
        elif isinstance(value, collections.abc.Sequence) and not isinstance(value, str):
            self.__as_sequence__(value,  force=True)
        else:
            self._data = value

    def __pre_process__(self, value, *args, **kwargs):
        return value

    def __post_process__(self, value, *args, **kwargs):
        if isinstance(value, (collections.abc.Mapping, collections.abc.Sequence)):
            return self.__class__(value)
        elif not isinstance(value, Node):
            return value
        elif isinstance(value._data, (collections.abc.Mapping, collections.abc.Sequence, type(None))):
            return self.__class__(value._data)
        else:
            return value._data

    def __setitem__(self, path, value):
        value = self.__pre_process__(value)
        if isinstance(self._data, LazyProxy):
            return self._data.__setitem__(path, value)
        elif path is None or (isinstance(path, collections.abc.Sequence) and len(path) == 0):
            self._data = value
            return
        elif isinstance(self._data, Entry):
            return self._data.set(path, value)
        elif isinstance(path, str):
            path = path.split('.')
        elif not isinstance(path, list):
            path = [path]

        if isinstance(self._data, LazyProxy):
            self._data[path] = value
        else:
            obj = self

            for k in path:
                if isinstance(k, str):
                    obj = obj.__as_mapping__(force=True).insert(None, k)
                else:
                    obj = obj.__as_sequence__(force=True).insert(None, k)

            obj.__update__(value)

    def __getitem__(self, path):
        if isinstance(self._data, LazyProxy):
            return self.__post_process__(self._data.__getitem__(path))
        elif path is None or (isinstance(path, collections.abc.Sequence) and len(path) == 0):
            return self.__post_process__(self._data)
        elif isinstance(path, str):
            path = path.split('.')
        elif not isinstance(path, list):
            path = [path]

        obj = self
        for i, key in enumerate(path):
            try:
                if isinstance(key, str):
                    res = obj.__as_mapping__(force=False)[key]
                elif isinstance(key, _TAG_):
                    res = obj.__as_sequence__(force=True)[key]
                else:
                    res = obj.__as_sequence__(force=False)[key]
            except Exception as error:
                raise KeyError(path)
                break
            else:
                obj = res

        return self.__post_process__(obj)

    def __delitem__(self, key):
        if isinstance(self._data, LazyProxy):
            self._data.__delitem__(key)
        elif key is None or len(key) == 0:
            self.__clear__()
        elif isinstance(key, str) and isinstance(self._data, collections.abc.Mapping):
            del self._data[key]
        elif not isinstance(key, str) and isinstance(self._data, collections.abc.Sequence):
            del self._data[key]
        else:
            raise RuntimeError((type(self._data), type(key)))

    # def __missing__(self, path):
    #     return LazyProxy(self._data, prefix=path)

    def __contains__(self, key):
        if isinstance(self._data, LazyProxy):
            return self._data.__contains__(key)
        elif isinstance(key, str) and isinstance(self._data, collections.abc.Mapping):
            return key in self._data
        elif not isinstance(key, str) and isinstance(self._data, collections.abc.Sequence):
            return key >= 0 and key < len(self._data)
        else:
            return False

    def __len__(self):
        if isinstance(self._data, LazyProxy):
            return self._data.__len__()
        elif isinstance(self._data, (collections.abc.Mapping, collections.abc.Sequence)) and not isinstance(self._data, str):
            return len(self._data)
        else:
            return 0 if self._data is None else 1

    def __iter__(self):
        if isinstance(self._data, LazyProxy):
            yield from map(lambda v: self.__post_process__(v), self._data.__iter__())
        elif isinstance(self._data, collections.abc.Mapping):
            yield from map(lambda v: self.__post_process__(v), self._data.values())
        elif isinstance(self._data, collections.abc.Sequence) and not isinstance(self._data, str):
            yield from map(lambda v: self.__post_process__(v), self._data)
        else:
            yield self.__post_process__(self._data)

    class __lazy_proxy__:
        @staticmethod
        def put(self, path, value):
            self.__setitem__(path, value)

        @staticmethod
        def get(self, path):
            return self.__getitem__(path)

        @staticmethod
        def count(self, path):
            if isinstance(self._data, LazyProxy):
                return len(self._data)
            else:
                return Node.__getitem__(self, path)

        # @staticmethod
        # def iter(self, path):
        #     obj = self[path]
        #     logger.debug(obj)
            # yield obj
            # if isinstance(path, str):
            #     path = path.split('.')

            # obj = self
            # for i, k in enumerate(path):
            #     if isinstance(k, str):
            #         obj = obj.__as_mapping__()
            #     try:
            #         obj = obj[k]
            #     except KeyError:
            #         raise KeyError('.'.join(map(str, path[:i+1])))

            # return None

        # def delete(self, key):
        #     if isinstance(self.__data__, collections.abc.Mapping) or isinstance(self.__data__, collections.abc.Sequence):
        #         try:
        #             del self.__data__[key]
        #         except KeyError:
        #             pass

        # def contain(self, key):
        #     if self.__data__ is None:
        #         return False
        #     elif isinstance(key, str):
        #         return key in self.__data__
        #     elif type(key) is int:
        #         return key < len(self.__data__)
        #     else:
        #         raise KeyError(key)

        # def iter(self):
        #     if self.__data__ is None:
        #         return
        #     elif isinstance(self.__data__,  collections.abc.Mapping):
        #         for k, v in self.__data__.items():
        #             if isinstance(v, collections.abc.Mapping):
        #                 v = PhysicalGraph(v)

        #             yield k, v
        #     else:
        #         for v in self.__data__:
        #             if isinstance(v, collections.abc.Mapping):
        #                 v = PhysicalGraph(v)
        #             yield v
