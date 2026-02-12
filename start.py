import os
import sys
import subprocess
import platform

def get_venv_python():
    """Get the path to the virtual environment python executable."""
    venv_dir = "venv"
    if platform.system() == "Windows":
        return os.path.join(venv_dir, "Scripts", "python.exe")
    else:
        return os.path.join(venv_dir, "bin", "python")

def create_venv():
    """Create a virtual environment if it doesn't exist."""
    if not os.path.exists("venv"):
        print("[*] Creating virtual environment...")
        subprocess.check_call([sys.executable, "-m", "venv", "venv"])
    else:
        print("[*] Virtual environment already exists.")

def install_requirements(python_path):
    """Install requirements using the venv python."""
    print("[*] Installing requirements...")
    subprocess.check_call([python_path, "-m", "pip", "install", "--upgrade", "pip"])
    subprocess.check_call([python_path, "-m", "pip", "install", "-r", "requirements.txt"])

def install_playwright(python_path):
    """Install Playwright browsers."""
    print("[*] Installing Playwright browsers...")
    subprocess.check_call([python_path, "-m", "playwright", "install", "chromium"])

def run_main(python_path):
    """Run the main application."""
    print("[*] Starting CCDI Scraper...")
    subprocess.call([python_path, "main.py"])

def main():
    print("=== CCDI Scraper Bootstrapper ===")
    
    # 1. Create Venv
    create_venv()
    
    venv_python = get_venv_python()
    if not os.path.exists(venv_python):
        print(f"[!] Error: Virtual environment python not found at {venv_python}")
        return

    # 2. Install Dependencies
    install_requirements(venv_python)
    
    # 3. Install Playwright
    install_playwright(venv_python)
    
    # 4. Run Main
    run_main(venv_python)

if __name__ == "__main__":
    main()
