from .Collection import Collection
from .Document import Document
from spdm.util.urilib import urisplit, URISplitResult
from spdm.util.logger import logger


def open_entry(desc, *args, **kwargs):
    if isinstance(desc, str):
        desc = urisplit(desc)
    elif isinstance(desc, URISplitResult):
        pass
    else:
        raise TypeError(f"Illegal uri type! {desc}")

    logger.debug(desc)
    query = dict([tuple(item.split("=")) for item in desc.query.split(',')])
    fragment = dict([tuple(item.split("=")) for item in desc.fragment.split(',')])

    if desc.schema is not None:
        return Collection(f"{desc.schema}://{desc.authority}/{desc.path}", **query).open(**fragment).entry
    else:
        return Document(desc.path, **query).find(**fragment).entry
