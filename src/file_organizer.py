import os
import shutil
import hashlib
import tkinter as tk
from tkinter import filedialog, messagebox

# --- Configuration ---
# You can change these default folder names if you like
DUPLICATES_FOLDER_NAME = "duplicates"
NO_EXTENSION_FOLDER_NAME = "_no_extension_" # For files without a discernible extension

# --- Helper Functions ---

def calculate_file_hash(file_path, block_size=65536):
    """
    Calculates the SHA256 hash of a file.
    This is used to identify duplicate files based on their content.
    """
    sha256 = hashlib.sha256()
    try:
        with open(file_path, 'rb') as f:
            for block in iter(lambda: f.read(block_size), b''):
                sha256.update(block)
        return sha256.hexdigest()
    except IOError:
        # Could occur if the file is inaccessible or deleted during processing
        print(f"Warning: Could not read file {file_path} to calculate hash.")
        return None

def create_directory_if_not_exists(dir_path):
    """
    Creates a directory if it doesn't already exist.
    """
    if not os.path.exists(dir_path):
        try:
            os.makedirs(dir_path)
            print(f"Created directory: {dir_path}")
        except OSError as e:
            print(f"Error creating directory {dir_path}: {e}")
            return False
    return True

def move_file_with_feedback(source_path, destination_path, file_name):
    """
    Moves a file and prints feedback.
    Handles potential overwrites by renaming if a file with the same name exists at the destination.
    """
    final_destination_path = destination_path
    # Check if a file with the same name already exists in the destination
    if os.path.exists(os.path.join(destination_path, file_name)):
        base, ext = os.path.splitext(file_name)
        counter = 1
        # Keep trying new names until an unused one is found
        while os.path.exists(os.path.join(destination_path, f"{base}_copy{counter}{ext}")):
            counter += 1
        new_file_name = f"{base}_copy{counter}{ext}"
        final_destination_path_for_file = os.path.join(destination_path, new_file_name)
        print(f"Warning: File '{file_name}' already exists in '{destination_path}'. Renaming to '{new_file_name}'.")
    else:
        final_destination_path_for_file = os.path.join(destination_path, file_name)

    try:
        shutil.move(source_path, final_destination_path_for_file)
        print(f"Moved: '{file_name}' to '{destination_path}'")
        return final_destination_path_for_file # Return the actual path it was moved to
    except Exception as e:
        print(f"Error moving file {file_name} to {destination_path}: {e}")
        return None


# --- Main Logic ---

def organize_files_in_folder(target_folder_path):
    """
    Organizes files in the specified folder by type and handles duplicates.
    """
    if not os.path.isdir(target_folder_path):
        messagebox.showerror("Error", f"The path '{target_folder_path}' is not a valid directory.")
        return

    # --- 1. Setup ---
    # Create the main "duplicates" folder if it doesn't exist
    duplicates_main_folder_path = os.path.join(target_folder_path, DUPLICATES_FOLDER_NAME)
    if not create_directory_if_not_exists(duplicates_main_folder_path):
        messagebox.showerror("Error", f"Could not create duplicates folder at: {duplicates_main_folder_path}")
        return # Stop if we can't create this essential folder

    # This dictionary will store file hashes to detect duplicates.
    # Key: file_hash, Value: path of the first encountered (original) file
    known_file_hashes = {}

    # This dictionary will store file extensions and their corresponding folder paths
    # Key: extension (e.g., ".txt"), Value: path to the type folder
    type_folders = {}

    print(f"\nStarting file organization in: {target_folder_path}")
    print("--------------------------------------------------")

    # --- 2. Iterate through files in the target directory ---
    # We use os.listdir() and then filter. We must be careful not to process files
    # in the type folders or duplicates folder we are creating.
    for item_name in os.listdir(target_folder_path):
        item_path = os.path.join(target_folder_path, item_name)

        # Skip if it's a directory (including our own organizational folders)
        if os.path.isdir(item_path):
            # Make sure we don't try to process our own created folders
            if item_name == DUPLICATES_FOLDER_NAME or item_name == NO_EXTENSION_FOLDER_NAME or \
               any(item_path == folder_path for folder_path in type_folders.values()):
                print(f"Skipping directory: {item_name} (organizational folder)")
            else:
                print(f"Skipping directory: {item_name}")
            continue

        # It's a file, let's process it
        print(f"\nProcessing file: {item_name}")

        # --- 3. Handle Duplicates ---
        file_hash = calculate_file_hash(item_path)
        if file_hash is None: # Hash calculation failed
            print(f"Skipping file {item_name} due to hash calculation error.")
            continue

        if file_hash in known_file_hashes:
            # This file is a duplicate of a previously processed file.
            original_file_path = known_file_hashes[file_hash]
            print(f"Duplicate found: '{item_name}' is a duplicate of '{os.path.basename(original_file_path)}'.")
            move_file_with_feedback(item_path, duplicates_main_folder_path, item_name)
            continue # Move to the next file

        # --- 4. Process Original File: Categorize and Move ---
        # This is the first time we've seen this file content.
        file_name_proper, file_extension = os.path.splitext(item_name)
        file_extension = file_extension.lower() # Normalize to lowercase

        if not file_extension:
            # File has no extension
            type_folder_name = NO_EXTENSION_FOLDER_NAME
            print(f"File '{item_name}' has no extension.")
        else:
            # Use the extension (without the dot) as the folder name
            type_folder_name = file_extension[1:] # e.g., "txt", "jpg"
            if not type_folder_name: # Handles cases like ".bashrc" where splitext might give ".bashrc" as ext
                type_folder_name = "_hidden_or_config_" # or some other generic name

        # Get or create the specific type folder path
        if type_folder_name not in type_folders:
            specific_type_folder_path = os.path.join(target_folder_path, type_folder_name)
            if not create_directory_if_not_exists(specific_type_folder_path):
                print(f"Skipping file {item_name} as its type folder '{specific_type_folder_path}' could not be created.")
                continue # Skip this file if its type folder can't be made
            type_folders[type_folder_name] = specific_type_folder_path
        else:
            specific_type_folder_path = type_folders[type_folder_name]

        # Move the original file to its type folder
        moved_file_path = move_file_with_feedback(item_path, specific_type_folder_path, item_name)

        if moved_file_path:
            # If successfully moved, record its hash and new path
            known_file_hashes[file_hash] = moved_file_path
        else:
            print(f"Failed to move '{item_name}', it will not be recorded as an original for duplicate checking.")


    print("\n--------------------------------------------------")
    print("File organization process complete.")
    messagebox.showinfo("Success", "File organization process complete!")

# --- GUI for folder selection ---
def select_folder_and_run():
    """
    Opens a dialog to select a folder and then runs the organization script.
    """
    root = tk.Tk()
    root.withdraw() # Hide the main Tkinter window

    folder_selected = filedialog.askdirectory(title="Select Folder to Organize")

    if folder_selected: # If a folder was selected
        # Confirmation dialog
        confirm = messagebox.askyesno(
            "Confirm Organization",
            f"Are you sure you want to organize files in:\n{folder_selected}\n\n"
            "This will move files into subfolders based on their type and move duplicates to a 'duplicates' folder.\n"
            "It's recommended to BACK UP YOUR FILES before proceeding."
        )
        if confirm:
            organize_files_in_folder(folder_selected)
        else:
            messagebox.showinfo("Cancelled", "File organization cancelled by user.")
    else:
        messagebox.showinfo("Cancelled", "No folder selected. File organization cancelled.")

# --- Main execution ---
if __name__ == "__main__":
    # Check if running in a terminal or with GUI capabilities
    # This is a simple check; more robust checks might be needed for all environments
    if 'DISPLAY' in os.environ or os.name == 'nt': # Basic check for GUI environment
        select_folder_and_run()
    else:
        # Fallback for non-GUI environments (e.g., running via SSH without X forwarding)
        print("No GUI detected. Please run this script in an environment that supports Tkinter,")
        print("or modify the script to accept the folder path as a command-line argument.")
        # Example of how you might take a command-line argument:
        # import sys
        # if len(sys.argv) > 1:
        #     folder_path_arg = sys.argv[1]
        #     if os.path.isdir(folder_path_arg):
        #         organize_files_in_folder(folder_path_arg)
        #     else:
        #         print(f"Error: Provided path '{folder_path_arg}' is not a valid directory.")
        # else:
        #     print("Usage: python script_name.py /path/to/your/folder")

