This is an work-in-progress Anki addon for performing complex batch field editing like what [Advanced Copy Fields](https://ankiweb.net/shared/info/1898445115), [Batch Editing](https://ankiweb.net/shared/info/291119185) and the default Anki's regex search and replace can do, but more and all at once.

Acknowledgments
- tatsumoto-ren at [Ajatt-tools](https://github.com/Ajatt-Tools) for `kana_conv.py`
- piazzatron for their [Smart Notes](https://ankiweb.net/shared/info/1531888719) which is where I got started with [text interpolation code](https://github.com/piazzatron/anki-smart-notes/blob/main/src/prompts.py#L138)
- [ijgnd](https://github.com/ijgnd) for their [Additional Card Fields](https://ankiweb.net/shared/info/744725736) whose card data gathering code was implemented in this.

# Roadmap ideas

## Big features
- Process field content with python code. The interpolated value is turned into a variable that is passed to the code in `locals`. You could have multiple variables, not just one. Would make sense to declare all variables first, then run evaluate each code block
  - **Breaking change**: This would replace the current process chain system
  - Provide code templates for common tasks like regex replace
  - Provide the current very specific procesors as functions to use in the code
  - The main idea is being able to call AI APIs to process stuff but any other APIs too. But also perform more complex processing that you can't do with just regex pattern replacement
  - Saving results into a file in collection.media and allowing reading files while copying.
- Chaining copy definition results into another definition.
  - For cases where you first need to query one set of notes, process some values from those, then use those values to further query other notes.
  - Instead saving results into note fields (or in addition to doin so - drive-by note editing!), they are saved into variables that are passed to the next step and used for querying.
- **Possible breaking change**: Instead having to choose destinations-to-sources or vice versa, you define a save step where you select notes to edit: the trigger note or the target notes queried. Then you could actually edit both in one definition. Chained definitions would create multiple lists of target notes. Any step could save into any of the so far queried target cards or the initial trigger note.


## Toward actually copying anywhere
- Copy a note's anything into tags
- Copy a note's anything into custom data
- Copy a note's anything into new notes: create notes of existing note types and fill them
- Copy a note type's anything into new notetypes
- Copy into new note fields: copy content becomes the names of fields created on a notetype
- Copy note field names into anything
- Copy into card templates: modify existing and create new templates
- Copy from card templates into anything
