# Running LearnAI in WSL (Windows Subsystem for Linux)

This guide helps you run LearnAI in WSL if LiquidMetal requires a Linux environment.

## Why WSL?

Some Python packages (including potentially LiquidMetal) work better in a Linux environment. WSL gives you a full Linux environment on Windows.

## Prerequisites

1. **WSL installed** - If not, run in PowerShell (as Administrator):
   ```powershell
   wsl --install
   ```
   This installs Ubuntu by default. Restart your computer.

2. **Check WSL is working**:
   ```bash
   wsl --version
   ```

## Setup Steps

### 1. Access WSL

Open WSL Ubuntu terminal:
- Press `Win + R`, type `wsl`, press Enter
- Or search for "Ubuntu" in Start menu

### 2. Navigate to Your Project

**Option A: Access Windows files from WSL**
```bash
# Your Windows C: drive is at /mnt/c/
cd /mnt/c/Users/alext/Desktop/self-evolve
```

**Option B: Copy to WSL filesystem (Recommended - Better Performance)**
```bash
# Copy from Windows to WSL home directory
cp -r /mnt/c/Users/alext/Desktop/self-evolve ~/self-evolve
cd ~/self-evolve
```

**Why Option B?** Files in WSL's native filesystem (`~/`) are much faster than accessing Windows files (`/mnt/c/`).

### 3. Install Python in WSL

Check if Python is installed:
```bash
python3 --version
```

If not installed:
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv -y
```

### 4. Create Virtual Environment (Fresh in WSL)

```bash
# Create new venv in WSL
python3 -m venv venv

# Activate it
source venv/bin/activate

# Your prompt should now show (venv)
```

### 5. Install Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install all dependencies
pip install -r requirements.txt
```

**Note**: This installs LiquidMetal, Daft, and all other dependencies in the Linux environment.

### 6. Fix Line Endings (If Needed)

If files were created on Windows, they may have Windows line endings (CRLF). Convert to Unix (LF):

```bash
# Install dos2unix if needed
sudo apt install dos2unix -y

# Convert all Python files
find . -name "*.py" -type f -exec dos2unix {} \;
find . -name "*.md" -type f -exec dos2unix {} \;

# Convert .env files
dos2unix .env.example
dos2unix .env 2>/dev/null || true
```

### 7. Set Up Environment Variables

```bash
# Copy example env file
cp .env.example .env

# Edit with nano (or vim)
nano .env
```

Add your API keys:
```bash
LIQUIDMETAL_API_KEY=your_actual_key_here
OPENAI_API_KEY=your_openai_key_here  # Optional
```

Save: `Ctrl+O`, `Enter`, then exit: `Ctrl+X`

### 8. Test the Installation

```bash
# Activate venv if not already
source venv/bin/activate

# Run test suite
python demo_test.py
```

You should see:
```
✓ LiquidMetal SDK loaded successfully
✓ All tests passed
```

### 9. Run the Application

```bash
python main.py
```

## File Editing Options

### Option 1: Edit in Windows, Run in WSL

**VS Code with WSL Extension** (Recommended):
1. Install "WSL" extension in VS Code
2. Open VS Code, press `F1`, select "WSL: Open Folder in WSL"
3. Navigate to `~/self-evolve`
4. Edit files in VS Code, run in WSL terminal

### Option 2: Edit in WSL

Use terminal editors:
```bash
# Nano (easier for beginners)
nano filename.py

# Vim (more powerful)
vim filename.py
```

### Option 3: Access WSL files from Windows

WSL files are accessible at:
```
\\wsl$\Ubuntu\home\alext\self-evolve
```

Open in File Explorer or VS Code.

## Common Issues & Solutions

### "Permission denied" errors
```bash
# Make Python files executable
chmod +x main.py demo_test.py

# Or run with python explicitly
python main.py
```

### "Module not found" errors
```bash
# Make sure venv is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### "LiquidMetal SDK not found"
```bash
# Check if installed
pip list | grep liquidmetal

# Reinstall if needed
pip install liquidmetal
```

### Slow performance
If you're running from `/mnt/c/` (Windows filesystem):
```bash
# Copy to WSL native filesystem
cp -r /mnt/c/Users/alext/Desktop/self-evolve ~/self-evolve
cd ~/self-evolve
```

### Line ending issues
```bash
# If you see ^M characters or weird errors
dos2unix *.py
dos2unix **/*.py
```

### Can't find .env file
```bash
# Check it exists
ls -la .env

# If not, copy from example
cp .env.example .env
nano .env  # Edit and add your keys
```

## Development Workflow

### Recommended Setup:

1. **Code in VS Code** (with WSL extension)
2. **Run in WSL terminal**
3. **Git from WSL** (better compatibility)

```bash
# Configure git in WSL
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# Check status
git status

# Commit changes
git add .
git commit -m "Your message"
```

## File Paths in WSL vs Windows

| Windows | WSL |
|---------|-----|
| `C:\Users\alext\Desktop\self-evolve` | `/mnt/c/Users/alext/Desktop/self-evolve` |
| WSL Home | `\\wsl$\Ubuntu\home\alext` |
| WSL Project | `\\wsl$\Ubuntu\home\alext\self-evolve` |

## Performance Tips

1. **Use WSL filesystem** (`~/`) not Windows (`/mnt/c/`) for best performance
2. **Install VS Code WSL extension** for seamless editing
3. **Run all Python commands in WSL**, not Windows
4. **Store data in WSL** - `/data/` will be faster

## Testing Your Setup

Run this quick test:
```bash
# Activate venv
source venv/bin/activate

# Test Python
python -c "import sys; print(sys.platform)"
# Should output: linux

# Test imports
python -c "import liquidmetal; print('LiquidMetal OK')"
python -c "import daft; print('Daft OK')"
python -c "import rich; print('Rich OK')"

# Run full test
python demo_test.py
```

## Switching Between Windows and WSL

You can run in both environments:

**Windows**:
```cmd
cd C:\Users\alext\Desktop\self-evolve
.venv\Scripts\activate
python main.py
```

**WSL**:
```bash
cd ~/self-evolve
source venv/bin/activate
python main.py
```

**Important**: Keep separate virtual environments (`.venv` for Windows, `venv` for WSL).

## Deactivating WSL

When done working:
```bash
# Deactivate virtual environment
deactivate

# Exit WSL
exit
```

## Further Help

- **WSL Docs**: https://learn.microsoft.com/en-us/windows/wsl/
- **VS Code + WSL**: https://code.visualstudio.com/docs/remote/wsl
- **WSL Commands**: https://learn.microsoft.com/en-us/windows/wsl/basic-commands

## Quick Reference

```bash
# Start WSL
wsl

# Navigate to project (if in WSL filesystem)
cd ~/self-evolve

# Activate environment
source venv/bin/activate

# Run app
python main.py

# Run tests
python demo_test.py

# Deactivate
deactivate

# Exit WSL
exit
```

Your code is 100% compatible with WSL - no modifications needed!
