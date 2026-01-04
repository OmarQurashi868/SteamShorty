import logging
import os
import platform
import sys
from typing import Any

from PySide6.QtCore import QFile, Qt
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (
    QApplication,
    QDialogButtonBox,
    QFileDialog,
    QPushButton,
    QStyleFactory,
    QTableWidget,
    QTableWidgetItem,
)

import metadata_manager
import path_manager
import shortcut_manager
import state
from setup_manager import confirm_config, is_steam_exists, on_path_change

try:
    import win32api
except ImportError:
    win32api = None

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()


def init_main_window():
    app = QApplication()

    # 1. Check for the best available style
    available_styles = QStyleFactory.keys()

    if "Breeze" in available_styles:
        app.setStyle("Breeze")  # Native KDE
    elif "Windows11" in available_styles:
        app.setStyle("Windows11")  # Native Modern Windows
    elif "WindowsVista" in available_styles:
        app.setStyle("WindowsVista")  # Standard Windows
    else:
        app.setStyle("Fusion")  # Safe fallback

    state.app = app

    ui_file = QFile("ui/main_window.ui")
    ui_file.open(QFile.OpenModeFlag.ReadOnly)
    loader = QUiLoader()
    window = loader.load(ui_file)
    ui_file.close()

    if not window:
        logger.error(loader.errorString())
        sys.exit(-1)

    state.window = window
    window.statusBar().showMessage("Welcome to SteamShorty!")  # type: ignore

    # Set buttons
    metadata_button = window.findChild(QPushButton, "metadataButton")
    metadata_button.clicked.connect(metadata_manager.grab_metadata)  # type: ignore

    add_button = window.findChild(QPushButton, "addButton")
    add_button.clicked.connect(add_exe)  # type: ignore

    config_button = window.findChild(QPushButton, "configButton")
    config_button.clicked.connect(init_setup_window)  # type: ignore

    table = window.findChild(QTableWidget, "shortcutsList")
    table.cellChanged.connect(shortcut_manager.on_cell_changed)  # type: ignore

    window.show()


def init_setup_window():
    ui_file = QFile("ui/config_window.ui")
    ui_file.open(QFile.OpenModeFlag.ReadOnly)
    loader = QUiLoader()
    window = loader.load(ui_file)
    ui_file.close()

    if not window:
        logger.error(loader.errorString())
        sys.exit(-1)

    state.config_window = window

    window.setWindowFlags(window.windowFlags() & ~Qt.WindowType.WindowCloseButtonHint)

    # Load config into fields
    window.pathField.setText(state.steam_path)  # type: ignore
    if is_steam_exists(state.steam_path):
        window.pathLabel.setText("Steam installation found")  # type: ignore
        window.pathLabel.setStyleSheet(f"color: {'green'};")  # type: ignore

    window.apiField.setText(state.api_key)  # type: ignore

    users = path_manager.get_steam_users(state.steam_path)
    window.userSelect.addItems(users)  # type: ignore
    if state.user in users:
        window.userSelect.setCurrentIndex(users.index(state.user))  # type: ignore

    if is_steam_exists(state.steam_path) and users:
        window.buttonBox.setEnabled(True)  # type: ignore

    window.pathField.textChanged.connect(on_path_change)  # type: ignore
    ok_button = window.buttonBox.button(QDialogButtonBox.StandardButton.Ok)  # type: ignore
    ok_button.clicked.connect(confirm_config)

    window.browseButton.clicked.connect(set_browsed_path)  # type: ignore

    # Window setup
    window.setWindowModality(Qt.WindowModality.ApplicationModal)
    window.show()
    window.setFocus()  # So no child takes first focus


def set_browsed_path():
    path = QFileDialog.getExistingDirectory(
        state.window, "Select Steam folder", state.steam_path
    )
    if path:
        state.config_window.pathField.setText(path)  # type: ignore


def update_shortcut_list(shortcuts: dict[str, Any]) -> bool:
    shortcuts_list = state.window.findChild(QTableWidget, "shortcutsList")
    if not shortcuts_list:
        return False
    shortcuts_list.blockSignals(True)

    columns = ["AppId", "AppName", "Path"]
    entry_columns = ["appid", "AppName", "Exe"]

    # shortcuts_list.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    # shortcuts_list.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    # shortcuts_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
    shortcuts_list.setRowCount(len(shortcuts))
    shortcuts_list.setColumnCount(3)
    shortcuts_list.setHorizontalHeaderLabels(columns)

    for row_idx, entry in enumerate(shortcuts.values()):
        for col_idx, col in enumerate(columns):
            item = QTableWidgetItem(col)
            if col != "AppName":
                item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)
            if col == "Path":
                item.setToolTip(str(entry[entry_columns[col_idx]]))
            if col == "AppId":
                # signed int -> unsigned int
                entry[entry_columns[col_idx]] = str(
                    int(entry[entry_columns[col_idx]]) + (1 << 32)
                )

            value = entry.get(entry_columns[col_idx], "")
            item.setText(str(value))
            shortcuts_list.setItem(row_idx, col_idx, item)

    shortcuts_list.sortItems(1, Qt.SortOrder.AscendingOrder)
    shortcuts_list.blockSignals(False)
    return True


def get_selected_rows() -> set[int]:
    selected_shortcuts = set()

    shortcuts_list = state.window.findChild(QTableWidget, "shortcutsList")
    if not shortcuts_list:
        return selected_shortcuts

    for idx in shortcuts_list.selectionModel().selectedRows():
        row = idx.row()
        selected_shortcuts.add(row)
    return selected_shortcuts


def add_exe():
    exe_path, _ = QFileDialog.getOpenFileName(
        state.window, "Select Executable", "", "Executable Files (*.exe)"
    )

    exe_path = os.path.normpath(exe_path)
    if not exe_path or exe_path == ".":
        return

    logger.info("Selected exe path: %s", exe_path)

    app_name = extract_app_name(exe_path)
    shortcut_manager.add_new_shortcut(exe_path, app_name)

    shortcuts_path = path_manager.get_shortcuts_path(state.steam_path, state.user)
    new_shortcuts = shortcut_manager.get_existing_shortcuts(shortcuts_path)
    update_shortcut_list(new_shortcuts)
    state.window.statusBar().showMessage(f'"{app_name}" was added successfully')  # type: ignore


def extract_app_name(exe_path: str) -> str:
    system = platform.system()

    if system == "Windows" and win32api:
        try:
            info = win32api.GetFileVersionInfo(exe_path, "\\")
            lang, codepage = list(info["StringFileInfo"].keys())[0]  # type: ignore
            metadata = info["StringFileInfo"][(lang, codepage)]  # type: ignore
            return metadata.get("FileDescription") or metadata.get("ProductName") or ""
        except Exception:
            pass

    return os.path.splitext(os.path.basename(exe_path))[0]
