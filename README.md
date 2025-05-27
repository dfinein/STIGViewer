# STIG Viewer

STIGViewer works to parse the current STIG ZIP across all platforms (including Apple), leveraging the Textualize library for user interaction.

## To-Do

- [ ] Create a better STIG tree to view from
- [ ] Update widget tags
- [ ] Fix loading screen for rendering a STIG
- [ ] Add option to allow the file to be fully decompressed to make the output faster
- [ ] Create web version
- [ ] Arrange for horizontal layout

## Quick Start

1. Clone the repository with `git clone https://github.com/dfinein/STIGViewer.git`
2. Create a virtual environment `python3 -m venv venv` , and activate the environment
3. Install dependencies with `pip install -r requirements.txt`
4. Download a copy of the latest STIG ZIP (GitHub won't allow the filesize for it) and put it into the same directory.  It should be named something like `U_SRG-STIG...zip`
5. Run the application with the basic `python PythonViewer.py`
