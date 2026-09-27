"""
Contains remote synchronization code.
Only handle directories on the same filesystem.
"""

import os
from typing import Optional

from . import base
from . import data

REMOTE_REFS_BASE = "refs/heads/"  # location of refs on remote
LOCAL_REFS_BASE = "refs/remote/"  # location to store remote refs on local


def fetch(remote_path: str):
    # Get refs from remote
    refs = _get_remote_refs(remote_path, REMOTE_REFS_BASE)

    # Fetch missing objects
    for oid in base.iter_objects_in_commit(refs.values()):
        data.fetch_object_if_missing(oid, remote_path)

    # Store fetched refs on local
    for remote_name, value in refs.items():
        refname = os.path.relpath(remote_name, REMOTE_REFS_BASE)
        data.update_ref(
            f"{LOCAL_REFS_BASE}/{refname}", data.RefValue(symbolic=False, value=value)
        )


def _get_remote_refs(remote_path: str, prefix: str = "") -> dict[str, Optional[str]]:
    with data.change_git_dir(remote_path):
        return {refname: ref.value for refname, ref in data.iter_refs(prefix)}
