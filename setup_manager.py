import json
import logging
import os
import platform

import gui_manager
import path_manager
import shortcut_manager
import state

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()


def get_config_path() -> str:
    """
    Return a platform-appropriate path for the application's config.json.

    - Windows: %APPDATA%/SteamShorty/config.json (existing behavior)
    - Linux:   $XDG_CONFIG_HOME/SteamShorty/config.json or ~/.config/SteamShorty/config.json
    - Other:   empty string
    """
    system = platform.system()
    if system == "Windows":
        return os.path.join(os.getenv("APPDATA"), "SteamShorty", "config.json")  # type: ignore
    elif system == "Linux":
        xdg = os.environ.get("XDG_CONFIG_HOME")
        if xdg:
            base = xdg
        else:
            base = os.path.expanduser("~/.config")
        return os.path.join(base, "SteamShorty", "config.json")
    else:
        return ""


def get_config() -> dict[str, str]:
    config_path = get_config_path()

    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
            logger.info("Loaded existing config")
            return config
    else:
        # Return defaults
        logger.info("No existing config found, using defaults...")
        steam_path = path_manager.get_steam_path()

        return {"steam_path": steam_path, "user": "", "api_key": ""}


def load_config():
    config = get_config()

    state.steam_path = config["steam_path"]
    state.user = config["user"]
    state.api_key = config["api_key"]


def save_config():
    config = {}

    config["steam_path"] = state.steam_path
    config["user"] = state.user
    config["api_key"] = state.api_key

    # Write file
    config_path = get_config_path()
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f)
        logger.info("Saved config")


def validate_config(steam_path: str) -> bool:
    # Check steam install
    if not is_steam_exists(steam_path):
        logger.error("Invalid Steam path provided")
        return False
    logger.info("Steam found at: %s", steam_path)

    # Check user existence
    if not path_manager.get_steam_users(steam_path):
        logger.error("No users found")
        return False

    logger.info("Config is valid")

    return True


def is_steam_exists(path: str) -> bool:
    """
    Check whether Steam appears to exist at `path`.

    - On Windows: verify presence of steam.exe
    - On Linux: verify presence of a Steam executable/script (steam or steam.sh) or the steamapps directory
    """
    if not path:
        return False

    system = platform.system()
    if system == "Windows":
        return os.path.exists(os.path.join(path, "steam.exe"))
    elif system == "Linux":
        # Common indicators of a Steam installation on Linux
        steam_bin = os.path.join(path, "steam")
        steam_sh = os.path.join(path, "steam.sh")
        steamapps_dir = os.path.join(path, "steamapps")
        if (
            os.path.exists(steam_bin)
            or os.path.exists(steam_sh)
            or os.path.isdir(steamapps_dir)
        ):
            return True
        # Also accept the Flatpak-style layout where the Steam binary may be under 'data/Steam'
        alt_steam_bin = os.path.join(path, "data", "Steam", "steam")
        alt_steam_sh = os.path.join(path, "data", "Steam", "steam.sh")
        if os.path.exists(alt_steam_bin) or os.path.exists(alt_steam_sh):
            return True
        return False
    else:
        return False


def on_path_change(path: str):
    if not is_steam_exists(path):
        state.config_window.pathLabel.setText("Steam installation NOT found")  # type: ignore
        state.config_window.pathLabel.setStyleSheet(f"color: {'red'};")  # type: ignore
        state.config_window.userSelect.clear()  # type: ignore
        state.config_window.buttonBox.setEnabled(False)  # type: ignore
        return

    state.config_window.pathLabel.setText("Steam installation found")  # type: ignore
    state.config_window.pathLabel.setStyleSheet(f"color: {'green'};")  # type: ignore
    users = path_manager.get_steam_users(path)
    state.config_window.userSelect.addItems(users)  # type: ignore
    state.config_window.userSelect.setCurrentIndex(0)  # type: ignore
    state.config_window.buttonBox.setEnabled(True)  # type: ignore


def confirm_config():
    steam_path = state.config_window.pathField.text()  # type: ignore
    if not validate_config(steam_path):
        logger.error("Config is invalid")
        return

    state.steam_path = steam_path
    state.user = state.config_window.userSelect.currentText()  # type: ignore
    state.api_key = state.config_window.apiField.text()  # type: ignore

    save_config()
    shortcuts_path = path_manager.get_shortcuts_path(state.steam_path, state.user)
    state.shortcuts = shortcut_manager.get_existing_shortcuts(shortcuts_path)
    gui_manager.update_shortcut_list(state.shortcuts)
