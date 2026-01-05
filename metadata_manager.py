import logging
import os

import requests
from PySide6.QtWidgets import QTableWidget

import gui_manager
import path_manager
import shortcut_manager
import state

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()


def download_image(url: str, save_path: str) -> bool:
    headers = {"Authorization": f"Bearer {state.api_key}"}
    try:
        limit = "?limit=1"
        if url.__contains__("?"):
            limit = "&limit=1"
        r = requests.get(url + limit, headers=headers)
    except Exception as exc:
        logger.error("Failed to query image metadata for %s: %s", save_path, exc)
        return False

    if r.status_code != 200:
        logger.error("Metadata request returned %s for %s", r.status_code, save_path)
        return False

    try:
        data = r.json()
    except ValueError:
        logger.error("Invalid JSON response when querying image for: %s", save_path)
        return False

    img_data = data.get("data", [])
    if len(img_data) < 1:
        logger.error("Image not found for: %s", save_path)
        return False

    img_url = img_data[0].get("url")
    if not img_url:
        logger.error("No image URL present in response for: %s", save_path)
        return False

    try:
        img = requests.get(img_url, stream=True)
    except Exception as exc:
        logger.error("Failed to download image from %s: %s", img_url, exc)
        return False

    if img.status_code != 200:
        logger.error("Image download returned %s for %s", img.status_code, img_url)
        return False

    mimetype = img.headers.get("Content-Type")
    path = save_path
    if mimetype == "image/jpeg":
        path += ".jpg"
    elif mimetype == "image/png":
        path += ".png"
    elif mimetype == "image/webp":
        path += ".webp"
    elif mimetype == "image/vnd.microsoft.icon":
        path += ".ico"
    else:
        logger.error("Unsupported image type: %s", mimetype)
        return False

    # Ensure the target directory exists (create recursively if needed)
    dirpath = os.path.dirname(path)
    if dirpath:
        os.makedirs(dirpath, exist_ok=True)

    # Write the image to disk
    try:
        with open(path, "wb") as f:
            for chunk in img.iter_content(8192):
                if chunk:
                    f.write(chunk)
    except Exception as exc:
        logger.error("Failed to write image to %s: %s", save_path, exc)
        return False

    logger.info("Downloaded image for: %s", save_path)

    # After successful download, remove any other files with the same base name but different extension
    try:
        base_dir = os.path.dirname(path) or "."
        base_name = os.path.splitext(os.path.basename(save_path))[0]
        for fname in os.listdir(base_dir):
            fbase, fext = os.path.splitext(fname)
            # If same base name but different filename than the one we just saved -> delete it
            if fbase == base_name and os.path.join(base_dir, fname) != os.path.normpath(
                path
            ):
                try:
                    os.remove(os.path.join(base_dir, fname))
                    logger.debug(
                        "Removed duplicate image with different extension: %s", fname
                    )
                except Exception as exc:
                    logger.warning(
                        "Failed to remove duplicate image %s: %s", fname, exc
                    )
    except Exception as exc:
        logger.debug("Failed to clean up duplicate images for %s: %s", save_path, exc)

    return True


def grab_metadata():
    if not state.api_key:
        logger.error("No API key for SteamGridDB defined in config")
        state.window.statusBar().showMessage("SteamGridDB API key not set in config")  # type: ignore
        return

    state.window.statusBar().showMessage("Grabbing metadata...")  # type: ignore

    url = "https://www.steamgriddb.com/api/v2"

    headers = {"Authorization": f"Bearer {state.api_key}"}

    shortcuts = state.shortcuts
    id_dict = {}
    for _, k in enumerate(shortcuts):
        # grab metadata
        shortcut = shortcuts[k]
        query = shortcut["AppName"]

        search_url = f"{url}/search/autocomplete/{query}"
        resp = requests.get(search_url, headers=headers)
        data = resp.json()

        if "data" not in data or not data["data"]:
            logger.error("No metadata match found for: %s", query)
            continue

        game = data["data"][0]  # best match
        game_id = game["id"]
        game_name = game["name"]

        # TODO: namelock?
        state.shortcuts[k]["AppName"] = game_name
        id_dict[shortcut["AppName"]] = game_id

        # Download images
        grid_path = path_manager.get_grid_path(state.steam_path, state.user)
        grid_id = int(shortcut["appid"]) & 0xFFFFFFFF  # type: ignore

        # Hero
        hero_path = os.path.join(grid_path, f"{str(grid_id)}_hero")
        download_image(f"{url}/heroes/game/{game_id}", hero_path)

        # Cover
        cover_path = os.path.join(grid_path, f"{str(grid_id)}p")
        download_image(f"{url}/grids/game/{game_id}?dimensions=600x900", cover_path)

        # Wide
        wide_path = os.path.join(grid_path, f"{str(grid_id)}")
        download_image(
            f"{url}/grids/game/{game_id}?dimensions=920x430,460x215", wide_path
        )

        # Logo
        logo_path = os.path.join(grid_path, f"{str(grid_id)}_logo")
        download_image(f"{url}/logos/game/{game_id}", logo_path)

    shortcut_manager.set_new_shortcuts()
    gui_manager.update_shortcut_list(state.shortcuts)
    # Update shortcuts
    shortcuts_path = path_manager.get_shortcuts_path(state.steam_path, state.user)
    state.shortcuts = shortcut_manager.get_existing_shortcuts(shortcuts_path)

    logger.info("Grabbing metadata... Done!")
    state.window.statusBar().showMessage("Grabbing metadata... Done!")  # type: ignore
