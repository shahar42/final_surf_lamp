#!/bin/bash
# Surf Lamp venv activation script
# Bypasses pyenv to activate the local virtual environment

# Completely disable pyenv for this session
export PATH=$(echo $PATH | tr ':' '\n' | grep -v pyenv | tr '\n' ':')
unset PYENV_VERSION
unset PYENV_ROOT

# Activate the venv
source ~/Git_Surf_Lamp_Agent/esurf/bin/activate

# Verify it worked
echo "✅ Virtual environment activated!"
echo "Python: $(which python)"
echo "Version: $(python --version)"
