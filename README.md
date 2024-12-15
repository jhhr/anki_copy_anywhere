This is an work-in-progress Anki addon for performing complex batch field editing like what [Advanced Copy Fields](https://ankiweb.net/shared/info/1898445115), [Batch Editing](https://ankiweb.net/shared/info/291119185) and the default Anki's regex search and replace can do, but more and all at once.

Acknowledgments
- tatsumoto-ren at [Ajatt-tools](https://github.com/Ajatt-Tools) for `kana_conv.py`
- piazzatron for their [Smart Notes](https://ankiweb.net/shared/info/1531888719) which is where I got started with [text interpolation code](https://github.com/piazzatron/anki-smart-notes/blob/main/src/prompts.py#L138)
- [ijgnd](https://github.com/ijgnd) for their [Additional Card Fields](https://ankiweb.net/shared/info/744725736) whose card data gathering code was implemented in this.

# Roadmap ideas

## Big features
- Rework process chains into being interpolated also. Something like `<<<REGEX:My_regex==replacement1==replacement2>{{Some field}} {{Another field}}>><<<SOME_OTHER_PROCESS:My_Process=={{A field as arg}}>{{More fields}} Any text <<<REGEX:My_other_regex>{{Yet more fields}}>>>>` So nesting processes would be allowed. You'd define the processes like currently but also be able to provide arguments to them as interpolated values
- Field content as python code. This would first be interpolated like normal, then executed. The main idea is being able to call AI APIs to process stuff but any other APIs too. But also perform more complex processing that you can't do with just regex pattern replacement

## Toward actually copying anywhere
- Copy a note's anything into tags
- Copy a note's anything into custom data
- Copy a note's anything into new notes: create notes of existing note types and fill them
- Copy a note type's anything into new notetypes
- Copy into new note fields: copy content becomes the names of fields created on a notetype
- Copy note field names into anything
- Copy into card templates: modify existing and create new templates
- Copy from card templates into anything
