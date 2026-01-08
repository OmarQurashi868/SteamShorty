# SteamShorty (Work In Progress)

A handy utility for easily managing non-Steam games shortcuts in Steam on Windows & Linux, it also grabs the metadata and cover arts for you :).

Built with Python and Qt.

# Features
- Easy and quick adding of shortcuts by clicking the button or drag & dropping an exe
- Easily rename or delete shortcuts (Double click name to edit)
- Automatically grab metadata including correct full game name + cover art (needs [SteamGridDB](https://www.steamgriddb.com/) API key)
- Windows & Linux support!

# Installation
To install SteamShorty, follow these steps:

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/SteamShorty.git
   ```

2. Navigate to the project directory:
   ```
   cd SteamShorty
   ```

3. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```
 
> [!NOTE]
> If you are on linux, do this instead:
> Install these 2 packages manually:
> ```
> pip install Requests vdf
> ```
> And also install pyside6 as a system package:
> ```
> sudo apt install python3-pyside6
> ```

4. Run the application:
   ```
   python main.py
   ```

# TODO
- Delete button (artwork)
- Delete confirm dialogue
- Existance check (checksum/filename)
- App images and other linux bins
- Arguments, editable paths and args
- Tooltips for all
- Status bar freeze
- Categories
- Name lock?
- Pyinstaller
