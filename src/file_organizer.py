import os
import shutil
import hashlib
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from datetime import datetime
import argparse

# --- Configuration ---
DUPLICATES_FOLDER_NAME = "duplicates"
NO_EXTENSION_FOLDER_NAME = "_no_extension_"
HIDDEN_OR_CONFIG_FOLDER_NAME = "_hidden_or_config_"
OTHER_FOLDER_NAME = "other"

# Global flag for verbose mode, set by command-line arguments
VERBOSE_MODE = False

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
                sha256.update(block)
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
    # Note: We need to exclude the actual names of the top-level folders that will be created
    # based on FILE_TYPE_GROUPS.keys(), plus the special folders.
    # This list is used only for counting, not for os.walk pruning in organize_files_in_folder
    top_level_group_names_for_counting_exclusion = list(FILE_TYPE_GROUPS.keys()) + [DUPLICATES_FOLDER_NAME, OTHER_FOLDER_NAME]

    for dirpath, dirnames, filenames in os.walk(target_folder_path):
        # Prune dirnames to avoid counting files in our own organizational folders
        # This is important for accurate file count if re-running on an already organized folder.
        dirnames[:] = [d for d in dirnames if d not in top_level_group_names_for_counting_exclusion]

        for item_name in filenames:
            count += 1
    return count


def organize_files_in_folder(target_folder_path, destination_root_folder, progress_bar=None, status_label=None, total_files_to_process=0):
    """
    Organizes files in the specified folder and its subfolders by type and handles duplicates.
    All organized files and duplicates are COPIED to subfolders directly under a new timestamped output folder.
    Includes progress bar updates (if GUI elements are provided).
    """
    error_messages = []
    processed_files_count = 0
    copied_files_count = 0
    duplicate_files_count = 0

    if not os.path.isdir(target_folder_path):
        error_messages.append(f"The source path '{target_folder_path.encode('utf-8', errors='replace').decode('utf-8')}' is not a valid directory.")
        return processed_files_count, copied_files_count, duplicate_files_count, error_messages, ""

    if not os.path.isdir(destination_root_folder):
        if not create_directory_if_not_exists(destination_root_folder, error_messages):
            error_messages.append(f"The destination path '{destination_root_folder.encode('utf-8', errors='replace').decode('utf-8')}' is not a valid directory and could not be created.")
            return processed_files_count, copied_files_count, duplicate_files_count, error_messages, ""


    # --- 1. Setup New Output Folder ---
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    original_folder_name = os.path.basename(target_folder_path)

    root_output_folder_name = f"file_organizer_{original_folder_name}_{timestamp}"
    # The organized output folder will be created INSIDE the user-selected destination_root_folder
    root_output_folder_path = os.path.join(destination_root_folder, root_output_folder_name)

    if not create_directory_if_not_exists(root_output_folder_path, error_messages):
        return processed_files_count, copied_files_count, duplicate_files_count, error_messages, ""

    # Create the main "duplicates" folder within the new root output folder
    duplicates_main_folder_path = os.path.join(root_output_folder_path, DUPLICATES_FOLDER_NAME)
    if not create_directory_if_not_exists(duplicates_main_folder_path, error_messages):
        return processed_files_count, copied_files_count, duplicate_files_count, error_messages, ""

    # This dictionary will store file hashes to detect duplicates.
    # Key: file_hash, Value: path of the first encountered (original) file in the new output folder
    known_file_hashes = {}

    # Set progress bar maximum if GUI elements are available
    if progress_bar and status_label:
        progress_bar['maximum'] = total_files_to_process
        current_file_index = 0
        if VERBOSE_MODE:
            print(f"\nStarting recursive file organization from: {target_folder_path.encode('utf-8', errors='replace').decode('utf-8')}")
            print(f"Output will be generated in: {root_output_folder_path.encode('utf-8', errors='replace').decode('utf-8')}")
            print("--------------------------------------------------")
    elif VERBOSE_MODE: # Only print this if not in GUI mode but verbose is on
        print(f"\nStarting recursive file organization from: {target_folder_path.encode('utf-8', errors='replace').decode('utf-8')}")
        print(f"Output will be generated in: {root_output_folder_path.encode('utf-8', errors='replace').decode('utf-8')}")
        print("--------------------------------------------------")


    # --- 2. Iterate through files in the target directory and its subdirectories ---
    for dirpath, dirnames, filenames in os.walk(target_folder_path):
        # IMPORTANT: Prune dirnames in-place to prevent os.walk from descending into
        # our *own output* organizational folders if they happen to be inside the source tree.
        # This ensures we don't try to re-process files already copied to the output.
        # We only exclude the root output folder itself and the duplicates folder.
        dirnames[:] = [d for d in dirnames if d != os.path.basename(root_output_folder_path) and d != DUPLICATES_FOLDER_NAME]

        if VERBOSE_MODE:
            print(f"\nScanning directory: {dirpath.encode('utf-8', errors='replace').decode('utf-8')}")

        for item_name in filenames:
            item_path = os.path.join(dirpath, item_name)

            # Update progress bar and status label if GUI elements are available
            if progress_bar and status_label:
                current_file_index += 1
                progress_bar['value'] = current_file_index
                status_label.config(text=f"Processing: {item_name.encode('utf-8', errors='replace').decode('utf-8')}")
                progress_bar.master.update_idletasks() # Update the progress window
                progress_bar.master.update() # Process events

            # Skip if the file is already in one of our organizational folders (e.g., if re-running on an already organized folder)
            # This check is more robust since the `dirnames` pruning is for directories.
            if item_path.startswith(root_output_folder_path):
                if VERBOSE_MODE:
                    print(f"Skipping file: '{item_name.encode('utf-8', errors='replace').decode('utf-8')}' (already in new output folder).")
                continue

            processed_files_count += 1
            if VERBOSE_MODE:
                print(f"Processing file: {item_name.encode('utf-8', errors='replace').decode('utf-8')} (from {dirpath.encode('utf-8', errors='replace').decode('utf-8')})")

            # --- 3. Handle Duplicates ---
            file_hash = calculate_file_hash(item_path)
            if file_hash is None: # Hash calculation failed (e.g., file disappeared)
                error_messages.append(f"Could not calculate hash for '{item_name.encode('utf-8', errors='replace').decode('utf-8')}' in '{dirpath.encode('utf-8', errors='replace').decode('utf-8')}'. Skipping.")
                if VERBOSE_MODE:
                    print(f"Skipping file {item_name.encode('utf-8', errors='replace').decode('utf-8')} due to hash calculation error.")
                continue

            if file_hash in known_file_hashes:
                # This file is a duplicate of a previously processed file.
                if VERBOSE_MODE:
                    original_file_path = known_file_hashes[file_hash]
                    print(f"Duplicate found: '{item_name.encode('utf-8', errors='replace').decode('utf-8')}' is a duplicate of '{os.path.basename(original_file_path).encode('utf-8', errors='replace').decode('utf-8')}'.")

                if copy_file_with_feedback(item_path, duplicates_main_folder_path, item_name, error_messages):
                    duplicate_files_count += 1
                continue # Move to the next file

            # --- 4. Process Original File: Categorize and Copy ---
            file_name_proper, file_extension = os.path.splitext(item_name)

            if VERBOSE_MODE:
                print(f"  Extracted file_name_proper: '{file_name_proper.encode('utf-8', errors='replace').decode('utf-8')}', file_extension: '{file_extension.encode('utf-8', errors='replace').decode('utf-8')}'")

            top_level_folder_name, sub_folder_name = get_categorized_paths(file_extension, file_name_proper)

            # First, ensure the top-level category folder exists within the root output folder
            current_top_level_path = os.path.join(root_output_folder_path, top_level_folder_name)
            if not create_directory_if_not_exists(current_top_level_path, error_messages):
                error_messages.append(f"Skipping file {item_name.encode('utf-8', errors='replace').decode('utf-8')} as its top-level category folder '{current_top_level_path.encode('utf-8', errors='replace').decode('utf-8')}' could not be created.")
                continue

            # Then, ensure the sub-folder for the specific extension exists within the top-level category
            specific_type_folder_path = os.path.join(current_top_level_path, sub_folder_name)
            if not create_directory_if_not_exists(specific_type_folder_path, error_messages):
                error_messages.append(f"Skipping file {item_name.encode('utf-8', errors='replace').decode('utf-8')} as its sub-folder '{specific_type_folder_path.encode('utf-8', errors='replace').decode('utf-8')}' could not be created.")
                continue

            # Copy the original file to its type folder
            copied_file_actual_path = copy_file_with_feedback(item_path, specific_type_folder_path, item_name, error_messages)

            if copied_file_actual_path:
                # If successfully copied, record its hash and new path
                known_file_hashes[file_hash] = copied_file_actual_path
                copied_files_count += 1
            else:
                error_messages.append(f"Failed to copy '{item_name.encode('utf-8', errors='replace').decode('utf-8')}', it will not be recorded as an original for duplicate checking.")

    if VERBOSE_MODE:
        print("\n--------------------------------------------------")
        print("File organization process complete.")

    return processed_files_count, copied_files_count, duplicate_files_count, error_messages, root_output_folder_path

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
                       f"Duplicates will be copied to a '{DUPLICATES_FOLDER_NAME}' folder.\n\n" \
                       f"A NEW timestamped output folder will be created inside the chosen destination." \
                       f"It's highly recommended to BACK UP YOUR FILES before proceeding."

        message_label = ttk.Label(content_frame, text=message_text, wraplength=500, justify="left")
        message_label.pack(pady=(0, 20), fill="both", expand=True)

        compress_checkbox = ttk.Checkbutton(content_frame, text="Compress output (.tar.xz) and delete uncompressed folder", variable=self.compress_output)
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
        height = max(height + 30, 350) # Slightly increased height

        x = self.parent.winfo_x() + (self.parent.winfo_width() // 2) - (width // 2)
        y = self.parent.winfo_y() + (self.parent.winfo_height() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

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

# --- GUI for folder selection ---
def select_folder_and_run():
    """
    Opens dialogs to select source and destination folders, then runs the organization script.
    """
    root = tk.Tk()
    root.geometry("1x1+2000+2000")
    root.overrideredirect(True)

    if VERBOSE_MODE:
        print("Launching source folder selection dialog.")

    source_folder_selected = filedialog.askdirectory(title="Select SOURCE Folder to Organize (and its subfolders)")

    if not source_folder_selected:
        messagebox.showinfo("Cancelled", "No source folder selected. File organization cancelled.")
        root.destroy()
        return

    # New: Ask for Destination Folder
    if VERBOSE_MODE:
        print("Launching destination folder selection dialog.")

    # Suggest parent of source_folder_selected as default
    initial_dir_for_dest = os.path.dirname(source_folder_selected)

    destination_folder_selected = filedialog.askdirectory(
        title="Select DESTINATION Folder for the Organized Output",
        initialdir=initial_dir_for_dest
    )

    if not destination_folder_selected:
        messagebox.showinfo("Cancelled", "No destination folder selected. File organization cancelled.")
        root.destroy()
        return

    # Check if source and destination are the same (or very similar)
    if os.path.abspath(source_folder_selected) == os.path.abspath(destination_folder_selected):
        warning_result = messagebox.askyesno(
            "Warning: Same Source and Destination",
            "You have selected the same folder for both source and destination.\n\n"
            "This will create a new timestamped organization folder directly inside the source folder.\n"
            "While this is generally safe, it's often better to choose a separate destination.\n\n"
            "Do you want to proceed anyway?"
        )
        if not warning_result:
            messagebox.showinfo("Cancelled", "File organization cancelled by user due to same source/destination.")
            root.destroy()
            return


    # Use custom confirmation dialog
    confirm_dialog = CustomConfirmationDialog(root, source_folder_selected, destination_folder_selected)
    confirm, compress_checked = confirm_dialog.show()

    if confirm:
        total_files = count_files_in_folder(source_folder_selected)
        if total_files == 0:
            messagebox.showinfo("No Files Found", "No files found in the selected source folder or its subfolders to organize.")
            root.destroy()
            return

        progress_window = tk.Toplevel(root)
        progress_window.title("Organizing Files...")
        progress_window.geometry("400x100")
        progress_window.resizable(False, False)
        progress_window.protocol("WM_DELETE_WINDOW", lambda: None)

        root.update_idletasks()
        x = root.winfo_x() + (root.winfo_width() // 2) - (progress_window.winfo_width() // 2)
        y = root.winfo_y() + (root.winfo_height() // 2) - (progress_window.winfo_height() // 2)
        progress_window.geometry(f"+{x}+{y}")

        progress_window.lift()
        progress_window.attributes('-topmost', True)
        progress_window.focus_force()
        progress_window.after_idle(progress_window.attributes, '-topmost', False)

        status_label = tk.Label(progress_window, text="Preparing...", pady=10)
        status_label.pack()

        progress_bar = ttk.Progressbar(progress_window, orient="horizontal", length=300, mode="determinate")
        progress_bar.pack(pady=5)

        # Pass the destination_folder_selected to the organization logic
        processed, copied, duplicates, errors, output_path = organize_files_in_folder(
            source_folder_selected, destination_folder_selected, progress_bar, status_label, total_files
        )

        progress_window.destroy()

        compressed_archive_path = None
        if output_path: # Ensure organization actually produced an output folder
            if compress_checked:
                try:
                    compression_status_window = tk.Toplevel(root)
                    compression_status_window.title("Compressing Output...")
                    compression_status_window.geometry("300x100")
                    compression_status_window.resizable(False, False)
                    compression_status_window.protocol("WM_DELETE_WINDOW", lambda: None)

                    x = root.winfo_x() + (root.winfo_width() // 2) - (compression_status_window.winfo_width() // 2)
                    y = root.winfo_y() + (root.winfo_height() // 2) - (compression_status_window.winfo_height() // 2)
                    compression_status_window.geometry(f"+{x}+{y}")

                    compression_label = tk.Label(compression_status_window, text="Compressing files, please wait...", pady=10)
                    compression_label.pack()

                    compression_progress_bar = ttk.Progressbar(compression_status_window, orient="horizontal", length=250, mode="indeterminate")
                    compression_progress_bar.pack(pady=5)
                    compression_progress_bar.start(10)

                    compression_status_window.update_idletasks()
                    compression_status_window.lift()
                    compression_status_window.attributes('-topmost', True)
                    compression_status_window.focus_force()
                    compression_status_window.after_idle(compression_status_window.attributes, '-topmost', False)

                    if VERBOSE_MODE:
                        print(f"\nCompression requested. Compressing '{output_path.encode('utf-8', errors='replace').decode('utf-8')}'...")

                    archive_base_name = os.path.basename(output_path)
                    archive_parent_dir = os.path.dirname(output_path) # This is the destination_folder_selected

                    compressed_archive_path = shutil.make_archive(
                        base_name=os.path.join(archive_parent_dir, archive_base_name),
                        format='xztar',
                        root_dir=output_path
                    )
                    if VERBOSE_MODE:
                        print(f"Successfully created archive: {compressed_archive_path.encode('utf-8', errors='replace').decode('utf-8')}")

                    compression_progress_bar.stop()
                    compression_status_window.destroy()

                    # New: Automatically delete uncompressed folder if compression was successful
                    try:
                        if VERBOSE_MODE:
                            print(f"Deleting original uncompressed folder: {output_path.encode('utf-8', errors='replace').decode('utf-8')}")
                        shutil.rmtree(output_path)
                    except Exception as e:
                        errors.append(f"Failed to delete original uncompressed folder '{output_path.encode('utf-8', errors='replace').decode('utf-8')}': {e}")
                        if VERBOSE_MODE:
                            print(f"Error deleting original folder: {e}")

                except Exception as e:
                    errors.append(f"Error during compression: {e}")
                    if VERBOSE_MODE:
                        print(f"Error during compression: {e}")
                    if 'compression_progress_bar' in locals() and compression_progress_bar.winfo_exists():
                        compression_progress_bar.stop()
                    if 'compression_status_window' in locals() and compression_status_window.winfo_exists():
                        compression_status_window.destroy()

            # --- Final Summary Message ---
            summary_message = f"File organization process complete!\n\n" \
                              f"Source folder: {source_folder_selected.encode('utf-8', errors='replace').decode('utf-8')}\n" \
                              f"Destination folder: {destination_folder_selected.encode('utf-8', errors='replace').decode('utf-8')}\n"

            if compressed_archive_path:
                summary_message += f"Resulting archive: {compressed_archive_path.encode('utf-8', errors='replace').decode('utf-8')}\n" \
                                   f"(Uncompressed folder automatically deleted)\n\n"
            else:
                summary_message += f"Resulting organized folder: {output_path.encode('utf-8', errors='replace').decode('utf-8')}\n\n"

            summary_message += f"Total files processed: {processed}\n" \
                               f"Files copied to type folders: {copied}\n" \
                               f"Duplicate files copied to '{DUPLICATES_FOLDER_NAME}': {duplicates}\n\n"

            if errors:
                summary_message += f"Errors encountered during process ({len(errors)}):\n"
                for i, error in enumerate(errors):
                    summary_message += f"- {error}\n"
                messagebox.showerror("Organization Complete with Errors", summary_message)
            else:
                messagebox.showinfo("Organization Complete", summary_message)
        else: # output_path was not successfully created (e.g., source not valid, or errors during initial setup)
            messagebox.showerror("Organization Failed", "The organization process could not be completed, or no output folder was created.\n" + "\n".join(errors))

    else:
        messagebox.showinfo("Cancelled", "File organization cancelled by user.")

    root.destroy()

# --- Main execution ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Organize files in a specified folder and its subfolders.")
    parser.add_argument(
        "source_folder_path",
        nargs="?", # Makes the argument optional
        help="The path to the SOURCE folder to organize. If not provided, a GUI dialog will open."
    )
    parser.add_argument(
        "--destination",
        help="Specify the DESTINATION folder for the organized output. Defaults to source parent if not provided."
    )
    parser.add_argument(
        "--compress",
        action="store_true", # Stores True if flag is present
        help="If specified, the organized output will be compressed into a .tar.xz archive, and the uncompressed output folder will be deleted."
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
            exit(1) # Exit with an error code

        # Determine destination folder for CLI
        destination_folder_cli = args.destination
        if not destination_folder_cli:
            destination_folder_cli = os.path.dirname(source_folder_cli)
            if VERBOSE_MODE:
                print(f"No destination folder specified. Defaulting to parent of source: {destination_folder_cli.encode('utf-8', errors='replace').decode('utf-8')}")

        if not os.path.isdir(destination_folder_cli):
            print(f"Error: Provided destination path '{destination_folder_cli.encode('utf-8', errors='replace').decode('utf-8')}' is not a valid directory and could not be created.")
            exit(1) # Exit with an error code

        # Warn if source and destination are effectively the same
        if os.path.abspath(source_folder_cli) == os.path.abspath(destination_folder_cli):
            print(f"Warning: Source and destination folders are the same ('{os.path.abspath(source_folder_cli).encode('utf-8', errors='replace').decode('utf-8')}').")
            print("A new timestamped organization folder will be created inside this directory.")

        total_files = count_files_in_folder(source_folder_cli)
        if total_files == 0:
            print("No files found in the selected source folder or its subfolders to organize.")
            exit(0) # Exit successfully if nothing to do

        print("--- Starting File Organization (CLI Mode) ---")
        processed, copied, duplicates, errors, output_path = organize_files_in_folder(
            source_folder_cli, destination_folder_cli, None, None, total_files # No GUI progress in CLI
        )

        print(f"\n--- Organization Summary for {source_folder_cli.encode('utf-8', errors='replace').decode('utf-8')} ---")
        print(f"Output intended for: {destination_folder_cli.encode('utf-8', errors='replace').decode('utf-8')}")

        if output_path: # Check if an output folder was successfully created
            print(f"Organized files written to temporary uncompressed folder: {output_path.encode('utf-8', errors='replace').decode('utf-8')}")

            if args.compress:
                try:
                    print(f"\nCLI mode: Compressing '{output_path.encode('utf-8', errors='replace').decode('utf-8')}'...")
                    archive_base_name = os.path.basename(output_path)
                    archive_parent_dir = os.path.dirname(output_path) # This is destination_folder_cli

                    compressed_archive_path = shutil.make_archive(
                        base_name=os.path.join(archive_parent_dir, archive_base_name),
                        format='xztar',
                        root_dir=output_path
                    )
                    print(f"Successfully created compressed archive: {compressed_archive_path.encode('utf-8', errors='replace').decode('utf-8')}")

                    # Automatically delete original uncompressed folder after successful compression
                    try:
                        print(f"Deleting original uncompressed folder: {output_path.encode('utf-8', errors='replace').decode('utf-8')}")
                        shutil.rmtree(output_path)
                        print("Original uncompressed folder deleted.")
                    except Exception as e:
                        print(f"Error deleting original uncompressed folder '{output_path.encode('utf-8', errors='replace').decode('utf-8')}': {e}")
                except Exception as e:
                    print(f"Error during CLI compression: {e}")
                    errors.append(f"Error during compression: {e}")
            else:
                print(f"Uncompressed organized output folder: {output_path.encode('utf-8', errors='replace').decode('utf-8')}")
        else:
            print("No organized output folder was created due to errors or no files.")

        print(f"Total files processed: {processed}")
        print(f"Files copied to type folders: {copied}")
        print(f"Duplicate files copied: {duplicates}")
        if errors:
            print("\nErrors encountered:")
            for error in errors:
                print(f"- {error}")

    else:
        # Fallback to GUI mode if no folder_path is provided and GUI is available
        if 'DISPLAY' in os.environ or os.name == 'nt':
            select_folder_and_run()
        else:
            print("No source folder path provided and no GUI detected. Please run this script in an environment that supports Tkinter,")
            print("or provide the source folder path as a command-line argument:")
            print("Usage: python script_name.py /path/to/your/source/folder [--destination /path/to/output] [--compress] [--verbose]")
