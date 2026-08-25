from typing import Iterator, Optional
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


def diff_trees(t_from: dict[str, str], t_to: dict[str, str]) -> bytes:
    output = b""
    for path, o_from, o_to in compare_trees(t_from, t_to):
        if o_from != o_to:
            output += diff_blobs(o_from, o_to)
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
