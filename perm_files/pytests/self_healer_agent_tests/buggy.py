# perm_files/buggy_math.py
import sys

def calculate_stats(numbers):
    # BUG: This crashes if the list is empty (ZeroDivisionError)
    avg = sum(numbers) / len(numbers)
    return avg

if __name__ == "__main__":
    data = [] # Empty list causing the crash
    print(f"Analyzing Data...")
    print(f"Average: {calculate_stats(data)}")