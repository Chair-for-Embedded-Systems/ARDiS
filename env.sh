#!/bin/bash

VENV_DIR=".venv"

# Check if a virtual environment is already active
if [ -n "$VIRTUAL_ENV" ]; then
  echo "Environment already active: $(basename "$VIRTUAL_ENV")"
  return 0
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
    PS1="(ARDiS) $_OLD_PS1"
  else
    echo "Error: Activation script not found in $VENV_DIR."
    return 1
  fi
else
  echo "Warning: Virtual environment folder '$VENV_DIR' not found."
  return 1
fi