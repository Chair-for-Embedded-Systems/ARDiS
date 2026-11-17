#!/bin/bash

VENV_DIR=".venv"
VENV_PROMPT="\[\e[35m\](ARDiS)\[\e[0m\]"

# Check if a virtual environment is already active
if [ -n "$VIRTUAL_ENV" ]; then
  echo "An existing virtual environment is already active: $VIRTUAL_ENV"
  read -r -p "Reload it? [y/N] " _REPLY
  case "$_REPLY" in
    [yY]|[yY][eE][sS])
      if declare -F deactivate > /dev/null; then
        echo "Deactivating current environment..."
        deactivate   # also restores the original PS1
        hash -r      # drop cached command paths from the old venv
      else
        echo "Error: 'deactivate' not available; cannot reload."
        unset _REPLY
        return 1
      fi
      ;;
    *)
      unset _REPLY
      return 0
      ;;
  esac
  unset _REPLY
fi

# Check if the .venv directory exists
if [ -d "$VENV_DIR" ]; then
  ACTIVATE_SCRIPT=""

  # Check for common activation script paths
  if [ -f "$VENV_DIR/bin/activate" ]; then
    ACTIVATE_SCRIPT="$VENV_DIR/bin/activate"
  elif [ -f "$VENV_DIR/Scripts/activate" ]; then
    ACTIVATE_SCRIPT="$VENV_DIR/Scripts/activate"
  fi

  if [ -n "$ACTIVATE_SCRIPT" ]; then
    _OLD_PS1="$PS1"
    source "$ACTIVATE_SCRIPT"
    PS1="$VENV_PROMPT $_OLD_PS1"
  else
    echo "Error: Activation script not found in $VENV_DIR."
    return 1
  fi
else
  echo "Warning: Virtual environment folder '$VENV_DIR' not found."
  return 1
fi