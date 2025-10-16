<p align="center">
  <pre style="color: #22c55e; font-weight: bold; line-height: 1.2; display: inline-block;">██████  ███████ ██    ██ ██ ██    ██ ███████ ██████  
██   ██ ██      ██    ██ ██ ██    ██ ██      ██   ██ 
██████  █████   ██    ██ ██ ██    ██ █████   ██████  
██   ██ ██       ██  ██  ██  ██  ██  ██      ██   ██ 
██   ██ ███████   ████   ██   ████   ███████ ██   ██</pre>
</p>

---
**Builders:** Vibhakar Mohta, Varad Pimpalkhute and Shaurya Rohatgi

**Automatically integrate older repositories with modern codebases using AI-powered analysis and migration.**

ReviveAgent is an intelligent Flask web application that leverages Claude Sonnet 4.5 to automatically analyze, adapt, and integrate legacy code repositories with their modern counterparts. Say goodbye to manual dependency resolution and compatibility issues!

📺 [**Full Presentation**](https://www.youtube.com/watch?v=GzqFLpUFegk) | 📑 [**Slides**](https://docs.google.com/presentation/d/1wTN5MeRkyqQS-VdWmr3JIrjLmjMZJIaJougbkHIujhg/edit?usp=sharing)

---

## 🚀 ReviveAgent Demo

🎬 **Watch in Action:**  
[![ReviveAgent Demo](https://img.youtube.com/vi/rmgXhW6sZ6o/0.jpg)](https://www.youtube.com/watch?v=rmgXhW6sZ6o)

🧠 **Overview:** Repository analysis · Dependency resolution · Code migration

---

## ✨ Key Features

### 🤖 **AI-Powered Integration**
- Powered by **Claude Sonnet 4.5** via Cursor CLI
- Intelligent code analysis and dependency resolution
- Automatic compatibility fixes and version upgrades
- Context-aware code modifications

### 📊 **Comprehensive Observability**
- **Weave Integration**: Full tracing and metrics via W&B Weave
- **Live Agent Output**: Real-time streaming of agent actions
- **Git Diff Viewer**: Side-by-side visualization of all code changes
- **Execution Statistics**: Token usage and tool call tracking

### 📝 **Side-by-Side Git Diff**

![Git Diff Viewer](assests/git_diff.png)

*Real-time visualization of code changes in both R_base and R_old repositories*

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Flask Web App                        │
│  ┌───────────┐  ┌──────────┐  ┌───────────────────┐   │
│  │  Index    │  │ Results  │  │  API Endpoints    │   │
│  │  (Submit) │→ │  (Track) │  │  - /submit        │   │
│  └───────────┘  └──────────┘  │  - /status        │   │
│                                │  - /stream        │   │
│                                │  - /weave-data    │   │
│                                │  - /git-diff      │   │
│                                └───────────────────┘   │
└─────────────────────────────────────────────────────────┘
                         ↓
              ┌──────────────────────┐
              │   ReviveAgent        │
              │  (Cursor CLI Wrapper)│
              └──────────────────────┘
                         ↓
      ┌──────────────────────────────────────────┐
      │         Claude Sonnet 4.5                │
      │  - Code Analysis  - Dependency Resolution│
      │  - File Editing   - Test Generation      │
      └──────────────────────────────────────────┘
                         ↓
         ┌────────────────────────────────┐
         │  Work Directory                │
         │  ├── r_base/                   │
         │  ├── r_old/                    │
         │  ├── setup_r_base.sh           │
         │  ├── test_base.sh              │
         │  ├── test_old.sh               │
         │  └── agent_summary.txt         │
         └────────────────────────────────┘
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.9+
- Cursor CLI installed
- Conda/Mamba package manager
- Git
- Weights & Biases account (for Weave tracing)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd rebibemecode
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Cursor CLI**
   ```bash
   curl https://cursor.com/install -fsS | bash
   ```

4. **Configure Weave** (optional but recommended)
   ```bash
   export WANDB_API_KEY=your_api_key
   ```

5. **Run the Flask app**
   ```bash
   python app.py
   ```

6. **Open your browser**
   ```
   http://localhost:8000
   ```

---

## 📖 Usage

### Web Interface

1. **Navigate to the home page** (`http://localhost:8000`)
2. **Enter repository URLs:**
   - **R_base**: The modern/latest repository (e.g., `https://github.com/Farama-Foundation/Gymnasium`)
   - **R_old**: The legacy repository to integrate (e.g., `https://github.com/igilitschenski/multi_car_racing/`)
3. **Click "Start Integration Process"**
4. **Monitor progress** in real-time on the results page

### Command Line Interface

```python
from classes.revive_agent import ReviveAgent
import classes.utils as utils

# Initialize agent
agent = ReviveAgent(model='sonnet-4.5')

# Run integration
result = utils.setup_r_base_environment(
    agent, 
    workdir="./work_dir", 
    GLOBAL_CONTEXT=context
)
```

## 📁 Project Structure

```
rebibemecode/
├── app.py                      # Main Flask application
├── main.py                     # CLI entry point
├── requirements.txt            # Python dependencies
├── classes/
│   ├── revive_agent.py        # Cursor CLI wrapper
│   ├── utils.py               # Integration utilities
│   └── clean_logger.py        # Stream output parser
├── templates/
│   ├── index.html             # Landing page
│   └── results.html           # Job dashboard
├── docs/
│   ├── STREAMING_GUIDE.md     # Streaming documentation
│   └── WEB_INTERFACE_README.md # Web UI guide
├── tests/
│   └── test_streaming.py      # Unit tests
└── work_dir/                  # Job execution workspace
```

---

## ⚙️ Configuration

### Environment Variables

```bash
# Weave/W&B Configuration
export WANDB_API_KEY=your_api_key
export WEAVE_PROJECT_NAME=rebibemecode-web-app

# Flask Configuration
export FLASK_ENV=development
export FLASK_DEBUG=1
```

### Global Context Customization

Edit the `GLOBAL_CONTEXT` in `app.py` to customize agent behavior:

```python
GLOBAL_CONTEXT = """
Global context:
You are an integration agent...

IMPORTANT COMMAND EXECUTION RULES:
- When running shell commands, ALWAYS use proper syntax
- When installing packages with versions, use quotes: pip install "package==1.2.0"
- Activate conda environments explicitly before installing packages
...
"""
```

---


## 🤝 Contributing

Contributions are welcome! Fork the repository, commit your changes (e.g., adding DSPY GePa optimization feature), and open a PR!

---

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

---


*Rebibemecode - Making legacy code integration effortless*
