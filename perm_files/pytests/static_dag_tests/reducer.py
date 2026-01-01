import sys
import os

if __name__ == "__main__":
    output_file = sys.argv[1]
    input_files = sys.argv[2:]

    # FIX: Resolve paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(base_dir, output_file)

    grand_total = 0
    print(f"[REDUCER] Aggregating inputs in: {base_dir}")

    for fname in input_files:
        fpath = os.path.join(base_dir, fname)
        try:
            with open(fpath, 'r') as f:
                val = int(f.read().strip())
                print(f"   + Read {val} from {fname}")
                grand_total += val
        except FileNotFoundError:
             print(f"[ERROR] Missing mapper output: {fpath}")

    with open(output_path, 'w') as f:
        f.write(f"FINAL RESULT: {grand_total}")

    print(f"[REDUCER] Grand Total calculated: {grand_total}")