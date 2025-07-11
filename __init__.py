from .hooks.browser_hooks import init_browser_hooks
from .hooks.note_hooks import init_note_hooks
from .hooks.sync_hook import init_sync_hook
from .configuration import migrate_config

migrate_config()
init_browser_hooks()
init_sync_hook()
init_note_hooks()
