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


def auto_copy_definitions(local_rids: List[int], texts: List[str]):
    if len(local_rids) == 0:
        return

    config = Config()
    config.load()

    remote_reviewed_cids = review_cid_remote(local_rids)

    for copy_definition in config.copy_definitions:
        copy_on_sync = copy_definition.get("copy_on_sync", False)
        if not copy_on_sync:
            continue

        fut = copy_fields(
            copy_definition=copy_definition,
            card_ids=set(remote_reviewed_cids),
            is_sync=True,
        )

        if fut:
            # wait for copy to finish
            (copy_result_msg, _) = fut.result()
            texts.append(copy_result_msg)


def init_sync_hook():
    local_rids = []
    texts = []

    sync_will_start.append(lambda: create_comparelog(local_rids, texts))
    sync_did_finish.append(lambda: auto_copy_definitions(local_rids, texts))
