import module_update  # noqa: F401,I001

import os

from generate_thumbnails_and_remove_old_saves import generate_thumbnails

if __name__ == "__main__":
    appdata = os.getenv("APPDATA")
    if appdata is None:
        raise RuntimeError("Couldn't find appdata directory. Is this not being run on Windows?")

    appdata_witness = os.path.normpath(os.path.join(appdata, "The Witness"))
    if not os.path.isdir(appdata_witness):
        raise RuntimeError('Couldn\'t find "The Witness" directory in Appdata.')

    generate_thumbnails(appdata_witness)
