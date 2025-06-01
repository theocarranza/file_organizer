import os
import shutil
import hashlib
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from datetime import datetime
import argparse
import tarfile
import configparser

# --- Configuration ---
DUPLICATES_FOLDER_NAME = "duplicates"
NO_EXTENSION_FOLDER_NAME = "_no_extension_"
HIDDEN_OR_CONFIG_FOLDER_NAME = "_hidden_or_config_"
OTHER_FOLDER_NAME = "other"

# Global flag for verbose mode, set by command-line arguments
VERBOSE_MODE = False

# Configuration file for remembering last paths
CONFIG_FILE_NAME = ".file_organizer_config.ini"
CONFIG_SECTION = "Paths"
CONFIG_SOURCE_KEY = "last_source_folder"
CONFIG_DEST_KEY = "last_destination_folder"

# --- File Type Grouping ---
FILE_TYPE_GROUPS = {
    "images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp", ".ico", ".svg"],
    "documents": [".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".ppt", ".pptx", ".xls", ".xlsx", ".csv", ".md", ".json", ".xml"],
    "audio": [".mp3", ".wav", ".aac", ".flac", ".ogg", ".wma", ".m4a"],
    "video": [".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".webm"],
    "archives": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz"],
    "executables": [".exe", ".msi", ".dmg", ".app", ".bat", ".sh"],
    "code": [".py", ".js", ".html", ".css", ".java", ".c", ".cpp", ".h", ".cs", ".php", ".rb", ".go", ".swift", ".kt", ".ts", ".jsx", ".tsx", ".vue", ".json", ".xml", ".yml", ".yaml", ".toml", ".ini", ".cfg"],
}

# --- Config Management Functions ---
def get_config_file_path():
    """Returns the full path to the configuration file in the user's home directory."""
    return os.path.join(os.path.expanduser("~"), CONFIG_FILE_NAME)

def load_last_paths():
    """Loads the last used source and destination paths from the config file."""
    config = configparser.ConfigParser()
    config_file_path = get_config_file_path()

    if os.path.exists(config_file_path):
        try:
            config.read(config_file_path)
            source_path = config.get(CONFIG_SECTION, CONFIG_SOURCE_KEY, fallback=None)
            dest_path = config.get(CONFIG_SECTION, CONFIG_DEST_KEY, fallback=None)

            # Validate if paths still exist
            if source_path and not os.path.isdir(source_path):
                source_path = None
            if dest_path and not os.path.isdir(dest_path):
                dest_path = None

            return source_path, dest_path
        except configparser.Error as e:
            if VERBOSE_MODE:
                print(f"Error reading config file {config_file_path}: {e}")
            return None, None
    return None, None

def save_last_paths(source_path, dest_path):
    """Saves the last used source and destination paths to the config file."""
    config = configparser.ConfigParser()
    config_file_path = get_config_file_path()

    # Read existing config to preserve other sections if any
    if os.path.exists(config_file_path):
        config.read(config_file_path)

    if CONFIG_SECTION not in config:
        config[CONFIG_SECTION] = {}

    config[CONFIG_SECTION][CONFIG_SOURCE_KEY] = source_path
    config[CONFIG_SECTION][CONFIG_DEST_KEY] = dest_path

    try:
        with open(config_file_path, 'w') as configfile:
            config.write(configfile)
        if VERBOSE_MODE:
            print(f"Saved last paths to config: {source_path.encode('utf-8', errors='replace').decode('utf-8')}, {dest_path.encode('utf-8', errors='replace').decode('utf-8')}")
    except IOError as e:
        if VERBOSE_MODE:
            print(f"Error writing config file {config_file_path}: {e}")
    except Exception as e:
        if VERBOSE_MODE:
            print(f"Unexpected error saving config file {config_file_path}: {e}")

# --- File Type Grouping ---

def get_categorized_paths(file_extension, file_name_proper):
    """
    Returns a tuple (top_level_folder_name, sub_folder_name) for a given file extension.
    This function now also takes file_name_proper to correctly identify hidden/config files.
    """
    normalized_ext = file_extension.lower()

    if VERBOSE_MODE:
        print(f"  Attempting to categorize extension: '{normalized_ext.encode('utf-8', errors='replace').decode('utf-8')}' (Original file_name_proper: '{file_name_proper.encode('utf-8', errors='replace').decode('utf-8')}')")

    # Case 1: No extension (e.g., "README", "my_script_without_ext")
    if not normalized_ext:
        if VERBOSE_MODE:
            print(f"    -> No extension. Categorized as: {OTHER_FOLDER_NAME}/{NO_EXTENSION_FOLDER_NAME}")
        return OTHER_FOLDER_NAME, NO_EXTENSION_FOLDER_NAME

    # Case 2: Hidden/config file (e.g., ".bashrc", ".profile")
    # This applies when the file name *starts* with a dot AND there is no "proper" file name part before the dot.
    # For example, for ".bashrc", os.path.splitext returns ('', '.bashrc').
    # For "archive.tar.gz", os.path.splitext returns ('archive.tar', '.gz').
    if not file_name_proper and normalized_ext.startswith('.'):
        if VERBOSE_MODE:
            print(f"    -> Hidden/config file. Categorized as: {OTHER_FOLDER_NAME}/{HIDDEN_OR_CONFIG_FOLDER_NAME}")
        return OTHER_FOLDER_NAME, HIDDEN_OR_CONFIG_FOLDER_NAME

    # Case 3: Regular file with extension (e.g., "document.pdf", "image.jpg")
    # At this point, normalized_ext will be something like '.pdf', '.jpg', '.xlsx'
    # We remove the leading dot for the sub_folder_name
    ext_without_dot = normalized_ext[1:]

    for group_name, extensions in FILE_TYPE_GROUPS.items():
        if normalized_ext in extensions: # Check if the full .ext is in our list
            if VERBOSE_MODE:
                print(f"    -> Matched group '{group_name}'. Categorized as: {group_name}/{ext_without_dot}")
            return group_name, ext_without_dot

    # Case 4: Not in any known group, but has an extension (e.g., ".bak", ".xyz")
    if VERBOSE_MODE:
        print(f"    -> No direct group match. Categorized as: {OTHER_FOLDER_NAME}/{ext_without_dot}")
    return OTHER_FOLDER_NAME, ext_without_dot

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
                sha256.update(block) # FIX: Changed sha256.update(sha256) to sha256.update(block)
        return sha256.hexdigest()
    except IOError:
        if VERBOSE_MODE:
            print(f"Warning: Could not read file {file_path.encode('utf-8', errors='replace').decode('utf-8')} to calculate hash.")
        return None
    except Exception as e:
        if VERBOSE_MODE:
            print(f"Error calculating hash for {file_path.encode('utf-8', errors='replace').decode('utf-8')}: {e}")
        return None

def create_directory_if_not_exists(dir_path, error_messages):
    """
    Creates a directory if it doesn't already exist.
    Records errors in the error_messages list.
    """
    if not os.path.exists(dir_path):
        try:
            os.makedirs(dir_path)
            if VERBOSE_MODE:
                print(f"Created directory: {dir_path.encode('utf-8', errors='replace').decode('utf-8')}")
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
        if VERBOSE_MODE:
            print(f"Warning: File '{file_name.encode('utf-8', errors='replace').decode('utf-8')}' already exists in '{destination_path.encode('utf-8', errors='replace').decode('utf-8')}'. Renaming to '{new_file_name.encode('utf-8', errors='replace').decode('utf-8')}'.")

    try:
        shutil.copy2(source_path, final_destination_file_path) # Use copy2 to preserve metadata
        if VERBOSE_MODE:
            print(f"Copied: '{os.path.basename(source_path).encode('utf-8', errors='replace').decode('utf-8')}' from '{os.path.dirname(source_path).encode('utf-8', errors='replace').decode('utf-8')}' to '{destination_path.encode('utf-8', errors='replace').decode('utf-8')}' as '{os.path.basename(final_destination_file_path).encode('utf-8', errors='replace').decode('utf-8')}'")
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
    # Collect all top-level group names for exclusion
    top_level_group_names_for_counting_exclusion = list(FILE_TYPE_GROUPS.keys()) + [DUPLICATES_FOLDER_NAME, OTHER_FOLDER_NAME]

    for dirpath, dirnames, filenames in os.walk(target_folder_path):
        # Prune dirnames to avoid counting files in our own organizational folders
        dirnames[:] = [d for d in dirnames if d not in top_level_group_names_for_counting_exclusion]

        for item_name in filenames:
            count += 1
    return count


def organize_files_in_folder(target_folder_path, destination_root_folder, compress_output_flag, progress_bar=None, status_label=None, total_files_to_process=0):
    """
    Organizes files in the specified folder and its subfolders.
    If compress_output_flag is True, files are added directly to a compressed archive.
    Otherwise, files are COPIED to a new timestamped output folder.
    Includes progress bar updates (if GUI elements are provided).
    """
    error_messages = []
    processed_files_count = 0
    files_added_to_output = 0 # Renamed from copied_files_count for clarity with archiving
    duplicate_files_count = 0

    if not os.path.isdir(target_folder_path):
        error_messages.append(f"The source path '{target_folder_path.encode('utf-8', errors='replace').decode('utf-8')}' is not a valid directory.")
        return processed_files_count, files_added_to_output, duplicate_files_count, error_messages, ""

    if not os.path.isdir(destination_root_folder):
        if not create_directory_if_not_exists(destination_root_folder, error_messages):
            error_messages.append(f"The destination path '{destination_root_folder.encode('utf-8', errors='replace').decode('utf-8')}' is not a valid directory and could not be created.")
            return processed_files_count, files_added_to_output, duplicate_files_count, error_messages, ""

    # --- Setup Output ---
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    original_folder_name = os.path.basename(target_folder_path)

    root_output_folder_path = None # Will be set only if not compressing
    final_output_path = "" # Will be the path to the folder OR archive

    tar = None
    if compress_output_flag:
        archive_name = f"file_organizer_{original_folder_name}_{timestamp}.tar.xz"
        final_output_path = os.path.join(destination_root_folder, archive_name)
        try:
            tar = tarfile.open(final_output_path, 'w:xz') # Open for writing with XZ compression
            if VERBOSE_MODE:
                print(f"Opened archive for direct writing: {final_output_path.encode('utf-8', errors='replace').decode('utf-8')}")
        except Exception as e:
            error_messages.append(f"Error opening archive file '{final_output_path.encode('utf-8', errors='replace').decode('utf-8')}': {e}")
            return processed_files_count, files_added_to_output, duplicate_files_count, error_messages, ""
    else:
        root_output_folder_name = f"file_organizer_{original_folder_name}_{timestamp}"
        root_output_folder_path = os.path.join(destination_root_folder, root_output_folder_name)
        final_output_path = root_output_folder_path # The folder is the final output

        if not create_directory_if_not_exists(root_output_folder_path, error_messages):
            return processed_files_count, files_added_to_output, duplicate_files_count, error_messages, ""

        # Create the main "duplicates" folder within the new root output folder for uncompressed mode
        duplicates_main_folder_path = os.path.join(root_output_folder_path, DUPLICATES_FOLDER_NAME)
        if not create_directory_if_not_exists(duplicates_main_folder_path, error_messages):
            return processed_files_count, files_added_to_output, duplicate_files_count, error_messages, ""

    # This dictionary will store file hashes to detect duplicates.
    # Key: file_hash, Value: path of the first encountered (original) file (either disk path or archive internal path)
    known_file_hashes = {}

    # Set progress bar maximum if GUI elements are available
    if progress_bar and status_label:
        progress_bar['maximum'] = total_files_to_process
        current_file_index = 0
        if VERBOSE_MODE:
            print(f"\nStarting recursive file organization from: {target_folder_path.encode('utf-8', errors='replace').decode('utf-8')}")
            print(f"Output will be generated as: {final_output_path.encode('utf-8', errors='replace').decode('utf-8')}")
            print("--------------------------------------------------")
    elif VERBOSE_MODE:
        print(f"\nStarting recursive file organization from: {target_folder_path.encode('utf-8', errors='replace').decode('utf-8')}")
        print(f"Output will be generated as: {final_output_path.encode('utf-8', errors='replace').decode('utf-8')}")
        print("--------------------------------------------------")

    # --- Iterate through files in the target directory and its subdirectories ---
    for dirpath, dirnames, filenames in os.walk(target_folder_path):
        # Prune dirnames in-place to prevent os.walk from descending into
        # our *own output* organizational folders if they happen to be inside the source tree.
        # This is primarily relevant for uncompressed output.
        if not compress_output_flag and root_output_folder_path: # Only relevant if uncompressed folder is created
             dirnames[:] = [d for d in dirnames if d != os.path.basename(root_output_folder_path) and d != DUPLICATES_FOLDER_NAME]

        if VERBOSE_MODE:
            print(f"\nScanning directory: {dirpath.encode('utf-8', errors='replace').decode('utf-8')}")

        for item_name in filenames:
            item_path = os.path.join(dirpath, item_name)

            # Update progress bar and status label if GUI elements are available
            if progress_bar and status_label:
                current_file_index += 1
                percentage = (current_file_index / total_files_to_process) * 100
                progress_bar['value'] = current_file_index
                # Updated status label to show percentage and current folder/file
                status_label.config(text=f"{percentage:.1f}% - Scanning: {os.path.basename(dirpath).encode('utf-8', errors='replace').decode('utf-8')} (File: {item_name.encode('utf-8', errors='replace').decode('utf-8')})")
                progress_bar.master.update_idletasks()
                progress_bar.master.update()

            # If not compressing, skip files already in the output folder.
            if not compress_output_flag and root_output_folder_path and item_path.startswith(root_output_folder_path):
                if VERBOSE_MODE:
                    print(f"Skipping file: '{item_name.encode('utf-8', errors='replace').decode('utf-8')}' (already in new output folder).")
                continue

            processed_files_count += 1
            if VERBOSE_MODE:
                print(f"Processing file: {item_name.encode('utf-8', errors='replace').decode('utf-8')} (from {dirpath.encode('utf-8', errors='replace').decode('utf-8')})")

            file_hash = calculate_file_hash(item_path)
            if file_hash is None:
                error_messages.append(f"Could not calculate hash for '{item_name.encode('utf-8', errors='replace').decode('utf-8')}' in '{dirpath.encode('utf-8', errors='replace').decode('utf-8')}'. Skipping.")
                if VERBOSE_MODE:
                    print(f"Skipping file {item_name.encode('utf-8', errors='replace').decode('utf-8')} due to hash calculation error.")
                continue

            # --- Handle Duplicates ---
            if file_hash in known_file_hashes:
                if VERBOSE_MODE:
                    original_file_path = known_file_hashes[file_hash]
                    print(f"Duplicate found: '{item_name.encode('utf-8', errors='replace').decode('utf-8')}' is a duplicate of '{os.path.basename(original_file_path).encode('utf-8', errors='replace').decode('utf-8')}'.")

                if compress_output_flag:
                    try:
                        # Add duplicate to archive under a special duplicates path
                        arcname_in_archive = os.path.join(DUPLICATES_FOLDER_NAME, item_name)
                        if VERBOSE_MODE:
                            print(f"  Adding duplicate to archive as: {arcname_in_archive.encode('utf-8', errors='replace').decode('utf-8')}")
                        tar.add(item_path, arcname=arcname_in_archive) # Add directly by path, tarfile handles internal details
                        duplicate_files_count += 1
                    except Exception as e:
                        error_messages.append(f"Error adding duplicate '{item_name.encode('utf-8', errors='replace').decode('utf-8')}' to archive: {e}")
                else:
                    if copy_file_with_feedback(item_path, duplicates_main_folder_path, item_name, error_messages):
                        duplicate_files_count += 1
                continue

            # --- Process Original File: Categorize and Copy/Add to Archive ---
            file_name_proper, file_extension = os.path.splitext(item_name)

            if VERBOSE_MODE:
                print(f"  Extracted file_name_proper: '{file_name_proper.encode('utf-8', errors='replace').decode('utf-8')}', file_extension: '{file_extension.encode('utf-8', errors='replace').decode('utf-8')}'")

            top_level_folder_name, sub_folder_name = get_categorized_paths(file_extension, file_name_proper)

            if compress_output_flag:
                try:
                    # Construct the path inside the archive
                    arcname_in_archive = os.path.join(top_level_folder_name, sub_folder_name, item_name)
                    if VERBOSE_MODE:
                        print(f"  Adding original to archive as: {arcname_in_archive.encode('utf-8', errors='replace').decode('utf-8')}")
                    tar.add(item_path, arcname=arcname_in_archive) # Add directly by path, tarfile handles internal details
                    known_file_hashes[file_hash] = arcname_in_archive # Store archive internal path
                    files_added_to_output += 1
                except Exception as e:
                    error_messages.append(f"Error adding file '{item_name.encode('utf-8', errors='replace').decode('utf-8')}' to archive: {e}")
            else:
                # Normal uncompressed copy process
                current_top_level_path = os.path.join(root_output_folder_path, top_level_folder_name)
                if not create_directory_if_not_exists(current_top_level_path, error_messages):
                    error_messages.append(f"Skipping file {item_name.encode('utf-8', errors='replace').decode('utf-8')} as its top-level category folder '{current_top_level_path.encode('utf-8', errors='replace').decode('utf-8')}' could not be created.")
                    continue

                specific_type_folder_path = os.path.join(current_top_level_path, sub_folder_name)
                if not create_directory_if_not_exists(specific_type_folder_path, error_messages):
                    error_messages.append(f"Skipping file {item_name.encode('utf-8', errors='replace').decode('utf-8')} as its sub-folder '{specific_type_folder_path.encode('utf-8', errors='replace').decode('utf-8')}' could not be created.")
                    continue

                copied_file_actual_path = copy_file_with_feedback(item_path, specific_type_folder_path, item_name, error_messages)

                if copied_file_actual_path:
                    known_file_hashes[file_hash] = copied_file_actual_path
                    files_added_to_output += 1
                else:
                    error_messages.append(f"Failed to copy '{item_name.encode('utf-8', errors='replace').decode('utf-8')}', it will not be recorded as an original for duplicate checking.")

    # Close the tarfile if it was opened
    if tar:
        try:
            tar.close()
            if VERBOSE_MODE:
                print(f"Archive closed: {final_output_path.encode('utf-8', errors='replace').decode('utf-8')}")
        except Exception as e:
            error_messages.append(f"Error closing archive file '{final_output_path.encode('utf-8', errors='replace').decode('utf-8')}': {e}")
            if os.path.exists(final_output_path):
                try:
                    os.remove(final_output_path)
                    error_messages.append(f"Removed incomplete archive due to error: {final_output_path.encode('utf-8', errors='replace').decode('utf-8')}")
                except Exception as clean_e:
                    error_messages.append(f"Failed to remove incomplete archive '{final_output_path.encode('utf-8', errors='replace').decode('utf-8')}': {clean_e}")
            final_output_path = ""

    if compress_output_flag and processed_files_count == 0 and final_output_path and os.path.exists(final_output_path):
        try:
            os.remove(final_output_path)
            if VERBOSE_MODE:
                print(f"Removed empty archive as no files were processed: {final_output_path.encode('utf-8', errors='replace').decode('utf-8')}")
            final_output_path = ""
        except Exception as e:
            error_messages.append(f"Failed to remove empty archive '{final_output_path.encode('utf-8', errors='replace').decode('utf-8')}': {e}")

    if VERBOSE_MODE:
        print("\n--------------------------------------------------")
        print("File organization process complete.")

    return processed_files_count, files_added_to_output, duplicate_files_count, error_messages, final_output_path

# --- Custom Confirmation Dialog ---
class CustomConfirmationDialog(tk.Toplevel):
    def __init__(self, parent, source_folder_path, destination_folder_path):
        super().__init__(parent)
        self.parent = parent
        self.transient(parent)
        self.grab_set()
        self.result = False
        self.compress_output = tk.BooleanVar(self, value=False)

        self.title("Confirm Organization")
        self.resizable(False, True)

        style = ttk.Style()
        style.configure("TLabel", font=("Arial", 10), padding=5)
        style.configure("TButton", font=("Arial", 10, "bold"), padding=8)
        style.configure("Header.TLabel", font=("Arial", 12, "bold"))

        content_frame = ttk.Frame(self, padding=15)
        content_frame.pack(expand=True, fill="both")

        header_label = ttk.Label(content_frame, text="Confirm File Organization", style="Header.TLabel")
        header_label.pack(pady=(0, 10))

        message_text = f"Are you sure you want to organize files from:\n" \
                       f"•  Source: {source_folder_path.encode('utf-8', errors='replace').decode('utf-8')}\n" \
                       f"•  Destination: {destination_folder_path.encode('utf-8', errors='replace').decode('utf-8')}\n\n" \
                       f"This will recursively COPY files from the source folder and all its subfolders.\n" \
                       f"Files will be organized into main categories (e.g., 'images', 'documents') " \
                       f"with subfolders for specific extensions (e.g., 'images/jpg').\n" \
                       f"Less common file types will be grouped under an '{OTHER_FOLDER_NAME}' folder.\n" \
                       f"Duplicates will be handled separately (copied to a '{DUPLICATES_FOLDER_NAME}' category).\n\n" \
                       f"A NEW timestamped output (folder or archive) will be created inside the chosen destination." \
                       f"It's highly recommended to BACK UP YOUR FILES before proceeding."

        message_label = ttk.Label(content_frame, text=message_text, wraplength=500, justify="left")
        message_label.pack(pady=(0, 20), fill="both", expand=True)

        compress_checkbox = ttk.Checkbutton(content_frame, text="Output as compressed .tar.xz archive (saves disk space during process)", variable=self.compress_output)
        compress_checkbox.pack(pady=(5, 15), anchor="w")

        button_frame = ttk.Frame(content_frame)
        button_frame.pack(pady=(10, 0))

        yes_button = ttk.Button(button_frame, text="Yes, Proceed", command=self._on_yes)
        yes_button.pack(side="left", padx=10)

        no_button = ttk.Button(button_frame, text="No, Cancel", command=self._on_no)
        no_button.pack(side="right", padx=10)

        self.protocol("WM_DELETE_WINDOW", self._on_no)

        self.update_idletasks()
        width = self.winfo_reqwidth()
        height = self.winfo_reqheight()

        width = max(width + 30, 550)
        height = max(height + 30, 350)

        x = self.parent.winfo_x() + (self.parent.winfo_width() // 2) - (width // 2)
        y = self.parent.winfo_y() + (self.parent.winfo_height() // 2) - (height // 2)
        self.geometry(f"+{x}+{y}")

        self.lift()
        self.attributes('-topmost', True)
        self.focus_force()
        self.after_idle(self.attributes, '-topmost', False)

    def _on_yes(self):
        self.result = True
        self.destroy()

    def _on_no(self):
        self.result = False
        self.destroy()

    def show(self):
        self.parent.wait_window(self)
        return self.result, self.compress_output.get()


# --- Main Application Class (GUI) ---
class FileOrganizerApp:
    def __init__(self, master):
        self.master = master
        master.title("File Organizer")
        master.geometry("400x250")
        master.resizable(False, False)

        # Center the main window
        master.update_idletasks()
        width = master.winfo_width()
        height = master.winfo_height()
        x = (master.winfo_screenwidth() // 2) - (width // 2)
        y = (master.winfo_screenheight() // 2) - (height // 2)
        master.geometry(f'+{x}+{y}')

        self.create_widgets()

    def create_widgets(self):
        style = ttk.Style()
        style.configure("TLabel", font=("Arial", 10), padding=5)
        style.configure("TButton", font=("Arial", 10, "bold"), padding=10)
        style.configure("Header.TLabel", font=("Arial", 14, "bold"))

        main_frame = ttk.Frame(self.master, padding=20)
        main_frame.pack(expand=True, fill="both")

        header_label = ttk.Label(main_frame, text="Welcome to File Organizer", style="Header.TLabel")
        header_label.pack(pady=(0, 20))

        description_label = ttk.Label(main_frame, text="Organize your files into categorized folders based on their type and extension. Duplicates are handled automatically.", wraplength=350, justify="center")
        description_label.pack(pady=(0, 30))

        start_button = ttk.Button(main_frame, text="Start Organization", command=self.start_organization_process)
        start_button.pack(pady=(0, 10))

    def start_organization_process(self):
        last_source_folder, last_destination_folder = load_last_paths()

        if VERBOSE_MODE:
            print("Launching source folder selection dialog.")

        source_folder_selected = filedialog.askdirectory(
            parent=self.master, # Parent the dialog to the main window
            title="Select SOURCE Folder to Organize (and its subfolders)",
            initialdir=last_source_folder if last_source_folder else os.getcwd()
        )

        if not source_folder_selected:
            messagebox.showinfo("Cancelled", "No source folder selected. File organization cancelled.", parent=self.master)
            return

        if VERBOSE_MODE:
            print("Launching destination folder selection dialog.")

        initial_dir_for_dest = last_destination_folder if last_destination_folder else os.path.dirname(source_folder_selected)

        destination_folder_selected = filedialog.askdirectory(
            parent=self.master, # Parent the dialog to the main window
            title="Select DESTINATION Folder for the Organized Output",
            initialdir=initial_dir_for_dest
        )

        if not destination_folder_selected:
            messagebox.showinfo("Cancelled", "No destination folder selected. File organization cancelled.", parent=self.master)
            return

        if os.path.abspath(source_folder_selected) == os.path.abspath(destination_folder_selected):
            warning_result = messagebox.askyesno(
                "Warning: Same Source and Destination",
                "You have selected the same folder for both source and destination.\n\n"
                "If you proceed without compression, a new timestamped organization folder will be created directly inside the source folder.\n"
                "If you select compression, the archive will be created directly in the source folder.\n"
                "While this is generally safe, it's often better to choose a separate destination.\n\n"
                "Do you want to proceed anyway?",
                parent=self.master
            )
            if not warning_result:
                messagebox.showinfo("Cancelled", "File organization cancelled by user due to same source/destination.", parent=self.master)
                return

        confirm_dialog = CustomConfirmationDialog(self.master, source_folder_selected, destination_folder_selected)
        confirm, compress_checked = confirm_dialog.show()

        if confirm:
            total_files = count_files_in_folder(source_folder_selected)
            if total_files == 0:
                messagebox.showinfo("No Files Found", "No files found in the selected source folder or its subfolders to organize.", parent=self.master)
                save_last_paths(source_folder_selected, destination_folder_selected)
                return

            progress_window = tk.Toplevel(self.master) # Parent the progress window to the main window
            progress_window.title("Organizing Files...")
            progress_window.geometry("550x100")
            progress_window.resizable(False, False)
            progress_window.protocol("WM_DELETE_WINDOW", lambda: None) # Prevent closing during operation

            # Center progress window relative to the main window
            self.master.update_idletasks()
            x = self.master.winfo_x() + (self.master.winfo_width() // 2) - (progress_window.winfo_width() // 2)
            y = self.master.winfo_y() + (self.master.winfo_height() // 2) - (progress_window.winfo_height() // 2)
            progress_window.geometry(f"+{x}+{y}")

            progress_window.lift()
            progress_window.attributes('-topmost', True)
            progress_window.focus_force()
            progress_window.after_idle(progress_window.attributes, '-topmost', False)

            status_label = tk.Label(progress_window, text="Preparing...", pady=10)
            status_label.pack()

            progress_bar = ttk.Progressbar(progress_window, orient="horizontal", length=500, mode="determinate")
            progress_bar.pack(pady=5)

            # Run the organization in a way that allows GUI to update
            # This is a simple approach; for very long operations, threading might be considered
            # but it adds complexity. For file copying, it's usually acceptable.
            processed, added_to_output, duplicates, errors, final_output_path = organize_files_in_folder(
                source_folder_selected, destination_folder_selected, compress_checked, progress_bar, status_label, total_files
            )

            progress_window.destroy()

            save_last_paths(source_folder_selected, destination_folder_selected)

            # --- Final Summary Message ---
            summary_message = f"File organization process complete!\n\n" \
                              f"Source folder: {source_folder_selected.encode('utf-8', errors='replace').decode('utf-8')}\n" \
                              f"Destination folder: {destination_folder_selected.encode('utf-8', errors='replace').decode('utf-8')}\n"

            if final_output_path:
                if compress_checked:
                    summary_message += f"Resulting archive: {final_output_path.encode('utf-8', errors='replace').decode('utf-8')}\n" \
                                       f"(No temporary uncompressed folder created)\n\n"
                else:
                    summary_message += f"Resulting organized folder: {final_output_path.encode('utf-8', errors='replace').decode('utf-8')}\n\n"
            else:
                summary_message += "\nNo output file/folder was created (potentially due to errors or no files processed).\n\n"

            summary_message += f"Total files processed: {processed}\n" \
                               f"Files copied/added to output: {added_to_output}\n" \
                               f"Duplicate files copied/added: {duplicates}\n\n"

            if errors:
                summary_message += f"Errors encountered during process ({len(errors)}):\n"
                for i, error in enumerate(errors):
                    summary_message += f"- {error}\n"
                messagebox.showerror("Organization Complete with Errors", summary_message, parent=self.master)
            else:
                message_title = "Organization Complete"
                if processed == 0:
                    message_title = "Organization Complete (No files processed)"
                messagebox.showinfo(message_title, summary_message, parent=self.master)

        else:
            messagebox.showinfo("Cancelled", "File organization cancelled by user.", parent=self.master)

# --- Main execution ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Organize files in a specified folder and its subfolders.")
    parser.add_argument(
        "source_folder_path",
        nargs="?",
        help="The path to the SOURCE folder to organize. If not provided, a GUI dialog will open."
    )
    parser.add_argument(
        "--destination",
        help="Specify the DESTINATION folder for the organized output. Defaults to source parent if not provided."
    )
    parser.add_argument(
        "--compress",
        action="store_true",
        help="If specified, the organized output will be compressed into a .tar.xz archive directly, without creating an intermediate uncompressed folder."
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output to the terminal for debugging."
    )
    args = parser.parse_args()

    VERBOSE_MODE = args.verbose

    if args.source_folder_path:
        # CLI mode
        source_folder_cli = args.source_folder_path

        if not os.path.isdir(source_folder_cli):
            print(f"Error: Provided source path '{source_folder_cli.encode('utf-8', errors='replace').decode('utf-8')}' is not a valid directory.")
            exit(1)

        destination_folder_cli = args.destination
        if not destination_folder_cli:
            destination_folder_cli = os.path.dirname(source_folder_cli)
            if VERBOSE_MODE:
                print(f"No destination folder specified. Defaulting to parent of source: {destination_folder_cli.encode('utf-8', errors='replace').decode('utf-8')}")

        if not os.path.isdir(destination_folder_cli):
            print(f"Error: Provided destination path '{destination_folder_cli.encode('utf-8', errors='replace').decode('utf-8')}' is not a valid directory and could not be created.")
            exit(1)

        if os.path.abspath(source_folder_cli) == os.path.abspath(destination_folder_cli):
            print(f"Warning: Source and destination folders are the same ('{os.path.abspath(source_folder_cli).encode('utf-8', errors='replace').decode('utf-8')}').")
            if args.compress:
                print("The archive will be created directly in this folder.")
            else:
                print("A new timestamped organization folder will be created inside this directory.")

        total_files = count_files_in_folder(source_folder_cli)
        if total_files == 0:
            print("No files found in the selected source folder or its subfolders to organize.")
            save_last_paths(source_folder_cli, destination_folder_cli) # Save paths even if no files
            exit(0)

        print("--- Starting File Organization (CLI Mode) ---")
        processed, added_to_output, duplicates, errors, final_output_path = organize_files_in_folder(
            source_folder_cli, destination_folder_cli, args.compress, None, None, total_files
        )

        save_last_paths(source_folder_cli, destination_folder_cli) # Save paths after operation

        print(f"\n--- Organization Summary for {source_folder_cli.encode('utf-8', errors='replace').decode('utf-8')} ---")
        print(f"Output intended for: {destination_folder_cli.encode('utf-8', errors='replace').decode('utf-8')}")

        if final_output_path:
            if args.compress:
                print(f"Resulting archive: {final_output_path.encode('utf-8', errors='replace').decode('utf-8')}")
                print("(No temporary uncompressed folder created)")
            else:
                print(f"Uncompressed organized output folder: {final_output_path.encode('utf-8', errors='replace').decode('utf-8')}")
        else:
            print("No organized output file/folder was created due to errors or no files processed.")

        print(f"Total files processed: {processed}")
        print(f"Files copied/added to output: {added_to_output}")
        print(f"Duplicate files copied/added: {duplicates}")
        if errors:
            print("\nErrors encountered:")
            for error in errors:
                print(f"- {error}")

    else:
        # GUI mode
        # Check if a display is available before launching GUI
        if 'DISPLAY' in os.environ or os.name == 'nt' or os.name == 'posix' and os.getenv('TERM_PROGRAM') == 'vscode':
            root = tk.Tk()
            app = FileOrganizerApp(root)
            root.mainloop()
        else:
            print("No source folder path provided and no GUI detected. Please run this script in an environment that supports Tkinter,")
            print("or provide the source folder path as a command-line argument:")
            print("Usage: python script_name.py /path/to/your/source/folder [--destination /path/to/output] [--compress] [--verbose]")

