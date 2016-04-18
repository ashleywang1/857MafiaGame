"""
Utility function + classes file
"""

from common import *
from enum import Enum
import json

# TODO: Create appropriate custom exception subclasses

#======================================================================
# Handle serialization of enums
# Source: https://stackoverflow.com/a/24482806
#======================================================================
class EnumEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Enum):
            return {"__enum__": str(obj)}
        return json.JSONEncoder.default(self, obj)

def as_enum(d):
    if "__enum__" in d:
        name, member = d["__enum__"].split(".")
        return getattr(globals()[name], member)
    return d
#======================================================================
