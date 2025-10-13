# Plotter A23-46

`Plotter_A23_46` is a Python application that uses the `UI_TS1` framework, which in turn relies on the `Renderer_D_30F6` to draw aesthetic plots.
The project is structured using Git submodules, so dependencies are automatically tracked at specific versions.


# Installation

1. Clone the repository with all submodules

    ```bash
    git clone --recurse-submodules https://github.com/alekoza02/PLOTTER_A23_46.git && cd PLOTTER_A23_46
    git submodule sync --recursive && git submodule update --init --recursive
    ```
    
    This will automatically clone `UI_TS1` inside `Plotter_A23_46` and `Renderer_D_30F6` inside `UI_TS1`,
    at the versions pinned by the project.

2. Run the application

    ```bash
    python main.py
    ```


# Updating to new versions

- When a new version of Rendering Engine or UI is released:

    ```bash
    git pull --recurse-submodules && git submodule update --init --recursive
    ```

# Notes

- Each repository is versioned independently using Git tags.