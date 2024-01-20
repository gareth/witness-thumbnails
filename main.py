import glob
import mmap
import os
from collections import defaultdict
from datetime import datetime

from tqdm import tqdm

from image import make_thumbnail

addressPanels = [ 0x09FA0, 0x09F86, 0x0C339, 0x09FAA, 0x0A249, 0x1C2DF, 0x1831E, 0x1C260, 0x1831C, 0x1C2F3, 0x1831D, 0x1C2B1, 0x1831B, 0x0A015 ]
slotNamePanels = [ 0x17CC4, 0x275ED, 0x03678, 0x03679, 0x03675, 0x03676, 0x17CAC, 0x03852, 0x03858, 0x38663, 0x275FA, 0x334DB, 0x334DC, 0x09E49 ]
passwordPanels = [ 0x0361B, 0x334D8, 0x2896A, 0x17D02, 0x03713, 0x00B10, 0x00C92, 0x09D9B, 0x17CAB, 0x337FA, 0x0A099, 0x34BC5, 0x34BC6, 0x17CBC ]


def get_address_and_slot_name(save_game_path):
    with open(save_game_path, "r+b") as fh:
        with mmap.mmap(fh.fileno(), 0) as mm:
            pos = mm.find(bytes([0xA1, 0x9F, 0x00, 0x00, 0x1D]))

            if pos == -1:
                return None, None

            address = mm.find(bytes([0x3F, 0x26]), pos)

            if address - pos > 80 or address == -1:
                return None, None

        full_address = ""

        for address_panel in addressPanels:
            bytepattern = (address_panel + 1).to_bytes(4, byteorder='little')
            bytepattern += bytes([0x1D])

            with mmap.mmap(fh.fileno(), 0) as mm:
                pos = mm.find(bytepattern)

                address = mm.find(bytes([0x3F, 0x26]), pos)
                mm.seek(address + 2)

                new_bytes = mm.read(16)

                if bytes([0x00]) in new_bytes:
                    try:
                        full_address += new_bytes.split(bytes([0x00]))[0].decode('utf-8')
                    except UnicodeDecodeError as e:
                        break

                    break
                else:
                    try:
                        full_address += new_bytes.decode('utf-8')
                    except UnicodeDecodeError as e:
                        break

        if not full_address:
            return None, None

        slot_name = ""

        for slot_name_panel in slotNamePanels:
            bytepattern = (slot_name_panel + 1).to_bytes(4, byteorder='little')
            bytepattern += bytes([0x1D])

            with mmap.mmap(fh.fileno(), 0) as mm:
                pos = mm.find(bytepattern)

                address = mm.find(bytes([0x3F, 0x26]), pos)
                mm.seek(address + 2)

                new_bytes = mm.read(16)

                if bytes([0x00]) in new_bytes:
                    try:
                        slot_name += new_bytes.split(bytes([0x00]))[0].decode('utf-8')
                    except UnicodeDecodeError as e:
                        break

                    break
                else:
                    try:
                        slot_name += new_bytes.decode('utf-8')
                    except UnicodeDecodeError as e:
                        break

    return full_address, slot_name


def get_time(savegame):
    basename = os.path.basename(savegame)
    if "time_" in basename:
        date = basename[:10]
        time = basename[(basename.find("time_")+5):-17]
        datetime_string = date + " " + time
        format_string = "%Y.%m.%d %H.%M.%S"
        datetime_obj = datetime.strptime(datetime_string, format_string)
    else:
        datetime_obj = datetime.fromtimestamp(os.path.getmtime(savegame))

    return datetime_obj

def identify_saves(savegame_directory):
    address_slot_to_savegames = defaultdict(lambda: [])

    for save_game in tqdm(glob.glob(os.path.join(savegame_directory, r"*.witness_campaign")), "Parsing save files"):
        address, slot = get_address_and_slot_name(save_game)

        if not address:
            continue

        address_slot_to_savegames[(address, slot)].append(save_game)

    address_slot_to_savegames = {
        key: sorted(savegames, key=lambda k: get_time(k), reverse=True)
        for key, savegames in address_slot_to_savegames.items()
    }

    for address, save_games in tqdm(address_slot_to_savegames.items(), "Generating image files"):
        make_thumbnail(address[0], address[1], save_games[0][:-17] + ".png")
        for older_save_game in save_games[1:]:
            make_thumbnail(address[0], address[1], older_save_game[:-17] + ".png", True)


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    identify_saves(os.path.normpath(os.path.join(os.getenv('APPDATA'), "The Witness")))
