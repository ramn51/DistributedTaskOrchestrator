import sys
import time
import os

if __name__ == "__main__":
    input_file = sys.argv[1]
    output_file = sys.argv[2]

    # FIX: Look for files in the same directory as this script
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(base_dir, input_file)
    output_path = os.path.join(base_dir, output_file)

    print(f"[MAPPER] Processing {input_path} -> {output_path}")
    
    total = 0
    try:
        with open(input_path, 'r') as f:
            for line in f:
                if line.strip():
                    val = int(line.strip())
                    total += val * 2
    except FileNotFoundError:
        print(f"[ERROR] Could not find input file: {input_path}")
        sys.exit(1)
    
    # Simulate work
    time.sleep(1) 
    
    with open(output_path, 'w') as f:
        f.write(str(total))
        
    print(f"[MAPPER] Finished. Result: {total}")