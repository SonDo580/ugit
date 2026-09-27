import hashlib
import os
import json
import shutil
from contextlib import contextmanager
from typing import Literal, Optional, Iterator, NamedTuple

GIT_DIR = None  # Will be initialized in cli.main()


@contextmanager
def change_git_dir(new_dir: str):
    global GIT_DIR
    old_dir = GIT_DIR
    GIT_DIR = f"{new_dir}/.ugit"
    yield
    GIT_DIR = old_dir


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


def delete_ref(ref: str, deref: bool = True):
    ref = _get_ref_internal(ref, deref)[0]
    os.remove(f"{GIT_DIR}/{ref}")


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
    refs = ["HEAD", "MERGE_HEAD"]
    for root, _, filenames in os.walk(f"{GIT_DIR}/refs/"):
        root = os.path.relpath(root, GIT_DIR)
        refs.extend(f"{root}/{name}" for name in filenames)

    for refname in refs:
        if not refname.startswith(prefix):
            continue
        ref = get_ref(refname, deref)
        if ref.value:
            yield refname, ref


@contextmanager
def get_index():
    index: dict[str, str] = {}
    if os.path.isfile(f"{GIT_DIR}/index"):
        with open(f"{GIT_DIR}/index") as f:
            index = json.load(f)

    yield index

    with open(f"{GIT_DIR}/index", "w") as f:
        json.dump(index, f)


ObjectType = Literal["blob", "tree", "commit"]


def hash_object(data: bytes, type_: ObjectType = "blob") -> str:
    obj = type_.encode() + b"\x00" + data
    oid = hashlib.sha1(obj).hexdigest()
    with open(f"{GIT_DIR}/objects/{oid}", "wb") as out:
        out.write(obj)
    return oid


def get_object(oid: str, expected: Optional[ObjectType] = "blob") -> bytes:
    with open(f"{GIT_DIR}/objects/{oid}", "rb") as f:
        obj = f.read()

    type_, _, content = obj.partition(b"\x00")
    type_ = type_.decode()

    if expected is not None:
        assert type_ == expected, f"Expected {expected}, got {type_}"
    return content


def object_exists(oid: str) -> bool:
    return os.path.isfile(f"{GIT_DIR}/objects/{oid}")


def fetch_object_if_missing(oid: str, remote_git_dir: str):
    if object_exists(oid):
        return

    remote_git_dir += "/.ugit"
    shutil.copy(f"{remote_git_dir}/objects/{oid}", f"{GIT_DIR}/objects/{oid}")


def push_object(oid: str, remote_git_dir: str):
    remote_git_dir += "/.ugit"
    shutil.copy(f"{GIT_DIR}/objects/{oid}", f"{remote_git_dir}/objects/{oid}")
