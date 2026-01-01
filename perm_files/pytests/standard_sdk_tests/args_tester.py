import sys

def main():
    print("--- ARGUMENT TEST START ---")

    # sys.argv[0] is always the script name itself
    print(f"Script Name: {sys.argv[0]}")

    # Check if we received args
    if len(sys.argv) > 1:
        print(f"Total Arguments Received: {len(sys.argv) - 1}")

        # Loop through and print each arg with its index
        for i, arg in enumerate(sys.argv[1:], start=1):
            print(f"Arg #{i}: {arg}")
    else:
        print("FAIL: No arguments were passed!")

    print("--- ARGUMENT TEST END ---")

if __name__ == "__main__":
    main()