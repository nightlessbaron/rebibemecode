# Create a conda environment for this project
conda create -n coderebibe python=3.11
conda activate coderebibe

# Install Cursor CLI
curl https://cursor.com/install -fsS | bash
cursor-agent --version
