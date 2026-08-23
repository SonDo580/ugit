import os

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


def is_ignored(path: str) -> bool:
    return ".ugit" in path.split("/")
