import hashlib
import os
from typing import Literal, Optional, Iterator, NamedTuple

GIT_DIR = ".ugit"


def init():
    os.makedirs(GIT_DIR)
    os.makedirs(f"{GIT_DIR}/objects")


class RefValue(NamedTuple):
    symbolic: bool
    value: Optional[str]


def update_ref(ref: str, refval: RefValue, deref: bool = True):
    ref = _get_ref_internal(ref, deref)[0]

    assert refval.value
    if refval.symbolic:
        value = f"ref: {refval.value}"
    else:
        value = refval.value

    ref_path = f"{GIT_DIR}/{ref}"
    os.makedirs(os.path.dirname(ref_path), exist_ok=True)
    with open(ref_path, "w") as f:
        f.write(value)


def get_ref(ref: str, deref: bool = True) -> RefValue:
    return _get_ref_internal(ref, deref)[1]


def _get_ref_internal(ref: str, deref: bool) -> tuple[str, RefValue]:
    ref_path = f"{GIT_DIR}/{ref}"
    value: Optional[str] = None
    if os.path.isfile(ref_path):
        with open(ref_path) as f:
            value = f.read().strip()

    symbolic = bool(value and value.startswith("ref:"))
    if symbolic:
        value = value.split(":", 1)[1].strip()
        if deref:
            return _get_ref_internal(value, deref)

    return ref, RefValue(symbolic=symbolic, value=value)


def iter_refs(prefix: str = "", deref: bool = True) -> Iterator[tuple[str, RefValue]]:
    refs = ["HEAD"]
    for root, _, filenames in os.walk(f"{GIT_DIR}/refs/"):
        root = os.path.relpath(root, GIT_DIR)
        refs.extend(f"{root}/{name}" for name in filenames)

    for refname in refs:
        if not refname.startswith(prefix):
            continue
        yield refname, get_ref(refname, deref)


ObjectType = Literal["blob", "tree", "commit"]


def hash_object(data: bytes, type_: ObjectType) -> str:
    obj = type_.encode() + b"\x00" + data
    oid = hashlib.sha1(obj).hexdigest()
    with open(f"{GIT_DIR}/objects/{oid}", "wb") as out:
        out.write(obj)
    return oid


def get_object(oid: str, expected: Optional[ObjectType]) -> bytes:
    with open(f"{GIT_DIR}/objects/{oid}", "rb") as f:
        obj = f.read()

    type_, _, content = obj.partition(b"\x00")
    type_ = type_.decode()

    if expected is not None:
        assert type_ == expected, f"Expected {expected}, got {type_}"
    return content
