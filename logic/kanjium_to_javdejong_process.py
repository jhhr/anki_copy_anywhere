import re
from typing import Callable

DEBUG = False


def kanjium_to_javdejong_process(
        text: str,
        delimiter: str = '・',
        show_error_message: Callable[[str], None] = None
):
    """
    Convert a pitch accent html string that is in Kanjium format to Javdejong format.
    :param text: Text with the pitch accent html string to convert. If not in Kanjium format, it will be returned as is.
    :param delimiter: The delimiter to use when joining the converted pitch accent descriptions. Default is '・'.
    :param show_error_message: A function to call to show an error message. Default is None.
    :return: The converted pitch accent html string in Javdejong format.
    """
    if not show_error_message:
        def show_error_message(message: str):
            print(message)

    is_kanjium_pitch = re.search(r'currentColor', text)
    if not is_kanjium_pitch:
        return text

    # Split the input string into pitch accent descriptions
    pitch_accent_descriptions = text.split('・')

    # Initialize a list to store the converted pitch accent descriptions
    javdejong_descriptions = []

    # Iterate through each pitch accent description
    for pitch_accent_description in pitch_accent_descriptions:
        if DEBUG:
            show_error_message(f'pitch_accent_description: {pitch_accent_description}')
        all_kana = []

        # Find all kana characters
        all_kana_matches = re.findall(r'[ぁ-んァ-ンゞ゛゜ー]', pitch_accent_description)
        if all_kana_matches:
            for (i, kana_match) in enumerate(all_kana_matches):
                all_kana.append({'kana': kana_match, 'index': i, 'overline': False, 'down': False})

        if DEBUG:
            show_error_message(f'all_kana: {all_kana}')

        kana_iter = iter(all_kana)

        # Find characters that have an overline
        overline_kana_matches = re.findall(
            r'<span style="display:inline-block;position:relative;padding-right:0.1em;margin-right:0.1em;"><span style="display:inline;">([ぁ-んァ-ンゞ゛゜ー]*?)<\/span>(?!<span style="border-color:currentColor;display:block;user-select:none;pointer-events:none;position:absolute;top:0.1em;left:0;right:0;height:0;border-top-width:0.1em;border-top-style:solid;right:-0.1em;height:0.4em;border-right-width:0.1em;border-right-style:solid;"></span>)|<span style="display:inline;">([ぁ-んァ-ンゞ゛゜ー]*?)<\/span><span style="border-color:currentColor;display:block;user-select:none;pointer-events:none;position:absolute;top:0.1em;left:0;right:0;height:0;border-top-width:0.1em;border-top-style:solid;"><\/span>',
            pitch_accent_description)
        if overline_kana_matches:
            for overline_match in overline_kana_matches:
                if DEBUG:
                    show_error_message(f'overline_match: {overline_match}')

                # Get the first or second match group
                overline_kana = overline_match[0] or overline_match[1]

                kana_def = next(kana_iter)
                while kana_def['kana'] != overline_kana:
                    kana_def = next(kana_iter)

                kana_def['overline'] = True

        # Find characters that have an overline and downpitch notch
        downpitch_matches = re.findall(
            r'<span style="display:inline;">([ぁ-んァ-ンゞ゛゜ー]*?)<\/span><span style="border-color:currentColor;display:block;user-select:none;pointer-events:none;position:absolute;top:0.1em;left:0;right:0;height:0;border-top-width:0.1em;border-top-style:solid;right:-0.1em;height:0.4em;border-right-width:0.1em;border-right-style:solid;"><\/span>',
            pitch_accent_description)
        if downpitch_matches:
            for downpitch_kana in downpitch_matches:
                if DEBUG:
                    show_error_message(f'downpitch_kana: {downpitch_kana}')

                kana_def = next(kana_iter)
                while kana_def['kana'] != downpitch_kana:
                    kana_def = next(kana_iter)

                kana_def['overline'] = True
                kana_def['down'] = True

        result = ''
        started_overline = False
        ended_overline = False
        for kana_def in all_kana:
            if kana_def['overline'] and not started_overline:
                result += '<span style="text-decoration:overline;">'
                started_overline = True
            result += kana_def['kana']
            if kana_def['down']:
                result += '</span>&#42780;'
                ended_overline = True
            elif started_overline and not kana_def['overline']:
                result += '</span>'
                ended_overline = True

        if not ended_overline:
            result += '</span>'

        if DEBUG:
            show_error_message(f'result: {result}')

        javdejong_descriptions.append(result)

    # Join the converted pitch accent descriptions with the separator ・
    javdejong_result = delimiter.join(javdejong_descriptions)

    return javdejong_result
