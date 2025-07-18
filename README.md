# CopyAnywhere

This is an Anki addon for performing complex batch field editing like what [Advanced Copy Fields](https://ankiweb.net/shared/info/1898445115), [Batch Editing](https://ankiweb.net/shared/info/291119185) and the default Anki's regex search and replace can do, but more and all at once.

Acknowledgments
- tatsumoto-ren at [Ajatt-tools](https://github.com/Ajatt-Tools) for `kana_conv.py`
- piazzatron for their [Smart Notes](https://ankiweb.net/shared/info/1531888719) which is where I got started with [text interpolation code](https://github.com/piazzatron/anki-smart-notes/blob/main/src/prompts.py#L138)
- [ijgnd](https://github.com/ijgnd) for their [Additional Card Fields](https://ankiweb.net/shared/info/744725736) whose card data gathering code was implemented in this.

## Usage

### Open main dialog

In the card browser main menu Edit --> Copy Anywhere or hotkey Alt+Shift+C

<img width="392" height="339" alt="image" src="https://github.com/user-attachments/assets/426620da-fd6e-4049-b98f-7f460eed491d" />

### Making and running copy definitions

Creating, editing and removing definitions is done through the dialog.

<img width="1151" height="302" alt="image" src="https://github.com/user-attachments/assets/a6579f91-3f03-47f2-8573-307b766c8f1f" />

 The dialog additionally allows running copy definitions for the selected notes in the browser, or the entire search result. This is useful for running multiple definitions at once for a selection of notes. Otherwise, to run a single definition for a selection of notes in the browser, you can use the right-click menu.

#### Run multiple copy definitions in dialog
<img width="1158" height="1022" alt="image" src="https://github.com/user-attachments/assets/839b86fb-acae-474d-9d84-3f32cc688ff2" />

#### Run a single copy definitions through browser right-click menu
<img width="999" height="934" alt="image" src="https://github.com/user-attachments/assets/f37f2d2e-eabe-4dbb-9d8c-e24ffaf3d074" />

#### Select main mode

- **Within note**: Edit one note's fields using only its own fields and other data. Can also be used to save data from a note into a file.
- **Across notes**: Edit notes using fields and data from other notes. There's two ways to do this:
  - **Source to destinations**: Search for other notes with data from a note, then edit *that one note* with data from the found notes
  - **Destination to sources**: Search for other notes with data from a note, then edit *each of the found notes* with data from the one note

<img width="1536" height="914" alt="image" src="https://github.com/user-attachments/assets/a222910e-57d3-4602-a052-0bd0a0962526" />

#### Basic settings

- **Name**: Name is shown in the progress dialog, report tooltip and undo menu.
- **Trigger note type**: What note type you'll be editing. For _Across notes_ mode, the notes you search are not restricted and can be any note types, even a mix of different note types, but the initial trigger note must be specified.
  - Selecting multiple note types restricts the editable fields to only those fields that _every_ note type shares.
  - In _Across notes_ mode, the trigger note is either the destination or the source, depending on the direction.
- **Trigger deck limit**: Optionally restrict whether the definition edits a note by deck by whitelisting specific decks.
- **Run on sync for reviewed cards** (see _Setting up custom scheduling_): cards reviewed on other devices are gathered during sync and the copy definition is run on them (depending on trigger note and trigger deck limit). This allows copy definitions to be run on notes that you review on mobile but would like to run on review there.
  - If **On review** is off and **On sync** is on, then operations will be run on desktop as well for cards reviewed. This option is good when the operation takes annoyingly long when running on review.
  - If  **On review** and **On sync** are both on, then on desktop the operation is run on review only. 

- **Run on review** (see _Setting up custom scheduling_): After reviewing a card, this copy definition is run on its note, if the note matches the trigger note type and the trigger deck limit.
- **Run when adding new note**: When adding a note, runs copy definition, if the note matches the trigger note type and the trigger deck limit.  Applies to the adding notes using the Add note dialog, through AnkiConnect or other addons calling `col.add_note()`. Does not apply adding notes from the import dialog or notes added on mobile and then synced to desktop.

#### Variables

Optional. The variables can be used in _Search Query_, _Field to Field_ and _Field to File_ tabs. Main usage is in _Across notes_ mode and you need to define a complex note search using the trigger note. Usage is similar to _Field to Field_ except there's no target field, you save the value into the variable name.

#### Search Query (Across notes mode only)

Required. Define a search query just like in the card browser, except you can include fields and data from the trigger note with ``{{}}`` like you do in the card template.

- **Sort queried notes by field**: Optionally sort the found notes by this field alphabetically. The options are from all note types in your collection - there's no detection of what note types your query might return, you'll need to ensure that the field works for your query.
  - Example use case: you have notes with a number field like _Frequency_ and you want to pick the note with the smallest/largest Frequency --> Set Sort by to "Frequency", Select multiple cards? to 1 and How to select card to _None_
- **How to select a card to copy from**: Applies when not selecting all notes.
  - None: no selection, whatever order the notes are found, the first ones get selected.
  - Random (default): randomly select notes until the select limit is reached
  - Least reps: The only choice that selects by card and not note. Only works properly, if you filter the search to only include a single card type or your note type or only has one card type
- **Separator for multiple values**: Only needed in _Destination to sources_ mode and you're selecting more than one note from the search. In _Destination to sources_ referencing fields with `{{Field}}` actually contains _all_ the field values from each note selected from the search, concatenated together with the separator in between.

<img width="1532" height="899" alt="image" src="https://github.com/user-attachments/assets/7c73b4d4-d2b8-41e8-abc7-630f3a961a8d" />

#### Field to Field

- **Destination field**: In _Within note_ or _Destination to sources_ mode, this a trigger note field and only those are shown as options. In _Source to destinations_ mode, this is a field in any of the notes gotten from the _Search Query_ and all fields from all note types are shown as options, but you'll need to manage your search query so that it only returns note types for which you pick the field here.
- **Content**: Define content to replace the field with. If you just want to edit the field "Field" itself with some regex then input `{{Field}}` and add regex processing.
- **Only copy into field, it it's empty**: Limits to only editing empty fields.
- **Copy on unfocusing the field when editing an existing note**: Runs copy definition _for just this destination field_ when you unfocus the selected field in the note editor. The selected field can be the field that will be edited or some other field, ie. the field that is used as a source for editing the destination field. Only applies to editing an existing note.
- **Copy on unfocusing the field when adding a new note**: Otherwise the same as above but only applies when editing a note in the Add note dialog
- **Copy on unfocus trigger field**: If empty, the trigger field is the destination field. Set to another field to make the unfocus auto-copying get triggered by that field instead. Does nothing if you haven't checked either of the _Copy on unfocusing ..._ options

<img width="1537" height="907" alt="image" src="https://github.com/user-attachments/assets/8d7f58e5-3bfb-4a46-8faa-eb25387acceb" />

##### Extra processing (Regex)

The Regex replace is what you want, the other options are some custom processors the author has made for themself and will get removed from the main addon eventually.

You can add any amount of regex steps that each get applied sequentially, so quite complex edits can be done, if you're willing to make complex regex. Note, this uses _Python regex_ and not the rust regex that Anki's own search and replace uses. This means advanced (and potentially low performance) expressions like lookahead are available. Both the regex expression and the replacement value can also use the same `{{Field}}` syntax to input values from the note fields, including Variables!

<img width="1479" height="707" alt="image" src="https://github.com/user-attachments/assets/08b75fc8-4b06-4df7-9507-82cf77da58c3" />

#### Field to File

Works otherwise the same as _Field to File_ but instead of specifying a destination note field, you save into a file in your collection media folder. The filename once can also use `{{Field}}` syntax.

<img width="1530" height="852" alt="image" src="https://github.com/user-attachments/assets/fbe9a9f5-048c-4380-817d-52f6cab4f863" />


## Setting up custom scheduling

If you enable copy definitions that should run on review or you use Anki on mobile, you need to add the below code to the custom scheduler in Anki. To enable fields to update after reviewing on mobile, enable Copy on sync.
- Open any deck's settings, at the very bottom in the **Advanced** section, open **Custom scheduling**.

```
customData.again.fc = 0;
customData.hard.fc = 0;
customData.good.fc = 0;
customData.easy.fc = 0;
```
What it does is sets a flag to the card that the addon checks for when looking for notes whose fields should be updated.


## Roadmap ideas

### Big features
- Process field content with python code. The interpolated value is turned into a variable that is passed to the code in `locals`. You could have multiple variables, not just one. Would make sense to declare all variables first, then run evaluate each code block
  - **Breaking change**: This would replace the current process chain system
  - Provide code templates for common tasks like regex replace
  - Provide the current very specific processors as functions to use in the code
  - The main idea is being able to call AI APIs to process stuff but any other APIs too. But also perform more complex processing that you can't do with just regex pattern replacement
- Chaining copy definition results into another definition.
  - For cases where you first need to query one set of notes, process some values from those, then use those values to further query other notes.
  - Instead saving results into note fields (or in addition to doin so - drive-by note editing!), they are saved into variables that are passed to the next step and used for querying.
- **Possible breaking change**: Instead having to choose destinations-to-sources or vice versa, you define a save step where you select notes to edit: the trigger note or the target notes queried. Then you could actually edit both in one definition. Chained definitions would create multiple lists of target notes. Any step could save into any of the so far queried target cards or the initial trigger note.


### Toward actually copying anywhere
- Copy a note's anything into tags
- Copy a note's anything into custom data
- Copy a note's anything into new notes: create notes of existing note types and fill them
- Copy a note type's anything into new notetypes
- Copy into new note fields: copy content becomes the names of fields created on a notetype
- Copy note field names into anything
- Copy into card templates: modify existing and create new templates
- Copy from card templates into anything
