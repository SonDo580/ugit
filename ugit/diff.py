from typing import Iterator, Optional, Literal
from typing_extensions import Unpack
from collections import defaultdict
from tempfile import NamedTemporaryFile
import subprocess

from . import data


def compare_trees(
    *trees: dict[str, str]
) -> Iterator[tuple[str, Unpack[tuple[Optional[str], ...]]]]:
    entries: defaultdict[str, list[Optional[str]]] = defaultdict(
        lambda: [None] * len(trees)
    )
    for i, tree in enumerate(trees):
        for path, oid in tree.items():
            entries[path][i] = oid

    for path, oids in entries.items():
        yield path, *oids


ActionType = Literal["new file", "deleted", "modified"]


def iter_changed_files(
    t_from: dict[str, str], t_to: dict[str, str]
) -> Iterator[tuple[str, ActionType]]:
    for path, o_from, o_to in compare_trees(t_from, t_to):
        if o_from != o_to:
            action: ActionType = (
                "new file" if not o_from else ("deleted" if not o_to else "modified")
            )
            yield path, action


def diff_trees(t_from: dict[str, str], t_to: dict[str, str]) -> bytes:
    output = b""
    for path, o_from, o_to in compare_trees(t_from, t_to):
        if o_from != o_to:
            output += diff_blobs(o_from, o_to, path)
    return output


def diff_blobs(o_from: Optional[str], o_to: Optional[str], path: str = "blob") -> bytes:
    with NamedTemporaryFile() as f_from, NamedTemporaryFile() as f_to:
        for oid, f in [(o_from, f_from), (o_to, f_to)]:
            if oid:
                f.write(data.get_object(oid, "blob"))
                f.flush()

        with subprocess.Popen(
            [
                "diff",
                "--unified",
                "--show-c-function",
                "--label",
                f"a/{path}",
                f_from.name,
                "--label",
                f"b/{path}",
                f_to.name,
            ],
            stdout=subprocess.PIPE,
        ) as proc:
            output, _ = proc.communicate()

        return output


def merge_trees(
    t_base: dict[str, str], t_HEAD: dict[str, str], t_other: dict[str, str]
) -> dict[str, str]:
    tree: dict[str, str] = {}
    for path, o_base, o_HEAD, o_other in compare_trees(t_base, t_HEAD, t_other):
        tree[path] = data.hash_object(merge_blobs(o_base, o_HEAD, o_other))
    return tree


def merge_blobs(
    o_base: Optional[str], o_HEAD: Optional[str], o_other: Optional[str]
) -> str:
    with NamedTemporaryFile() as f_base, NamedTemporaryFile() as f_HEAD, NamedTemporaryFile() as f_other:
        for oid, f in [(o_base, f_base), (o_HEAD, f_HEAD), (o_other, f_other)]:
            if oid:
                f.write(data.get_object(oid))
                f.flush()

        with subprocess.Popen(
            [
                "diff3",
                "-m",
                "-L",
                "HEAD",
                f_HEAD.name,
                "-L",
                "BASE",
                f_base.name,
                "-L",
                "MERGE_HEAD",
                f_other.name,
            ],
            stdout=subprocess.PIPE,
        ) as proc:
            output, _ = proc.communicate()
            assert proc.returncode in (0, 1)

        return output
