import logging
import os
import platform

# winreg is a Windows-only module; import it conditionally so this module can be imported on non-Windows systems.
try:
    if platform.system() == "Windows":
        import winreg  # type: ignore
    else:
        # Keep a placeholder so the rest of the code can safely check for None.
        winreg = None  # type: ignore
except ImportError:
    winreg = None  # type: ignore

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()


def get_steam_path() -> str:
    system = platform.system()
    if system == "Windows":
        try:
            # If winreg couldn't be imported for some reason, fall back to default path.
            if winreg is None:
                raise ImportError("winreg unavailable")
            # Open registry key for Steam
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"SOFTWARE\Valve\Steam")
            steam_path, _ = winreg.QueryValueEx(key, "SteamPath")
            winreg.CloseKey(key)
            return os.path.normpath(steam_path)
        except Exception:
            # Fallback common install location
            return "C:\\Program Files (x86)\\Steam"
    elif system == "Linux":
        # Try common Steam locations on Linux, including Flatpak
        possible = [
            os.path.expanduser("~/.local/share/Steam"),
            os.path.expanduser("~/.steam/steam"),
            os.path.expanduser("~/.var/app/com.valvesoftware.Steam/data/Steam"),
        ]
        for p in possible:
            if os.path.exists(p):
                logger.info("Using Steam path: %s", p)
                return os.path.normpath(p)
        # If none found, return a sane default (expanded & normalized)
        fallback = os.path.normpath(possible[0])
        logger.debug(
            "No existing Steam path found, falling back to default: %s", fallback
        )
        return fallback
    else:
        return ""


def get_steam_users(steam_path: str) -> list[str]:
    userdata_path = os.path.join(steam_path, "userdata")
    try:
        _, users, _ = next(os.walk(userdata_path))
        logger.info("Found %s users", len(users))
        return users
    except StopIteration:
        return []


def get_shortcuts_path(steam_path: str, user: str) -> str:
    return os.path.join(steam_path, "userdata", user, "config", "shortcuts.vdf")


def get_grid_path(steam_path: str, user: str) -> str:
    return os.path.join(steam_path, "userdata", user, "config", "grid")
