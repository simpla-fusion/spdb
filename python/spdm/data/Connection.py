import collections.abc
from copy import deepcopy
from enum import Flag, auto
from typing import Mapping, TypeVar, Union
import pathlib
from spdm.common.logger import logger
from spdm.util.urilib import urisplit_as_dict

from ..common.SpObject import SpObject

_TConnection = TypeVar('_TConnection', bound='Connection')


class Connection(SpObject):
    class Mode(Flag):
        r = auto()  # open for reading (default)
        w = auto()  # open for writing, truncating the file first
        x = auto()  # open for exclusive creation, failing if the file already exists
        a = auto()  # open for writing, appending to the end of the file if it exists

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def __del__(self):
        if self.is_open:
            self.close()

    @property
    def is_open(self) -> bool:
        return False

    def open(self) -> _TConnection:
        # logger.debug(f"[{self.__class__.__name__}]: {self._metadata}")
        return self

    def close(self) -> None:
        # logger.debug(f"[{self.__class__.__name__}]: {self._metadata}")
        return

    def __enter__(self) -> _TConnection:
        return self.open()

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
