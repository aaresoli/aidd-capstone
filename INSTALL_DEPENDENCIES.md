# Installing Dependencies

## Issue
The app is failing with `ModuleNotFoundError: No module named 'flask_login'` because dependencies are not installed.

## Solution

### Option 1: Install in WSL (Recommended)

Since your project is in WSL (`/Ubuntu/home/aashish/code/capstone`), you should install dependencies using WSL's Python:

1. **Open WSL terminal** (not Windows PowerShell)
2. **Navigate to project directory:**
   ```bash
   cd /home/aashish/code/capstone
   ```

3. **Create virtual environment (if not already created):**
   ```bash
   python3 -m venv venv
   ```

4. **Activate virtual environment:**
   ```bash
   source venv/bin/activate
   ```

5. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

6. **Run the app from WSL:**
   ```bash
   python src/app.py
   ```
   or
   ```bash
   flask run
   ```

### Option 2: Install in Windows Python

If you want to use Windows Python, install dependencies in Windows:

1. **Open PowerShell or Command Prompt**
2. **Navigate to project directory:**
   ```powershell
   cd \\wsl.localhost\Ubuntu\home\aashish\code\capstone
   ```

3. **Create virtual environment:**
   ```powershell
   python -m venv venv
   ```

4. **Activate virtual environment:**
   ```powershell
   venv\Scripts\activate
   ```

5. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```

6. **Run the app:**
   ```powershell
   python src/app.py
   ```

## Verify Installation

After installing, verify the packages are installed:

```bash
pip list | grep -i flask
```

You should see:
- Flask
- Flask-Login
- Flask-WTF

## Troubleshooting

If you still get import errors:
1. Make sure your virtual environment is activated
2. Verify you're using the correct Python interpreter
3. Try reinstalling: `pip install --upgrade -r requirements.txt`

