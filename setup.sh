#!/bin/bash

# Define the name of the virtual environment directory
VENV_NAME=".venv"

# Define the path to the pyproject.toml file
PYPROJECT_TOML_PATH="./pyproject.toml"

# --- Check for venv installation ---
echo "Checking for 'venv' module..."
python3 -m venv --help > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "Error: The 'venv' module is not installed for 'python3'."
    echo "On Debian/Ubuntu, you might need to install 'python3-venv'."
    exit 1
fi

# --- Create Virtual Environment ---
CREATE_VENV=true

if [ -d "$VENV_NAME" ]; then
    # Default to "no" if there is no interactive input (e.g. piped/CI)
    read -r -p "Virtual environment '$VENV_NAME' already exists. Reinstall it? [y/N] " REPLY
    case "$REPLY" in
        [yY]|[yY][eE][sS])
            echo "Removing existing virtual environment '$VENV_NAME'..."
            rm -rf "$VENV_NAME"
            hash -r
            ;;
        *)
            echo "Keeping existing virtual environment. Skipping creation."
            CREATE_VENV=false
            ;;
    esac
fi

if [ "$CREATE_VENV" = true ]; then
    echo "Creating virtual environment '$VENV_NAME'..."
    python3 -m venv "$VENV_NAME" --prompt "ARDiS"
    if [ $? -ne 0 ]; then
        echo "Error: Failed to create virtual environment."
        exit 1
    fi
fi

# --- Activate Virtual Environment ---
echo "Activating virtual environment '$VENV_NAME'..."
# Note: Activation only persists if the script is sourced
source "$VENV_NAME/bin/activate"

# --- Check for pyproject.toml ---
if [ ! -f "$PYPROJECT_TOML_PATH" ]; then
    echo "Error: 'pyproject.toml' not found at '$PYPROJECT_TOML_PATH'."
    deactivate 2> /dev/null
    exit 1
fi

# --- Install Project ---
echo "Installing project from 'pyproject.toml' in editable mode..."
pip3 install -e .
if [ $? -ne 0 ]; then
    echo "Error: Failed to install the project."
    deactivate 2> /dev/null
    exit 1
fi

deactivate 2> /dev/null

# --- Completion Message ---
echo ""
echo "Setup is complete!"
echo "To activate the virtual environment in your shell, run: source env.sh"