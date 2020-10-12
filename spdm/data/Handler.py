
from spdm.util.LazyProxy import LazyProxy
from spdm.util.logger import logger
import pathlib
import collections
from xml.etree import (ElementTree, ElementInclude)
import numpy as np

RefLinker = collections.namedtuple("RefLinker", "schema path")


class Handler(LazyProxy.Handler):
    DELIMITER = LazyProxy.DELIMITER

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class HandlerProxy(Handler):
    def __init__(self, next_handler, mapping_files, *args, mapper=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._next_handler = next_handler
        self._trees = self.load_mapping(mapping_files)

        def default_mapper(xtree, path):
            xpath = ""
            for p in path:
                if type(p) is int:
                    xpath += f"[{p+1}]"
                elif isinstance(p, str):
                    xpath += f"/{p}"
                else:
                    # TODO: handle slice
                    raise TypeError(f"Illegal path type! {type(p)} {path}")

            if len(xpath) > 0 and xpath[0] == "/":
                xpath = xpath[1:]

            return xtree.find(xpath) if xpath != "" else None

        if mapper is None:
            self._mapper = default_mapper
        else:
            self._mapper = lambda xtree, path: mapper(xtree, path)

    def load_mapping(self, path):
        if isinstance(path, str):
            return self.load_mapping(pathlib.Path(path))
        elif isinstance(path, collections.abc.Sequence):
            trees = []
            for fp in path:
                trees.extend(self.load_mapping(fp))
            return trees
        elif not isinstance(path, pathlib.Path):
            return []
        elif path.is_dir():
            trees = []
            for fp in path.glob("*.xml"):
                trees.extend(self.load_mapping(fp))
            return trees

        root = ElementTree.parse(path).getroot()

        # for child in root.findall("{http://www.w3.org/2001/XInclude}include"):
        #     fp = mapping_file.parent/child.attrib["href"]
        #     try:
        #         root.insert(0, ElementTree.parse(fp).getroot())
        #     except ElementTree.ParseError as error:
        #         raise RuntimeError(f"Parse Error in {fp}: {error}")
        #     root.remove(child)

        logger.debug(f"Loading mapping file from {path}")

        return [root]

    def mapping(self, p):
        obj = None
        for tree in self._trees:
            obj = self._mapper(tree, p)
            if obj is not None:
                break

        if not isinstance(obj, ElementTree.Element):
            return obj

        dtype = obj.attrib.get("dtype", None)
        res = None
        if dtype is None and len(obj) > 0:
            res = obj
        elif dtype is None and len(obj) == 0:
            res = obj.text
        elif dtype == "ref":
            res = RefLinker(obj.attrib.get("schema", None), obj.text)
        else:
            if dtype == "string":
                res = obj.text.split(',')
            elif dtype == "int":
                res = [int(v) for v in obj.text.split(',')]
            elif dtype == "float":
                res = [float(v) for v in obj.text.split(',')]
            else:
                raise NotImplementedError(f"Not supported dtype {dtype}!")

            dims = [int(v) for v in obj.attrib.get("dims", "").split(',') if v != '']

            res = np.array(res)
            if len(dims) == 0 and len(res) == 1:
                res = res[0]
            elif len(dims) > 0:
                res = np.array(res).reshape(dims)

        return res

    def put(self, grp, path, value, **kwargs):
        target = self.mapping(path)

        if target is None:
            self._next_handler.put(grp, path, value, **kwargs)
        elif isinstance(target, RefLinker):
            self._next_handler.put(grp, target.path, value, **kwargs)
        else:
            logger.warning(f"Fixed value is not changeable: {path}")

    def get(self, grp, path=[], **kwargs):
        target = self.mapping(path)

        if target is None:
            return self._next_handler.get(grp, path,  **kwargs)
        elif isinstance(target, RefLinker):
            return self._next_handler.get(grp, target.path, **kwargs)
        else:
            return target