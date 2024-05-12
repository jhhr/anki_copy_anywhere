from aqt import mw

tag = mw.addonManager.addonFromModule(__name__)

DAYS_TO_CACHE_FIELDS_MENU = "days_to_cache_fields_menu"
DAYS_TO_CACHE_FIELDS_AUTO = "days_to_cache_fields_auto"
CACHE_NEW_CARDS_COUNT = "cache_new_cards_count"


def load_config():
    return mw.addonManager.getConfig(tag)


def save_config(data):
    mw.addonManager.writeConfig(tag, data)


def run_on_configuration_change(function):
    mw.addonManager.setConfigUpdatedAction(__name__, lambda *_: function())


class Config:
    def load(self):
        self.data = load_config()

    def save(self):
        save_config(self.data)

    @property
    def days_to_cache_fields_menu(self):
        return self.data[DAYS_TO_CACHE_FIELDS_MENU]

    @days_to_cache_fields_menu.setter
    def days_to_cache_fields_menu(self, value):
        self.data[DAYS_TO_CACHE_FIELDS_MENU] = value
        self.save()

    @property
    def days_to_cache_fields_auto(self):
        return self.data[DAYS_TO_CACHE_FIELDS_AUTO]

    @days_to_cache_fields_auto.setter
    def days_to_cache_fields_auto(self, value):
        self.data[DAYS_TO_CACHE_FIELDS_AUTO] = value
        self.save()

    @property
    def cache_new_cards_count(self):
        return self.data[CACHE_NEW_CARDS_COUNT]

    @cache_new_cards_count.setter
    def cache_new_cards_count(self, value):
        self.data[CACHE_NEW_CARDS_COUNT] = value
        self.save()
