import os
import shutil
import hashlib
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk # Import ttk for themed widgets like Progressbar
from datetime import datetime

# --- Configuration ---
# You can change these default folder names if you like
DUPLICATES_FOLDER_NAME = "duplicates"
NO_EXTENSION_FOLDER_NAME = "_no_extension_" # For files without a discernible extension
HIDDEN_OR_CONFIG_FOLDER_NAME = "_hidden_or_config_" # For files like .bashrc (starting with a dot, no extension after)

# --- File Type Grouping ---
# Define major categories and the extensions that belong to them
FILE_TYPE_GROUPS = {
    "images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp", ".ico", ".svg"],
    "documents": [".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".ppt", ".pptx", ".xls", ".xlsx", ".csv", ".md", ".json", ".xml"],
    "audio": [".mp3", ".wav", ".aac", ".flac", ".ogg", ".wma", ".m4a"],
    "video": [".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".webm"],
    "archives": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz"],
    "executables": [".exe", ".msi", ".dmg", ".app", ".bat", ".sh"],
    "code": [".py", ".js", ".html", ".css", ".java", ".c", ".cpp", ".h", ".cs", ".php", ".rb", ".go", ".swift", ".kt", ".ts", ".jsx", ".tsx", ".vue", ".json", ".xml", ".yml", ".yaml", ".toml", ".ini", ".cfg"],
}

def get_grouped_folder_name(file_extension):
    """
    Returns a grouped folder name (e.g., "images", "documents") based on the file extension.
    If no group is found, returns the extension without the leading dot.
    """
    normalized_ext = file_extension.lower()
    for group_name, extensions in FILE_TYPE_GROUPS.items():
        if normalized_ext in extensions:
            return group_name

    # If no group matches, use the extension itself (without the dot)
    return normalized_ext[1:] if normalized_ext.startswith('.') else normalized_ext

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
        return None
    except Exception as e:
        return None

def create_directory_if_not_exists(dir_path, error_messages):
    """
    Creates a directory if it doesn't already exist.
    Records errors in the error_messages list.
    """
    if not os.path.exists(dir_path):
        try:
            os.makedirs(dir_path)
            # print(f"Created directory: {dir_path.encode('utf-8', errors='replace').decode('utf-8')}")
        except OSError as e:
            error_messages.append(f"Error creating directory {dir_path.encode('utf-8', errors='replace').decode('utf-8')}: {e}")
            return False
    return True

def copy_file_with_feedback(source_path, destination_path, file_name, error_messages):
    """
    Copies a file and prints feedback.
    Handles potential overwrites by renaming if a file with the same name exists at the destination.
    Records errors in the error_messages list.
    """
    # Construct the full path for the potential new file
    potential_new_file_path = os.path.join(destination_path, file_name)
    final_destination_file_path = potential_new_file_path

    # Check if a file with the same name already exists in the destination
    if os.path.exists(potential_new_file_path):
        base, ext = os.path.splitext(file_name)
        counter = 1
        # Keep trying new names until an unused one is found
        while os.path.exists(os.path.join(destination_path, f"{base}_copy{counter}{ext}")):
            counter += 1
        new_file_name = f"{base}_copy{counter}{ext}"
        final_destination_file_path = os.path.join(destination_path, new_file_name)
        # print(f"Warning: File '{file_name.encode('utf-8', errors='replace').decode('utf-8')}' already exists in '{destination_path.encode('utf-8', errors='replace').decode('utf-8')}'. Renaming to '{new_file_name.encode('utf-8', errors='replace').decode('utf-8')}'.")

    try:
        shutil.copy2(source_path, final_destination_file_path) # Use copy2 to preserve metadata
        # print(f"Copied: '{os.path.basename(source_path).encode('utf-8', errors='replace').decode('utf-8')}' from '{os.path.dirname(source_path).encode('utf-8', errors='replace').decode('utf-8')}' to '{destination_path.encode('utf-8', errors='replace').decode('utf-8')}' as '{os.path.basename(final_destination_file_path).encode('utf-8', errors='replace').decode('utf-8')}'")
        return final_destination_file_path # Return the actual path it was copied to
    except Exception as e:
        error_messages.append(f"Error copying file '{os.path.basename(source_path).encode('utf-8', errors='replace').decode('utf-8')}' to '{destination_path.encode('utf-8', errors='replace').decode('utf-8')}': {e}")
        return None


# --- Main Logic ---

def count_files_in_folder(target_folder_path):
    """
    Counts the total number of files in the target folder and its subdirectories.
    Used for setting the maximum value of the progress bar.
    """
    count = 0
    for dirpath, dirnames, filenames in os.walk(target_folder_path):
        # Exclude organizational folders from the count if they exist in the source
        folders_to_exclude = [DUPLICATES_FOLDER_NAME, NO_EXTENSION_FOLDER_NAME, HIDDEN_OR_CONFIG_FOLDER_NAME] + \
                             list(FILE_TYPE_GROUPS.keys()) # Exclude potential existing grouped folders

        dirnames[:] = [d for d in dirnames if d not in folders_to_exclude]

        for item_name in filenames:
            item_path = os.path.join(dirpath, item_name)
            # Also exclude the new output folder if it happens to be within the scanned path
            # This check is more robust for the actual organization, but a simpler count is fine here.
            count += 1
    return count


def organize_files_in_folder(target_folder_path, progress_bar, status_label, total_files_to_process):
    """
    Organizes files in the specified folder and its subfolders by type and handles duplicates.
    All organized files and duplicates are COPIED to subfolders directly under a new timestamped output folder.
    Includes progress bar updates.
    """
    error_messages = []
    processed_files_count = 0
    copied_files_count = 0
    duplicate_files_count = 0

    if not os.path.isdir(target_folder_path):
        error_messages.append(f"The path '{target_folder_path.encode('utf-8', errors='replace').decode('utf-8')}' is not a valid directory.")
        return processed_files_count, copied_files_count, duplicate_files_count, error_messages, ""

    # --- 1. Setup New Output Folder ---
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    original_folder_name = os.path.basename(target_folder_path)
    parent_dir = os.path.dirname(target_folder_path)

    root_output_folder_name = f"file_organizer_{original_folder_name}_{timestamp}"
    root_output_folder_path = os.path.join(parent_dir, root_output_folder_name)

    if not create_directory_if_not_exists(root_output_folder_path, error_messages):
        return processed_files_count, copied_files_count, duplicate_files_count, error_messages, ""

    # Create the main "duplicates" folder within the new root output folder
    duplicates_main_folder_path = os.path.join(root_output_folder_path, DUPLICATES_FOLDER_NAME)
    if not create_directory_if_not_exists(duplicates_main_folder_path, error_messages):
        return processed_files_count, copied_files_count, duplicate_files_count, error_messages, ""

    # This dictionary will store file hashes to detect duplicates.
    # Key: file_hash, Value: path of the first encountered (original) file in the new output folder
    known_file_hashes = {}

    # This dictionary will store file type group names and their corresponding folder paths
    # Key: group_name (e.g., "images"), Value: path to the type folder (e.g., "/path/to/output/images")
    type_folders_cache = {}

    # Set progress bar maximum
    progress_bar['maximum'] = total_files_to_process
    current_file_index = 0

    # print(f"\nStarting recursive file organization in: {target_folder_path.encode('utf-8', errors='replace').decode('utf-8')}")
    # print(f"Output will be generated in: {root_output_folder_path.encode('utf-8', errors='replace').decode('utf-8')}")
    # print("--------------------------------------------------")

    # --- 2. Iterate through files in the target directory and its subdirectories ---
    for dirpath, dirnames, filenames in os.walk(target_folder_path):
        # IMPORTANT: Prune dirnames in-place to prevent os.walk from descending into
        # our organizational folders or the duplicates folder if they somehow exist in the source.
        # Also, exclude the new output folder itself if it's created within the source tree.
        folders_to_exclude = [DUPLICATES_FOLDER_NAME, NO_EXTENSION_FOLDER_NAME, HIDDEN_OR_CONFIG_FOLDER_NAME, root_output_folder_name] + \
                             list(type_folders_cache.keys()) # Add names of created type folders

        dirnames[:] = [d for d in dirnames if d not in folders_to_exclude]

        # print(f"\nScanning directory: {dirpath.encode('utf-8', errors='replace').decode('utf-8')}")

        for item_name in filenames:
            item_path = os.path.join(dirpath, item_name)

            # Update progress bar and status label
            current_file_index += 1
            progress_bar['value'] = current_file_index
            status_label.config(text=f"Processing: {item_name.encode('utf-8', errors='replace').decode('utf-8')}")
            progress_bar.master.update_idletasks() # Update the progress window
            progress_bar.master.update() # Process events

            # Skip if the file is already in one of our organizational folders (e.g., if re-running on an already organized folder)
            if item_path.startswith(duplicates_main_folder_path) or \
               any(item_path.startswith(folder_path) for folder_path in type_folders_cache.values()) or \
               item_path.startswith(root_output_folder_path): # Also skip if it's in the new output folder
                # print(f"Skipping file: '{item_name.encode('utf-8', errors='replace').decode('utf-8')}' (already in an organizational folder or new output folder).")
                continue

            processed_files_count += 1
            # print(f"Processing file: {item_name.encode('utf-8', errors='replace').decode('utf-8')} (from {dirpath.encode('utf-8', errors='replace').decode('utf-8')})")

            # --- 3. Handle Duplicates ---
            file_hash = calculate_file_hash(item_path)
            if file_hash is None: # Hash calculation failed (e.g., file disappeared)
                error_messages.append(f"Could not calculate hash for '{item_name.encode('utf-8', errors='replace').decode('utf-8')}' in '{dirpath.encode('utf-8', errors='replace').decode('utf-8')}'. Skipping.")
                continue

            if file_hash in known_file_hashes:
                # This file is a duplicate of a previously processed file.
                # original_file_path = known_file_hashes[file_hash]
                # print(f"Duplicate found: '{item_name.encode('utf-8', errors='replace').decode('utf-8')}' is a duplicate of '{os.path.basename(original_file_path).encode('utf-8', errors='replace').decode('utf-8')}'.")

                if copy_file_with_feedback(item_path, duplicates_main_folder_path, item_name, error_messages):
                    duplicate_files_count += 1
                continue # Move to the next file

            # --- 4. Process Original File: Categorize and Copy ---
            # This is the first time we've seen this file content.
            file_name_proper, file_extension = os.path.splitext(item_name)
            file_extension = file_extension.lower() # Normalize to lowercase

            if not file_extension:
                # File has no extension
                type_folder_name = NO_EXTENSION_FOLDER_NAME
                # print(f"File '{item_name.encode('utf-8', errors='replace').decode('utf-8')}' has no extension.")
            else:
                # Use the grouped name or the extension itself (without the dot) as the folder name
                type_folder_name = get_grouped_folder_name(file_extension)
                if not type_folder_name: # Handles cases like ".bashrc" where splitext might give ".bashrc" as ext
                    type_folder_name = HIDDEN_OR_CONFIG_FOLDER_NAME

            # Get or create the specific type folder path within the new root output folder
            if type_folder_name not in type_folders_cache:
                specific_type_folder_path = os.path.join(root_output_folder_path, type_folder_name)
                if not create_directory_if_not_exists(specific_type_folder_path, error_messages):
                    error_messages.append(f"Skipping file {item_name.encode('utf-8', errors='replace').decode('utf-8')} as its type folder '{specific_type_folder_path.encode('utf-8', errors='replace').decode('utf-8')}' could not be created.")
                    continue # Skip this file if its type folder can't be made
                type_folders_cache[type_folder_name] = specific_type_folder_path
            else:
                specific_type_folder_path = type_folders_cache[type_folder_name]

            # Copy the original file to its type folder
            moved_file_path = copy_file_with_feedback(item_path, specific_type_folder_path, item_name, error_messages)

            if moved_file_path:
                # If successfully copied, record its hash and new path
                known_file_hashes[file_hash] = moved_file_path
                copied_files_count += 1
            else:
                error_messages.append(f"Failed to copy '{item_name.encode('utf-8', errors='replace').decode('utf-8')}', it will not be recorded as an original for duplicate checking.")

    # print("\n--------------------------------------------------")
    # print("File organization process complete.")

    return processed_files_count, copied_files_count, duplicate_files_count, error_messages, root_output_folder_path

# --- GUI for folder selection ---
def select_folder_and_run():
    """
    Opens a dialog to select a folder and then runs the organization script.
    """
    root = tk.Tk()
    root.withdraw() # Hide the main Tkinter window

    folder_selected = filedialog.askdirectory(title="Select Folder to Organize (and its subfolders)")

    if folder_selected: # If a folder was selected
        # Confirmation dialog
        confirm = messagebox.askyesno(
            "Confirm Organization",
            f"Are you sure you want to organize files from:\n{folder_selected.encode('utf-8', errors='replace').decode('utf-8')}\n\n"
            "This will recursively COPY files from this folder and all its subfolders "
            "into type-based subfolders (e.g., 'images', 'documents', 'pdf', 'jpg') and "
            "move duplicates to a 'duplicates' folder.\n\n"
            "A NEW output folder will be created in the parent directory of "
            "'{os.path.basename(folder_selected).encode('utf-8', errors='replace').decode('utf-8')}' "
            "to contain all organized files.\n\n"
            "It's highly recommended to BACK UP YOUR FILES before proceeding."
        )
        if confirm:
            # --- Pre-scan to count files for progress bar ---
            total_files = count_files_in_folder(folder_selected)
            if total_files == 0:
                messagebox.showinfo("No Files Found", "No files found in the selected folder or its subfolders to organize.")
                return

            # --- Create Progress Window ---
            progress_window = tk.Toplevel(root)
            progress_window.title("Organizing Files...")
            progress_window.geometry("400x100")
            progress_window.resizable(False, False)
            progress_window.protocol("WM_DELETE_WINDOW", lambda: None) # Disable close button

            # Center the progress window
            root.update_idletasks() # Ensure window dimensions are calculated
            x = root.winfo_x() + (root.winfo_width() // 2) - (progress_window.winfo_width() // 2)
            y = root.winfo_y() + (root.winfo_height() // 2) - (progress_window.winfo_height() // 2)
            progress_window.geometry(f"+{x}+{y}")

            # Progress Label
            status_label = tk.Label(progress_window, text="Preparing...", pady=10)
            status_label.pack()

            # Progress Bar
            progress_bar = ttk.Progressbar(progress_window, orient="horizontal", length=300, mode="determinate")
            progress_bar.pack(pady=5)

            # Start the organization process
            processed, copied, duplicates, errors, output_path = organize_files_in_folder(
                folder_selected, progress_bar, status_label, total_files
            )

            # Close the progress window after completion
            progress_window.destroy()

            summary_message = f"File organization process complete!\n\n" \
                              f"Original folder scanned: {folder_selected.encode('utf-8', errors='replace').decode('utf-8')}\n" \
                              f"Output generated in: {output_path.encode('utf-8', errors='replace').decode('utf-8')}\n\n" \
                              f"Total files processed: {processed}\n" \
                              f"Files copied to type folders: {copied}\n" \
                              f"Duplicate files copied to '{DUPLICATES_FOLDER_NAME}': {duplicates}\n\n"

            if errors:
                summary_message += f"Errors encountered during process ({len(errors)}):\n"
                for i, error in enumerate(errors):
                    summary_message += f"- {error}\n"
                messagebox.showerror("Organization Complete with Errors", summary_message)
            else:
                messagebox.showinfo("Organization Complete", summary_message)
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
        #         processed, copied, duplicates, errors, output_path = organize_files_in_folder(
        #             folder_path_arg, None, None, count_files_in_folder(folder_path_arg) # Pass None for GUI elements
        #         )
        #         print(f"\n--- Organization Summary for {folder_path_arg} ---")
        #         print(f"Output generated in: {output_path}")
        #         print(f"Total files processed: {processed}")
        #         print(f"Files copied to type folders: {copied}")
        #         print(f"Duplicate files copied: {duplicates}")
        #         if errors:
        #             print("\nErrors encountered:")
        #             for error in errors:
        #                 print(f"- {error}")
        #     else:
        #         print(f"Error: Provided path '{folder_path_arg}' is not a valid directory.")
        # else:
        #     print("Usage: python script_name.py /path/to/your/folder")
