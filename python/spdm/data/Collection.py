import collections
import inspect
import pathlib
import re
import urllib
from typing import Any, Dict, List, NewType, Tuple
from functools import cached_property
import numpy
from spdm.util.AttributeTree import AttributeTree
from spdm.util.logger import logger
from spdm.util.sp_export import sp_find_module
from spdm.util.urilib import urisplit, uriunsplit
from spdm.util.SpObject import SpObject

from .Document import Document

InsertOneResult = collections.namedtuple("InsertOneResult", "inserted_id success")
InsertManyResult = collections.namedtuple("InsertManyResult", "inserted_ids success")
UpdateResult = collections.namedtuple("UpdateResult", "upserted_id success")
DeleteResult = collections.namedtuple("DeleteResult", "deleted_id success")


class Collection(SpObject):
    ''' Collection of documents
    '''
    DOCUMENT_CLASS = Document

    associations = {
        "mapping": f"{__package__}.db.Mapping",
        "local": f"{__package__}.db.LocalFile",

        "mds": f"{__package__}.db.MDSplus",
        "mdsplus": f"{__package__}.db.MDSplus",

        "mongo": f"{__package__}.db.MongoDB",
        "mongodb": f"{__package__}.db.MongoDB",
    }
    metadata = AttributeTree()

    @staticmethod
    def __new__(cls, desc=None, *args, schema=None, **kwargs):
        if cls is not Collection:
            return object.__new__(cls)
            # return super(Collection, cls).__new__(desc, *args, **kwargs)

        if isinstance(desc, str):
            desc = urisplit(desc)

        if isinstance(desc, AttributeTree):
            desc = desc.__as_native__()

        schema = (schema or desc.get("schema", "local")).split("+")[0]

        n_cls = Collection.associations.get(schema.lower(), f"{__package__}.db.{schema}")

        if isinstance(n_cls, str):
            n_cls = sp_find_module(n_cls)

        if inspect.isclass(n_cls):
            res = object.__new__(n_cls)
        elif callable(n_cls):
            res = n_cls()
        else:
            raise RuntimeError(f"Illegal schema! {schema} {n_cls} {desc}")

        return res

    def __init__(self, desc, *args, id_hasher=None, envs=None, **kwargs):
        super().__init__(attributes=desc)

        logger.info(f"Open {self.__class__.__name__} : \n {desc}")

        self._id_hasher = id_hasher or "{_id}"

        self._envs = collections.ChainMap(kwargs, envs or {})

    @cached_property
    def envs(self):
        return AttributeTree(self._envs)

    @property
    def is_writable(self):
        return "w" in self.metadata.mode

    @property
    def handler(self):
        return self._handler

    # mode in ["", auto_inc  , glob ]
    def guess_id(self, d, auto_inc=True):
        fid = None
        if callable(self._id_hasher):
            fid = self._id_hasher(self, d, auto_inc)
        elif isinstance(self._id_hasher, str):
            try:
                fid = self._id_hasher.format_map(d)
            except KeyError:
                if auto_inc:
                    fid = self._id_hasher.format(_id=self.count())
                else:
                    raise RuntimeError(f"Can not get id from {d}!")

        return fid

    def open_document(self, fid, mode):
        logger.debug(f"Opend Document: {fid} mode=\"{mode}\"")
        raise NotImplementedError()

    def insert(self, *args, **kwargs):
        return self.insert_one(*args, **kwargs)

    def open(self, *args, mode="r", **kwargs):
        if "w" in mode and self.is_writable:
            return self.insert_one(*args, **kwargs)
        elif "w" not in mode:
            return self.find_one(*args, **kwargs)
        else:
            raise RuntimeWarning("Collection is not writable!")

    def find_one(self, predicate=None, *args, **kwargs):
        raise NotImplementedError()

    def find(self, predicate=None, projection=None, *args, **kwargs):
        raise NotImplementedError()

    def insert_one(self, data=None, *args, **kwargs) -> InsertOneResult:
        raise NotImplementedError()

    def insert_many(self, documents, *args, **kwargs) -> InsertManyResult:
        return [self.insert_one(doc, *args, **kwargs) for doc in documents]

    def replace_one(self, predicate, replacement,  *args, **kwargs) -> UpdateResult:
        raise NotImplementedError()

    def update_one(self, predicate, update,  *args, **kwargs) -> UpdateResult:
        raise NotImplementedError()

    def update_many(self, predicate, updates: list,  *args, **kwargs) -> UpdateResult:
        return [self.update_one(predicate, update, *args, **kwargs) for update in updates]

    def delete_one(self, predicate,  *args, **kwargs) -> DeleteResult:
        raise NotImplementedError()

    def delete_many(self, predicate, *args, **kwargs) -> DeleteResult:
        raise NotImplementedError()

    def count(self, predicate=None, *args, **kwargs) -> int:
        raise NotImplementedError()

    ######################################################################
    # TODO(salmon, 2019.07.01) support index

    def create_indexes(self, indexes: List[str], session=None, **kwargs):
        raise NotImplementedError()

    def create_index(self, keys: List[str], session=None, **kwargs):
        raise NotImplementedError()

    def ensure_index(self, key_or_list, cache_for=300, **kwargs):
        raise NotImplementedError()

    def drop_indexes(self, session=None, **kwargs):
        raise NotImplementedError()

    def drop_index(self, index_or_name, session=None, **kwargs):
        raise NotImplementedError()

    def reindex(self, session=None, **kwargs):
        raise NotImplementedError()

    def list_indexes(self, session=None):
        raise NotImplementedError()