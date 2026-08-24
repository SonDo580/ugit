import os
from typing import Iterator

from . import data


def write_tree(directory: str = ".") -> str:
    entries: list[tuple[str, str, data.ObjectType]] = []

    with os.scandir(directory) as it:
        for entry in it:
            full = f"{directory}/{entry.name}"
            if is_ignored(full):
                continue

            type_: data.ObjectType
            if entry.is_file(follow_symlinks=False):
                type_ = "blob"
                with open(full, "rb") as f:
                    oid = data.hash_object(f.read(), type_)
            elif entry.is_dir(follow_symlinks=False):
                type_ = "tree"
                oid = write_tree(full)
            else:
                continue
            entries.append((entry.name, oid, type_))

        tree = "".join(
            f"{type_} {oid} {name}\n" for name, oid, type_ in sorted(entries)
        )
        return data.hash_object(tree.encode(), "tree")


def _iter_tree_entries(oid: str) -> Iterator[tuple[data.ObjectType, str, str]]:
    tree = data.get_object(oid, "tree")
    for entry in tree.decode().splitlines():
        type_, oid, name = entry.split(" ", 2)
        yield type_, oid, name


def get_tree(oid: str, base_path: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for type_, oid, name in _iter_tree_entries(oid):
        assert "/" not in name
        assert name not in ("..", ".")
        path = base_path + name
        if type_ == "blob":
            result[path] = oid
        elif type_ == "tree":
            result.update(get_tree(oid, f"{path}/"))
        else:
            assert False, f"Unknown entry type {type_}"
    return result


def _empty_current_directory():
    for root, dirnames, filenames in os.walk(".", topdown=False):
        for filename in filenames:
            path = os.path.relpath(f"{root}/{filename}")
            if is_ignored(path) or not os.path.isfile(path):
                continue
            os.remove(path)

        for dirname in dirnames:
            path = os.path.relpath(f"{root}/{dirname}")
            if is_ignored(path):
                continue
            try:
                os.rmdir(path)
            except:
                pass


def read_tree(tree_oid: str):
    _empty_current_directory()
    for path, oid in get_tree(tree_oid, base_path="./").items():
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(data.get_object(oid, expected="blob"))


def is_ignored(path: str) -> bool:
    return ".ugit" in path.split("/")
