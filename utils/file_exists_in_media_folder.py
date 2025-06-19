from aqt import mw


from pathlib import Path


def file_exists_in_media_folder(filename: str) -> bool:
    """
    Check if a file exists in the media folder
    """
    if not filename:
        raise ValueError("Filename must not be empty")
    # If filename doesn't start with _, add it
    if not filename.startswith("_"):
        filename = f"_{filename}"

    media_path = Path(mw.pm.profileFolder(), "collection.media")

    file_path = Path(media_path, filename)

    return file_path.exists()
