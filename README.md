# Create a conda environment for this project
conda create -n coderebibe python=3.11
conda activate coderebibe

# Install project dependencies
pip install -r requirements.txt

# Install Cursor CLI
curl https://cursor.com/install -fsS | bash
cursor-agent --version


# Running the code
```
BASE_DIR=https://github.com/DLR-RM/stable-baselines3
OLD_DIR=https://github.com/openai/atari-py
python main.py\
  --R_base $BASE_DIR\
  --R_old $OLD_DIR
```