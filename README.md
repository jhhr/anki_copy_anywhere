This is an Anki addon that creates a new template field syntax for fetching the field value from another note.

Some code copied from Ajatt-tools like `kana_conv.py`.

# Usage
- A new filter is added that can be used in all card templates with the structure `{{fetch[..args]:Field}}` where `Field` is the note field whose content is passed to the filter to process. The `...args` are as follows:

## Args basics
- `arg_name='single_value';` or `arg_name=['value_1', 'value_2', ...];`
  1. The `arg_name` must be spelled exactly, uncapitalized.
  2. The = character can have spaces before or after, so `arg_name  =  'single_value';` is valid
  3. The value must be wrapped with '', not "". For multi value args, the values must be wrapped with [] and each individual value with '' and separated by ,
  4. The arg must end with ; There can be spaces before or after and a new line can be added, so this is valid `arg_name = 'single_value' ;`

## Required args
- `from_did='deck_id'` or `from_deck_name='from_deck_name'`: Defines the deck from which a note will be fetched. Can be any deck in your collection.
- `from_note_type_id='note_type_id'` or `from_note_type_name='from_note_type_name'`: Defines the note type from which to fetch a field. Must be a note type used in the deck you specify above.
- `select_card_by_fld_name='note_fld_name_to_get_card_by'`: Defines how to select a card or cards from the deck. Must be the name of a field in the note type you specify above. All notes in the `from_deck` are returned where the `Field` content is contained in content of the field `note_fld_name_to_get_card_by`.
- `pick_card_by='random'/'random_stable'/'least_reps[ord]'`: Defines how to select a single card from among those that belong to the notes returned by the fetch above.
  - **Note**: If there are multiple card templates per note, the two first args will select among all of them.
  - `random`: Pick by random.
    - **Note**: This means the each time you render a card with the filter you can get a different result! If you use the same filter three times, you will (possibly) get three different results.
  - `random_stable`: Pick by random except that the card picked for the same combination of `from_deck_name`/`deck_id`, `from_note_type_id`/`from_note_type_name` and `select_card_by_fld_name` will return the same card. This allows you to return multiple different fields from the same randomly picked card.
  - `least_reps` or `least_reps[ord]`: Pick the card with the least reps. `[ord]` is an optional addition that is the ordinal number of the card template to select from. If `[ord]` is defined, selection will be done only among the specified card type and the rest are ignored.
- `fld_name_to_get_from_card='note_field_name_to_get'`: Once a single card is picked, defines what field to return from the note. Can be the same field used to fetch the notes or a different one.

### Required args in a nutshell
Essentially, the first three args do the same thing as doing a query in the card browser like `"deck:<from_deck_name>" "note:<from_note_type_name>" <note_fld_name_to_get_card_by>:*<Field_content>*`. And then `pick_card_by` defines how to select a single one from those.

## Optional args
- `cur_deck_white_list=['deck_name1', 'deck_name2', ...']`: If you want to use the filter in a card template but only for notes in some decks, define all the decks the filter should be run in. For subdecks the whole deck name is not needed, only the subdeck name. When a card not in those decks is rendered the filter will return nothing.
- `multi_value_count='number_of_cards_to_get'`: Instead of picking a single card, pick this many. `pick_card_by` is used to select each card. The final return value of the filter will then be the field contents gotten from all the picked cards concatenated together. If the number exceeds the cards found, all cards are picked which makes `pick_card_by` irrelevant. The number should be wrapped in '', so `multi_value_count='3'` NOT `multi_value_count=3`.
- `multi_value_separator='separator_for_multiple_results'`: What separator to use when concatenating the contents of multiple cards' fields. Defaults to ,


# Example usage
In a kanji writing card deck, for kanji cards but not hiragana or katakana cards, fetch an example sentence and sentence audio along with five vocabulary examples using that kanji from a different deck.

First getting the example sentence and sentence audio from a single vocab card. Here `random_stable` is used so that the same card is picked for the sentence and audio.
```
<!-- get sentence -->
  {{fetch[
    from_deck_name = 'JP vocab';
    from_note_type_name='Japanese vocab note';
    cur_deck_white_list=['1-kanji'];
  
    select_card_by_fld_name='kanjified-vocab';
    fld_name_to_get_from_card ='Reading';
    pick_card_by= 'random_stable';
    ]:Kanji}}

<!-- get audio for sentence -->
{{fetch[
    from_deck_name = 'JP vocab';
    from_note_type_name='Japanese vocab note';
    select_card_by_fld_name='kanjified-vocab';
    cur_deck_white_list=['1-kanji'];
    fld_name_to_get_from_card ='Reading-audio';
    pick_card_by= 'random_stable';
    ]:Kanji}}

<!-- get five vocab examples -->
    {{fetch[
      from_deck_name='JP vocab';
      from_note_type_name='Japanese vocab note';
      select_card_by_fld_name='kanjified-vocab';
      cur_deck_white_list=['1- kaji'];
      fld_name_to_get_from_card='vocab-furigana';
      pick_card_by='random';
      multi_value_count='5';
      multi_value_separator='、'
    ]:Kanji}}
```
