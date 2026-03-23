import sys                          # Gives access to command-line arguments (e.g. the filename you pass in)
import os                           # Used to check if the file actually exists on disk

def summarize(file_path):
    # Check that the file exists before trying to open it
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found.")
        sys.exit(1)                 # Exit the script with an error code so you know something went wrong

    # Open the file in read mode, using UTF-8 encoding to handle most text files safely
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()             # Read the entire file content into a single string

    # Split the text into individual lines, stripping blank ones
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    # Split the text into words by whitespace so we can count them
    words = text.split()

    # Split the text into sentences using a simple period/exclamation/question mark rule
    import re                       # Regular expressions module — lets us do pattern-based splitting
    sentences = re.split(r'[.!?]+', text)                        # Split on . ! or ?
    sentences = [s.strip() for s in sentences if s.strip()]      # Remove empty/whitespace-only entries

    # Build a summary: take up to the first 5 sentences as a preview
    preview_sentences = sentences[:5]
    preview = ". ".join(preview_sentences) + ("." if preview_sentences else "")

    # Print the summary report
    print("=" * 50)
    print("FILE SUMMARY")
    print("=" * 50)
    print(f"File:       {file_path}")              # Name of the file that was read
    print(f"Lines:      {len(lines)}")             # Total non-blank lines
    print(f"Words:      {len(words)}")             # Total word count
    print(f"Sentences:  {len(sentences)}")         # Estimated sentence count
    print(f"Characters: {len(text)}")              # Total character count including spaces
    print()
    print("--- PREVIEW (first 5 sentences) ---")
    print(preview)                                 # Show the opening lines as a quick preview
    print("=" * 50)

# This block only runs when the script is executed directly (not imported as a module)
if __name__ == "__main__":
    # Expect exactly one argument: the path to the .txt file
    if len(sys.argv) != 2:
        print("Usage: python summarize.py <path_to_file.txt>")
        sys.exit(1)                 # Exit with an error if the user didn't provide a filename

    summarize(sys.argv[1])         # Call the summarize function with the provided file path
