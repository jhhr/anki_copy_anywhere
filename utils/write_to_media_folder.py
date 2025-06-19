from aqt import mw


from pathlib import Path


def write_to_media_folder(filename: str, text: str) -> None:
    """
    Write text to a file in the media folder
    """
    if not filename:
        raise ValueError("Filename must not be empty")
    # If filename doesn't start with _, add it
    if not filename.startswith("_"):
        filename = f"_{filename}"

    media_path = Path(mw.pm.profileFolder(), "collection.media")

    file_path = Path(media_path, filename)

    # Write the text to the file, overwriting, if it already exists
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(text)
