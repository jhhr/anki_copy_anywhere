from anki import hooks
from aqt import gui_hooks
from aqt.browser import Browser
from aqt.gui_hooks import deck_browser_will_show_options_menu
from aqt.qt import QAction, qconnect, QMenu

from .cache_fetches import cache_fetches
from .configuration import Config
from .on_field_filter import on_field_filter
from .reset_custom_data import reset_custom_data

hooks.field_filter.append(on_field_filter)

config = Config()
config.load()


def build_action(fun, text, shortcut=None):
    """fun -- without argument
    text -- the text in the menu
    """
    action = QAction(text)
    action.triggered.connect(lambda b, did=None: fun(did))
    if shortcut:
        action.setShortcut(shortcut)
    return action


def add_action_to_gear(fun, get_text):
    """fun -- takes an argument, the did
    text -- what's written in the gear."""

    def aux(m, did):
        config.load()
        # Use function to get so that it occurs after config is loaded
        # in case the text uses a config value
        # This the text gets updated when the config changes
        a = m.addAction(get_text())
        a.triggered.connect(lambda b, did=did: fun(did))

    deck_browser_will_show_options_menu.append(aux)


def add_separator_to_gear():
    """fun -- takes an argument, the did
    text -- what's written in the gear."""

    def aux(m, did):
        a = m.addSeparator()

    deck_browser_will_show_options_menu.append(aux)


def cache_fetches_menu(did):
    cache_fetches(did=did, result_text="", from_menu=True)


add_separator_to_gear()
add_action_to_gear(
    cache_fetches_menu,
    lambda: f"Cache fetch fields for the next {config.days_to_cache_fields_menu} days"
)


def on_browser_will_show_context_menu(browser: Browser, menu: QMenu):
    reset_fc_action = QAction("Reset 'fc'", browser)
    qconnect(
        reset_fc_action.triggered,
        lambda: reset_custom_data(card_ids=browser.selectedNotesAsCards(), parent=browser, reset_field='fc'),
    )
    reset_all_action = QAction("Reset all fields", browser)
    qconnect(
        reset_all_action.triggered,
        lambda: reset_custom_data(card_ids=browser.selectedNotesAsCards(), parent=browser),
    )
    custom_data_menu = menu.addMenu("CustomData")
    # Add the actions to the browser's card context menu
    custom_data_menu.addAction(reset_fc_action)
    custom_data_menu.addAction(reset_all_action)

    cache_fetches_action = QAction("Cache fetch fields", browser)
    qconnect(
        cache_fetches_action.triggered,
        lambda: cache_fetches(card_ids=browser.selectedNotesAsCards(), parent=browser, from_menu=True),
    )
    menu.addAction(cache_fetches_action)


gui_hooks.browser_will_show_context_menu.append(on_browser_will_show_context_menu)
