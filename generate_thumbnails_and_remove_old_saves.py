import glob
import mmap
import os
from collections import defaultdict
from datetime import datetime, timedelta
from functools import lru_cache
from typing import BinaryIO, Dict, List, Optional, Tuple

from send2trash import send2trash
from tqdm import tqdm

import module_update  # noqa: F401
from image import make_thumbnail

ADDRESS_PANELS = [
    0x09FA0,
    0x09F86,
    0x0C339,
    0x09FAA,
    0x0A249,
    0x1C2DF,
    0x1831E,
    0x1C260,
    0x1831C,
    0x1C2F3,
    0x1831D,
    0x1C2B1,
    0x1831B,
    0x0A015,
]
SLOT_NAME_PANELS = [
    0x17CC4,
    0x275ED,
    0x03678,
    0x03679,
    0x03675,
    0x03676,
    0x17CAC,
    0x03852,
    0x03858,
    0x38663,
    0x275FA,
    0x334DB,
    0x334DC,
    0x09E49,
]
PASSWORD_PANELS = [
    0x0361B,
    0x334D8,
    0x2896A,
    0x17D02,
    0x03713,
    0x00B10,
    0x00C92,
    0x09D9B,
    0x17CAB,
    0x337FA,
    0x0A099,
    0x34BC5,
    0x34BC6,
    0x17CBC,
]

REMOVE_REDUNDANTS_OLDER_THAN: Optional[timedelta] = timedelta(days=10)
REMOVE_AP_OLDER_THAN: Optional[timedelta] = timedelta(days=365 * 2 / 3)
REMOVE_REGARDLESS_OLDER_THAN: Optional[timedelta] = None

# Use this to also remove old non-AP save games:
# REMOVE_REGARDLESS_OLDER_THAN: Optional[timedelta] = timedelta(days=365)


def get_string_from_panels(fh: BinaryIO, panel_set: List[int]) -> str:
    ret_string = ""

    for characteristic_panel in panel_set:
        bytepattern = (characteristic_panel + 1).to_bytes(4, byteorder="little")
        bytepattern += bytes([0x1D])

        with mmap.mmap(fh.fileno(), 0) as mm:
            pos = mm.find(bytepattern)

            address = mm.find(bytes([0x3F, 0x26]), pos)
            mm.seek(address + 2)

            new_bytes = mm.read(16)

            if bytes([0x00]) in new_bytes:
                try:
                    ret_string += new_bytes.split(bytes([0x00]))[0].decode("utf-8")
                except UnicodeDecodeError:
                    break

                break
            else:
                try:
                    ret_string += new_bytes.decode("utf-8")
                except UnicodeDecodeError:
                    break

    return ret_string


def get_address_and_slot_name(save_game_path: str) -> Tuple[Optional[str], Optional[str]]:
    with open(save_game_path, "r+b") as fh:
        with mmap.mmap(fh.fileno(), 0) as mm:
            pos = mm.find(bytes([0xA1, 0x9F, 0x00, 0x00, 0x1D]))

            if pos == -1:
                return None, None

            address = mm.find(bytes([0x3F, 0x26]), pos)

            if address - pos > 80 or address == -1:
                return None, None

        full_address = get_string_from_panels(fh, ADDRESS_PANELS)

        if not full_address:
            return None, None

        slot_name = get_string_from_panels(fh, SLOT_NAME_PANELS)

    return full_address, slot_name


def get_time(save_game: str) -> datetime:
    basename = os.path.basename(save_game)
    if "time_" in basename:
        date = basename[:10]
        time = basename[(basename.find("time_") + 5) : -17]
        datetime_string = date + " " + time
        format_string = "%Y.%m.%d %H.%M.%S"
        datetime_obj = datetime.strptime(datetime_string, format_string)
    else:
        datetime_obj = datetime.fromtimestamp(os.path.getmtime(save_game))

    return datetime_obj


def remove_witness_save_game(save_game: str) -> None:
    if os.path.isfile(save_game):
        send2trash(save_game)
    if os.path.isfile(save_game[:-17] + ".png"):
        send2trash(save_game[:-17] + ".png")


def remove_old_saves(save_game_directory: str) -> None:
    address_slot_to_save_games = identify_saves(save_game_directory)

    for save_game in address_slot_to_save_games[(None, None)]:
        if REMOVE_REGARDLESS_OLDER_THAN and datetime.now() - get_time(save_game) > REMOVE_REGARDLESS_OLDER_THAN:
            print(f"Removing save file older than {REMOVE_REGARDLESS_OLDER_THAN}: f{save_game}")
            remove_witness_save_game(save_game)

    address_slot_to_save_games = {
        key: sorted(save_games, key=lambda k: get_time(k), reverse=True)
        for key, save_games in address_slot_to_save_games.items()
        if key != (None, None)
    }

    for address, save_games in address_slot_to_save_games.items():
        if REMOVE_AP_OLDER_THAN and datetime.now() - get_time(save_games[0]) > REMOVE_AP_OLDER_THAN:
            print(f"Removing AP save file older than {REMOVE_AP_OLDER_THAN}: f{save_games[0]}")
            remove_witness_save_game(save_games[0])
        for older_save_game in save_games[1:]:
            if (
                REMOVE_REDUNDANTS_OLDER_THAN
                and datetime.now() - get_time(older_save_game) > REMOVE_REDUNDANTS_OLDER_THAN
            ):
                print(f"Removing redundant save file older than {REMOVE_REDUNDANTS_OLDER_THAN}: f{older_save_game}")
                remove_witness_save_game(older_save_game)


def generate_thumbnails(save_game_directory: str) -> None:
    address_slot_to_save_games = identify_saves(save_game_directory)

    address_slot_to_save_games = {
        key: sorted(save_games, key=lambda k: get_time(k), reverse=True)
        for key, save_games in address_slot_to_save_games.items()
        if key != (None, None)
    }

    for address, save_games in tqdm(address_slot_to_save_games.items(), "Generating image files"):
        make_thumbnail(address[0], address[1], save_games[0][:-17] + ".png")
        for older_save_game in save_games[1:]:
            make_thumbnail(address[0], address[1], older_save_game[:-17] + ".png", True)


@lru_cache
def identify_saves(save_game_directory: str) -> Dict[Tuple[Optional[str], Optional[str]], List[str]]:
    address_slot_to_save_games = defaultdict(lambda: [])

    for save_game in tqdm(glob.glob(os.path.join(save_game_directory, r"*.witness_campaign")), "Parsing save files"):
        address_slot_to_save_games[get_address_and_slot_name(save_game)].append(save_game)

    return address_slot_to_save_games


if __name__ == "__main__":
    appdata = os.getenv("APPDATA")
    if appdata is None:
        raise RuntimeError("Couldn't find appdata directory. Is this not being run on Windows?")

    appdata_witness = os.path.normpath(os.path.join(appdata, "The Witness"))
    if not os.path.isdir(appdata_witness):
        raise RuntimeError('Couldn\'t find "The Witness" directory in Appdata.')

    remove_old_saves(appdata_witness)
    generate_thumbnails(appdata_witness)
