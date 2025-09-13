import sys
import state
import path_manager
import shortcut_manager
import gui_manager
import setup_manager
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()

def main():
    logger.info("Initializing...")

    state.window, app = gui_manager.init_main_window()

    setup_manager.load_config()

    if not setup_manager.validate_config(state.steam_path) or not state.user:
        logger.info("Config invalid or missing, opening setup window...")
        state.config_window = gui_manager.init_setup_window()

    # Get shortcuts
    shortcuts_path = path_manager.get_shortcuts_path(state.steam_path, state.user)
    state.shortcuts = shortcut_manager.get_existing_shortcuts(shortcuts_path)
    logger.info("Found %i shortcut entries", len(state.shortcuts))

    # Display the list
    success = gui_manager.update_shortcut_list(state.shortcuts)
    if not success:
        logger.error("Can't find shortcuts table in UI")
        sys.exit("ui_shortcut_table_not_found")

    sys.exit(app.exec())

    existing_shortcuts = shortcut_manager.get_existing_shortcuts(shortcuts_path)
    print('existing shortcuts: ', existing_shortcuts)
    
    # Exit
    logger.info("Exiting")
    sys.exit(0)

if __name__ == "__main__":
    main()

