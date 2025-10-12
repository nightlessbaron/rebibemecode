# REVIVE BOT

## Create a conda environment for this project
conda create -n coderebibe python=3.11
conda activate coderebibe

## Install project dependencies
pip install -r requirements.txt

## Install Cursor CLI
curl https://cursor.com/install -fsS | bash
cursor-agent --version


## Running the code
1. Delete coderebibe and env_r_base if they exist
2. Make the coderebibe environment
3. Activate and run the code
```bash
conda deactivate
conda remove -n coderebibe --all -y
conda remove -n env_r_base --all -y

conda create -n coderebibe python=3.11 -y
conda activate coderebibe
pip install -r requirements.txt
curl https://cursor.com/install -fsS | bash

# Run locally or
BASE_DIR=https://github.com/Farama-Foundation/Gymnasium
OLD_DIR=https://github.com/axelbr/racecar_gym
python main.py\
  --R_base $BASE_DIR\
  --R_old $OLD_DIR\
  --model sonnet-4.5

# Run with GUI
python app.py
```