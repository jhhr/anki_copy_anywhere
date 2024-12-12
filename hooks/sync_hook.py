from typing import List

from anki.utils import ids2str
from aqt import mw
from aqt.gui_hooks import sync_will_start, sync_did_finish

from ..configuration import Config
from ..logic.copy_fields import copy_fields


def create_comparelog(local_rids: List[int], texts: List[str]) -> None:
    texts.clear()
    local_rids.clear()
    local_rids.extend([id for id in mw.col.db.list("SELECT id FROM revlog")])


def review_cid_remote(local_rids: List[int]):
    local_rid_string = ids2str(local_rids)
    remote_reviewed_cids = [
        cid
        for cid in mw.col.db.list(
            f"""SELECT DISTINCT cid
            FROM revlog
            WHERE id NOT IN {local_rid_string}
            AND type < 4
            """
        )  # type: 0=Learning, 1=Review, 2=relearn, 3=filtered, 4=Manual
    ]
    return remote_reviewed_cids


def auto_copy_definitions(texts: List[str]):

    config = Config()
    config.load()

    copy_on_sync_definitions = [
        definition for definition in config.copy_definitions if definition.get("copy_on_sync", False)
    ]
    if not copy_on_sync_definitions:
        return

    fut = copy_fields(
        copy_definitions=copy_on_sync_definitions,
        is_sync=True,
    )

    if fut:
        # wait for copy to finish
        (copy_result_msg, _) = fut.result()
        texts.append(copy_result_msg)


def init_sync_hook():
    texts = []

    # sync_will_start.append(lambda: create_comparelog(local_rids, texts))
    # Run copy fields for local changes that will be synced
    sync_will_start.append(lambda: auto_copy_definitions(texts))
    # Then again after getting changes from remote, another sync will be needed after this
    sync_did_finish.append(lambda: auto_copy_definitions(texts))
