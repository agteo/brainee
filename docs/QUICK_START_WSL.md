# Quick Start: Running LearnAI in WSL

Fast-track guide to get LearnAI running in WSL.

## Prerequisites Check

- [ ] WSL installed (`wsl --version` in PowerShell)
- [ ] LiquidMetal API key obtained

## 5-Minute Setup

### 1. Open WSL Terminal
```bash
wsl
```

### 2. Copy Project to WSL
```bash
# Copy from Windows to WSL home
cp -r /mnt/c/Users/alext/Desktop/self-evolve ~/self-evolve
cd ~/self-evolve
```

### 3. Install Python (if needed)
```bash
sudo apt update && sudo apt install python3 python3-pip python3-venv -y
```

### 4. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### 5. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 6. Configure API Key
```bash
cp .env.example .env
nano .env
# Add: LIQUIDMETAL_API_KEY=your_key_here
# Save: Ctrl+O, Enter, Ctrl+X
```

### 7. Run It!
```bash
python demo_test.py  # Test everything works
python main.py       # Start the app
```

## That's It!

Your self-evolving AI learning agent is now running in WSL with LiquidMetal AI.

## Quick Commands

```bash
# Start WSL
wsl

# Go to project
cd ~/self-evolve

# Activate environment
source .venv/bin/activate

# Run app
python main.py

# Exit
deactivate && exit
```

## Troubleshooting

**"Module not found"**
```bash
source venv/bin/activate
pip install -r requirements.txt
```

**"Permission denied"**
```bash
chmod +x *.py
```

**Need detailed help?** See [WSL_SETUP.md](WSL_SETUP.md)
