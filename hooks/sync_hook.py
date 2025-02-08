from typing import List

from anki.utils import ids2str
from aqt import mw
from aqt.gui_hooks import sync_will_start, sync_did_finish
from aqt.utils import tooltip

from ..configuration import Config
from ..logic.copy_fields import copy_fields


def create_comparelog(local_rids: List[int], texts: List[str]) -> None:
    assert mw.col.db is not None
    texts.clear()
    local_rids.clear()
    local_rids.extend([id for id in mw.col.db.list("SELECT id FROM revlog")])


def review_cid_remote(local_rids: List[int]):
    assert mw.col.db is not None
    local_rid_string = ids2str(local_rids)
    remote_reviewed_cids = [cid for cid in mw.col.db.list(f"""SELECT DISTINCT cid
            FROM revlog
            WHERE id NOT IN {local_rid_string}
            AND type < 4
            """)]
    return remote_reviewed_cids


class SyncResult:
    def __init__(self):
        self.local_changes_text = ""
        self.remote_changes_text = ""
        self.definitions_count = 0

    def has_changes(self):
        return bool(self.local_changes_text or self.remote_changes_text)

    def incr_count(self, count: int):
        self.definitions_count += count

    def clear(self):
        self.local_changes_text = ""
        self.remote_changes_text = ""
        self.definitions_count = 0


def local_changes_copy_definitions(sync_result: SyncResult) -> None:

    config = Config()
    config.load()

    copy_on_sync_definitions = [
        definition
        for definition in config.copy_definitions
        if definition.get("copy_on_sync", False)
    ]
    if not copy_on_sync_definitions:
        return

    def update_local_sync_result(text: str, count: int):
        if text:
            sync_result.local_changes_text = text
        sync_result.incr_count(count)

    copy_fields(
        copy_definitions=copy_on_sync_definitions,
        update_sync_result=update_local_sync_result,
        progress_title="Copying fields for local changes",
    )


def show_result_tooltip(sync_result: SyncResult) -> None:
    if sync_result.has_changes():
        result_text = ""
        if sync_result.local_changes_text:
            result_text += f"<b>Local changes:</b><br>{sync_result.local_changes_text}"
        if sync_result.remote_changes_text:
            if sync_result.local_changes_text:
                result_text += "<br><br>"
            result_text += f"<b>Remote changes:</b><br>{sync_result.remote_changes_text}"
        tooltip(
            result_text,
            parent=mw,
            period=5000 + sync_result.definitions_count * 1000,
            # Position the tooltip higher so other tooltips don't get covered
            # 100 is the default offset, see aqt.utils.tooltip
            y_offset=200,
        )
    # Clear the result for the next sync
    sync_result.clear()


def remote_changes_copy_definitions(sync_result: SyncResult) -> None:

    config = Config()
    config.load()

    copy_on_sync_definitions = [
        definition
        for definition in config.copy_definitions
        if definition.get("copy_on_sync", False)
    ]
    if not copy_on_sync_definitions:
        show_result_tooltip(sync_result)
        return

    def update_remote_sync_result(text: str, count: int):
        if text:
            sync_result.remote_changes_text = text
        sync_result.incr_count(count)

    def show_tooltip_on_done():
        # Showing the tooltip right after the op finishes results in it being closed right
        # away, likely becayse the progress dialog is still open. So we use a single shot timer
        # to delay the tooltip.
        mw.progress.single_shot(100, lambda: show_result_tooltip(sync_result))

    copy_fields(
        copy_definitions=copy_on_sync_definitions,
        update_sync_result=update_remote_sync_result,
        on_done=show_tooltip_on_done,
        progress_title="Copying fields for remote changes",
    )


def init_sync_hook():
    sync_result = SyncResult()

    # Run copy fields for local changes that will be synced
    sync_will_start.append(lambda: local_changes_copy_definitions(sync_result))
    # Then again after getting changes from remote, another sync will be needed after this
    sync_did_finish.append(lambda: remote_changes_copy_definitions(sync_result))
