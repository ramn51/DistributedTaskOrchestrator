import sys
import os
import time

def main():
    # 1. DEBUG: Prove we are in the correct shared folder
    current_dir = os.getcwd()
    print(f"[DEBUG] Python executing in: {current_dir}")

    # 2. SIMULATION: Create files for the Merge job

    # Create Logic
    with open("logic.py", "w") as f:
        f.write("# Logic Module\nclass Game:\n    def start(self): print('Started')")
    print("[OK] Created logic.py")  # <--- Changed from ✅

    # Create UI
    with open("ui.py", "w") as f:
        f.write("# UI Module\ndef draw(): print('Drawing...')")
    print("[OK] Created ui.py")     # <--- Changed from ✅

    # Create main.java.titan.Main (The output of Merge)
    with open("main.py", "w") as f:
        f.write("import logic\nimport ui\nprint('Merged App')")
    print("[OK] Created main.py")   # <--- Changed from ✅

if __name__ == "__main__":
    main()