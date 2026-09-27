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
    for oid in base.iter_objects_in_commits(set(refs.values())):
        data.fetch_object_if_missing(oid, remote_path)

    # Update local ref to match remote
    for remote_name, value in refs.items():
        refname = os.path.relpath(remote_name, REMOTE_REFS_BASE)
        data.update_ref(
            f"{LOCAL_REFS_BASE}/{refname}", data.RefValue(symbolic=False, value=value)
        )


def push(remote_path: str, refname: str):
    # Get refs data
    remote_refs = _get_remote_refs(remote_path)
    remote_ref = remote_refs.get(refname)
    local_ref = data.get_ref(refname).value
    assert local_ref

    # Don't allow force-push. Allow push if:
    # - the ref doesn't exist on remote (new branch).
    # - or the ref is an ancestor of the pushed ref
    #   (otherwise, must fetch and merge).
    assert not remote_ref or base.is_ancestor_of(local_ref, remote_ref)

    # Find objects that remote doesn't have
    known_remote_refs = filter(data.object_exists, remote_refs.values())
    remote_objects = set(base.iter_objects_in_commits(set(known_remote_refs)))
    local_objects = set(base.iter_objects_in_commits({local_ref}))
    objects_to_push = local_objects - remote_objects

    # Push missing objects
    for oid in objects_to_push:
        data.push_object(oid, remote_path)

    # Update remote ref to match local
    with data.change_git_dir(remote_path):
        data.update_ref(refname, data.RefValue(symbolic=False, value=local_ref))


def _get_remote_refs(remote_path: str, prefix: str = "") -> dict[str, Optional[str]]:
    with data.change_git_dir(remote_path):
        return {refname: ref.value for refname, ref in data.iter_refs(prefix)}
