import os
import json
from typing import TypedDict

# import all_kanji_data from the json file in ./all_kanji_data.json


class KanjiData(TypedDict):
    onyomi: str
    kunyomi: str


current_dir = os.path.dirname(os.path.abspath(__file__))
json_file_path = os.path.join(current_dir, "all_kanji_data.json")

all_kanji_data: dict[str, KanjiData] = {}
with open(json_file_path, "r", encoding="utf-8") as f:
    all_kanji_data = json.load(f)
