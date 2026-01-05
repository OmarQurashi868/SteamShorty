import logging
import os
import zlib

import vdf
from PySide6.QtWidgets import QTableWidget

import gui_manager
import path_manager
import state

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()


def get_appid(exe, name):
    """Generate Steam shortcut AppID (same algo Steam uses)."""
    data = f"{exe}{name}".encode("utf-8")
    crc = zlib.crc32(data) & 0xFFFFFFFF
    appid = crc | 0x80000000  # non-Steam flag
    return str(appid)


def get_existing_shortcuts(shortcuts_path: str) -> dict[str, dict[str, str | int]]:
    if os.path.exists(shortcuts_path):
        with open(shortcuts_path, "rb") as f:
            return vdf.binary_load(f)["shortcuts"]
    return {}


def set_new_shortcuts():
    shortcuts_path = path_manager.get_shortcuts_path(state.steam_path, state.user)
    data_to_save = {"shortcuts": state.shortcuts}
    if os.path.exists(shortcuts_path):
        with open(shortcuts_path, "wb") as f:
            vdf.binary_dump(data_to_save, f)


def add_new_shortcut(path: str, name: str = ""):
    shortcuts_path = path_manager.get_shortcuts_path(state.steam_path, state.user)
    if not name:
        name = os.path.basename(path)

    if os.path.exists(shortcuts_path):
        appid = get_appid(path, name)
        start_dir = os.path.dirname(path)

        index = str(len(state.shortcuts))  # Key of the new shortcut entry
        state.shortcuts[str(index)] = {  # Modifying the current shortcuts dict
            "appid": appid,
            "AppName": name,
            "Exe": f'"{path}"',
            "StartDir": f'"{start_dir}"',
            "LaunchOptions": "",
            "icon": "",
            "ShortcutPath": "",
            "AllowOverlay": 1,
            "OpenVR": 0,
            "LastPlayTime": 0,
            "tags": {"0": "SteamShorty"},
        }

        set_new_shortcuts()


def get_shortcuts_dict(shortcuts_list: QTableWidget) -> dict[str, dict[str, str | int]]:
    headers = [
        shortcuts_list.horizontalHeaderItem(i).text()
        for i in range(shortcuts_list.columnCount())
    ]  # type: ignore
    # NOTE: the original main branch returned inside the loop (likely a bug).
    # Here’s a safe version that reads all rows into a dict keyed by row index.
    data: dict[str, dict[str, str | int]] = {}
    for row in range(shortcuts_list.rowCount()):
        row_dict: dict[str, str | int | None] = {}
        row_dict: dict[str, str | int | None] = {}
        for col, header in enumerate(headers):
            item = shortcuts_list.item(row, col)
            row_dict[header] = item.text() if item else None
        data[str(row)] = row_dict  # type: ignore # key as string to match vdf-like dicts
    return data


def on_cell_changed(row, col):
    appid_item = state.window.shortcutsList.item(row, 0)  # type: ignore
    if not appid_item:
        return

    app_id = appid_item.text()
    shortcut_id = get_shortcut_id_by_appid(app_id)
    if shortcut_id == -1:
        logger.error("Invalid cell changed")
        return

    state.shortcuts[shortcut_id]["AppName"] = state.window.shortcutsList.item(
        row, 1
    ).text()  # type: ignore
    set_new_shortcuts()
    gui_manager.update_shortcut_list(state.shortcuts)


def get_shortcut_id_by_appid(app_id: str) -> str:
    shortcuts = state.shortcuts
    for _, k in enumerate(shortcuts):
        shortcut = shortcuts[k]
        if shortcut["appid"] == app_id:
            return k
    return "-1"
