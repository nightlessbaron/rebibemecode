#!/bin/bash

# Setup script for R_base (Gymnasium) repository
# This script creates a Python virtual environment and installs dependencies

set -e  # Exit on any error

echo "=== R_base (Gymnasium) Setup Script ==="
echo "Working directory: $(pwd)"

# Check if r_base directory exists
if [ ! -d "r_base" ]; then
    echo "ERROR: r_base directory not found!"
    echo "Expected to find r_base/ in current directory"
    exit 1
fi

# Remove existing virtual environment if it exists
if [ -d "env_r_base" ]; then
    echo "Removing existing virtual environment..."
    rm -rf env_r_base
fi

# Create new virtual environment
echo "Creating Python virtual environment at env_r_base..."
python3 -m venv env_r_base

# Activate virtual environment
echo "Activating virtual environment..."
source env_r_base/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install Gymnasium in development mode
echo "Installing Gymnasium in development mode..."
cd r_base
pip install -e .

# Install additional dependencies for testing
echo "Installing testing dependencies..."
pip install pytest scipy dill array_api_extra

# Install optional dependencies for Box2D (needed for CarRacing)
echo "Installing Box2D dependencies..."
pip install "gymnasium[box2d]"

# Verify installation
echo "Verifying installation..."
python -c "import gymnasium; print(f'Gymnasium version: {gymnasium.__version__}')"
python -c "import gymnasium; print(f'Available environments: {len(list(gymnasium.envs.registry.values()))}')"

# Check if CarRacing environment is available
echo "Checking for CarRacing environment..."
python -c "
import gymnasium as gym
try:
    env = gym.make('CarRacing-v2')
    print('CarRacing-v2 environment is available')
    env.close()
except Exception as e:
    print(f'CarRacing-v2 not available: {e}')
    # Try other versions
    for version in ['v0', 'v1', 'v3']:
        try:
            env = gym.make(f'CarRacing-{version}')
            print(f'CarRacing-{version} environment is available')
            env.close()
            break
        except:
            continue
"

cd ..

echo "=== Setup completed successfully! ==="
echo "Virtual environment location: $(pwd)/env_r_base"
echo "To activate: source env_r_base/bin/activate"
echo "To test: ./test_base.sh"