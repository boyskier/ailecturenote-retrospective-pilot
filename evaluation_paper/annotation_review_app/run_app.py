"""
CLI launcher helper for the annotation-review Streamlit application.
"""

import sys
import subprocess
from pathlib import Path

def main():
    app_dir = Path(__file__).resolve().parent
    app_file = app_dir / "app.py"
    
    # Check if streamlit is installed
    try:
        import streamlit
    except ImportError:
        print("Error: 'streamlit' is not installed in the current environment.")
        print("Please install requirements first:")
        print(f"  pip install -r {app_dir / 'requirements.txt'}")
        sys.exit(1)
        
    cmd = [sys.executable, "-m", "streamlit", "run", str(app_file)]
    print(f"Launching Streamlit review app: {' '.join(cmd)}")
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\nReview app stopped.")

if __name__ == "__main__":
    main()
