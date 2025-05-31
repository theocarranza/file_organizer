import os
import shutil
import hashlib
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk # Import ttk for themed widgets like Progressbar
from datetime import datetime
import argparse # Import argparse for command-line argument parsing

# --- Configuration ---
# You can change these default folder names if you like
DUPLICATES_FOLDER_NAME = "duplicates"
NO_EXTENSION_FOLDER_NAME = "_no_extension_" # For files without a discernible extension
HIDDEN_OR_CONFIG_FOLDER_NAME = "_hidden_or_config_" # For files like .bashrc (starting with a dot, no extension after)
OTHER_FOLDER_NAME = "other" # For files not belonging to any specific group

# Global flag for verbose mode, set by command-line arguments
VERBOSE_MODE = False

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


def organize_files_in_folder(target_folder_path, progress_bar=None, status_label=None, total_files_to_process=0):
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

    # Set progress bar maximum if GUI elements are available
    if progress_bar and status_label:
        progress_bar['maximum'] = total_files_to_process
        current_file_index = 0
        if VERBOSE_MODE:
            print(f"\nStarting recursive file organization in: {target_folder_path.encode('utf-8', errors='replace').decode('utf-8')}")
            print(f"Output will be generated in: {root_output_folder_path.encode('utf-8', errors='replace').decode('utf-8')}")
            print("--------------------------------------------------")
    elif VERBOSE_MODE: # Only print this if not in GUI mode but verbose is on
        print(f"\nStarting recursive file organization in: {target_folder_path.encode('utf-8', errors='replace').decode('utf-8')}")
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
    def __init__(self, parent, folder_path):
        super().__init__(parent)
        self.parent = parent # Store the parent reference
        self.transient(parent) # Make this dialog transient for the parent
        self.grab_set() # Make it modal
        self.result = False # Default result
        self.compress_output = tk.BooleanVar(self, value=False) # New: Variable for the checkbox

        self.title("Confirm Organization")
        self.resizable(False, True) # Allow vertical resizing if needed, but not horizontal

        # Styling
        style = ttk.Style()
        style.configure("TLabel", font=("Arial", 10), padding=5)
        style.configure("TButton", font=("Arial", 10, "bold"), padding=8)
        style.configure("Header.TLabel", font=("Arial", 12, "bold"))

        # Frame for content
        content_frame = ttk.Frame(self, padding=15)
        content_frame.pack(expand=True, fill="both")

        header_label = ttk.Label(content_frame, text="Confirm File Organization", style="Header.TLabel")
        header_label.pack(pady=(0, 10))

        # Message details
        message_text = f"Are you sure you want to organize files from:\n" \
                       f"•  {folder_path.encode('utf-8', errors='replace').decode('utf-8')}\n\n" \
                       f"This will recursively COPY files from this folder and all its subfolders.\n" \
                       f"Files will be organized into main categories (e.g., 'images', 'documents') " \
                       f"with subfolders for specific extensions (e.g., 'images/jpg').\n" \
                       f"Less common file types will be grouped under an '{OTHER_FOLDER_NAME}' folder.\n" \
                       f"Duplicates will be copied to a '{DUPLICATES_FOLDER_NAME}' folder.\n\n" \
                       f"A NEW output folder will be created in the parent directory of " \
                       f"'{os.path.basename(folder_path).encode('utf-8', errors='replace').decode('utf-8')}' " \
                       f"to contain all organized files.\n\n" \
                       f"It's highly recommended to BACK UP YOUR FILES before proceeding."

        # Using a Label with wraplength and allowing the window to resize is simpler
        message_label = ttk.Label(content_frame, text=message_text, wraplength=500, justify="left")
        message_label.pack(pady=(0, 20), fill="both", expand=True) # Allow label to expand

        # New: Checkbox for compression
        compress_checkbox = ttk.Checkbutton(content_frame, text="Compress output (.tar.xz)", variable=self.compress_output)
        compress_checkbox.pack(pady=(5, 15), anchor="w") # Anchor west for left alignment

        # Buttons
        button_frame = ttk.Frame(content_frame)
        button_frame.pack(pady=(10, 0)) # Pack at the bottom

        yes_button = ttk.Button(button_frame, text="Yes, Proceed", command=self._on_yes)
        yes_button.pack(side="left", padx=10)

        no_button = ttk.Button(button_frame, text="No, Cancel", command=self._on_no)
        no_button.pack(side="right", padx=10)

        self.protocol("WM_DELETE_WINDOW", self._on_no) # Handle window close button

        # --- Dynamic sizing and centering ---
        self.update_idletasks() # Force widgets to compute their sizes
        width = self.winfo_reqwidth()
        height = self.winfo_reqheight()

        # Add some padding to the requested dimensions and ensure minimums
        width = max(width + 30, 550) # Add 30px padding, ensure minimum width
        height = max(height + 30, 300) # Add 30px padding, ensure minimum height to prevent tiny windows

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
        self.parent.wait_window(self) # Wait until the dialog is closed
        return self.result, self.compress_output.get() # New: Return checkbox state

# --- GUI for folder selection ---
def select_folder_and_run():
    """
    Opens a dialog to select a folder and then runs the organization script.
    """
    root = tk.Tk()
    # Instead of root.withdraw(), make it tiny and off-screen
    root.geometry("1x1+2000+2000") # Position far off-screen
    root.overrideredirect(True) # Remove window decorations (title bar, etc.)
    # root.withdraw() # Old way

    # Add a verbose print here
    if VERBOSE_MODE:
        print("Launching folder selection dialog. Please look for a popup window.")

    folder_selected = filedialog.askdirectory(title="Select Folder to Organize (and its subfolders)")

    if folder_selected: # If a folder was selected
        # Use custom confirmation dialog
        confirm_dialog = CustomConfirmationDialog(root, folder_selected)
        confirm, compress_checked = confirm_dialog.show() # New: Capture checkbox state

        if confirm:
            # --- Pre-scan to count files for progress bar ---
            total_files = count_files_in_folder(folder_selected)
            if total_files == 0:
                messagebox.showinfo("No Files Found", "No files found in the selected folder or its subfolders to organize.")
                root.destroy() # Destroy root before returning
                return

            # --- Create Progress Window ---
            progress_window = tk.Toplevel(root)
            progress_window.title("Organizing Files...")
            # Set a reasonable initial size for the progress window
            progress_window.geometry("400x100")
            progress_window.resizable(False, False)
            progress_window.protocol("WM_DELETE_WINDOW", lambda: None) # Disable close button

            # Center the progress window
            root.update_idletasks() # Ensure window dimensions are calculated
            x = root.winfo_x() + (root.winfo_width() // 2) - (progress_window.winfo_width() // 2)
            y = root.winfo_y() + (root.winfo_height() // 2) - (progress_window.winfo_height() // 2)
            progress_window.geometry(f"+{x}+{y}")

            # Bring progress window to front and give focus
            progress_window.lift()
            progress_window.attributes('-topmost', True) # Keep it on top
            progress_window.focus_force() # Force focus
            # Release topmost after a short delay to allow other windows to come up if needed later
            progress_window.after_idle(progress_window.attributes, '-topmost', False)

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

            # --- New: Compression Logic ---
            compressed_archive_path = None
            if compress_checked and output_path:
                try:
                    # Update status label for compression
                    compression_status_window = tk.Toplevel(root)
                    compression_status_window.title("Compressing Output...")
                    compression_status_window.geometry("300x100") # Increased height for progress bar
                    compression_status_window.resizable(False, False)
                    compression_status_window.protocol("WM_DELETE_WINDOW", lambda: None) # Disable close button

                    x = root.winfo_x() + (root.winfo_width() // 2) - (compression_status_window.winfo_width() // 2)
                    y = root.winfo_y() + (root.winfo_height() // 2) - (compression_status_window.winfo_height() // 2)
                    compression_status_window.geometry(f"+{x}+{y}")

                    compression_label = tk.Label(compression_status_window, text="Compressing files, please wait...", pady=10)
                    compression_label.pack()

                    # New: Indeterminate Progress Bar for Compression
                    compression_progress_bar = ttk.Progressbar(compression_status_window, orient="horizontal", length=250, mode="indeterminate")
                    compression_progress_bar.pack(pady=5)
                    compression_progress_bar.start(10) # Start animation, update every 10ms

                    compression_status_window.update_idletasks()
                    compression_status_window.lift()
                    compression_status_window.attributes('-topmost', True)
                    compression_status_window.focus_force()
                    compression_status_window.after_idle(compression_status_window.attributes, '-topmost', False)

                    if VERBOSE_MODE:
                        print(f"\nCompression requested. Compressing '{output_path.encode('utf-8', errors='replace').decode('utf-8')}'...")

                    # shutil.make_archive will create the archive in the parent directory of output_path
                    # The base_name will be the name of the output folder itself
                    archive_base_name = os.path.basename(output_path)
                    archive_parent_dir = os.path.dirname(output_path)

                    compressed_archive_path = shutil.make_archive(
                        base_name=os.path.join(archive_parent_dir, archive_base_name),
                        format='xztar', # For high compression
                        root_dir=output_path # The directory to archive
                    )
                    if VERBOSE_MODE:
                        print(f"Successfully created archive: {compressed_archive_path.encode('utf-8', errors='replace').decode('utf-8')}")

                    compression_progress_bar.stop() # Stop animation
                    compression_status_window.destroy() # Close compression status window

                    # Optional: Ask to delete original uncompressed folder
                    if messagebox.askyesno("Compression Complete",
                                            f"Output compressed to:\n{compressed_archive_path.encode('utf-8', errors='replace').decode('utf-8')}\n\n"
                                            "Do you want to delete the original uncompressed folder?") :
                        try:
                            shutil.rmtree(output_path)
                            if VERBOSE_MODE:
                                print(f"Deleted original uncompressed folder: {output_path.encode('utf-8', errors='replace').decode('utf-8')}")
                        except Exception as e:
                            messagebox.showerror("Cleanup Error", f"Failed to delete original folder: {e}")
                            if VERBOSE_MODE:
                                print(f"Error deleting original folder: {e}")

                except Exception as e:
                    errors.append(f"Error during compression: {e}")
                    if VERBOSE_MODE:
                        print(f"Error during compression: {e}")
                    # Ensure progress bar is stopped and window is destroyed even on error
                    if 'compression_progress_bar' in locals() and compression_progress_bar.winfo_exists():
                        compression_progress_bar.stop()
                    if 'compression_status_window' in locals() and compression_status_window.winfo_exists():
                        compression_status_window.destroy()


            # --- Final Summary Message ---
            summary_message = f"File organization process complete!\n\n" \
                              f"Original folder scanned: {folder_selected.encode('utf-8', errors='replace').decode('utf-8')}\n" \
                              f"Output generated in: {output_path.encode('utf-8', errors='replace').decode('utf-8')}\n"

            if compressed_archive_path:
                summary_message += f"Compressed archive created: {compressed_archive_path.encode('utf-8', errors='replace').decode('utf-8')}\n\n"
            else:
                summary_message += "\n" # Add a newline if no compression

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
        else:
            messagebox.showinfo("Cancelled", "File organization cancelled by user.")
    else:
        messagebox.showinfo("Cancelled", "No folder selected. File organization cancelled.")

    root.destroy() # Ensure the root Tkinter window is destroyed when done.

# --- Main execution ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Organize files in a specified folder and its subfolders.")
    parser.add_argument(
        "folder_path",
        nargs="?", # Makes the argument optional
        help="The path to the folder to organize. If not provided, a GUI dialog will open."
    )
    parser.add_argument(
        "--verbose",
        action="store_true", # Stores True if flag is present
        help="Enable verbose output to the terminal for debugging."
    )
    args = parser.parse_args()

    # Set the global VERBOSE_MODE flag
    VERBOSE_MODE = args.verbose

    if args.folder_path:
        # Run in CLI mode if folder_path is provided
        if not os.path.isdir(args.folder_path):
            print(f"Error: Provided path '{args.folder_path}' is not a valid directory.")
        else:
            total_files = count_files_in_folder(args.folder_path)
            if total_files == 0:
                print("No files found in the selected folder or its subfolders to organize.")
            else:
                # Pass None for GUI elements when running in CLI mode
                processed, copied, duplicates, errors, output_path = organize_files_in_folder(
                    args.folder_path, None, None, total_files
                )
                print(f"\n--- Organization Summary for {args.folder_path.encode('utf-8', errors='replace').decode('utf-8')} ---")
                print(f"Output generated in: {output_path.encode('utf-8', errors='replace').decode('utf-8')}")
                print(f"Total files processed: {processed}")
                print(f"Files copied to type folders: {copied}")
                print(f"Duplicate files copied: {duplicates}")
                if errors:
                    print("\nErrors encountered:")
                    for error in errors:
                        print(f"- {error}")

                # CLI mode compression (no checkbox, always compress if output exists)
                # For CLI, we'll assume compression is desired if the output path is valid
                if output_path:
                    try:
                        print(f"\nCLI mode: Compressing '{output_path.encode('utf-8', errors='replace').decode('utf-8')}'...")
                        archive_base_name = os.path.basename(output_path)
                        archive_parent_dir = os.path.dirname(output_path)
                        compressed_archive_path = shutil.make_archive(
                            base_name=os.path.join(archive_parent_dir, archive_base_name),
                            format='xztar',
                            root_dir=output_path
                        )
                        print(f"Successfully created compressed archive: {compressed_archive_path.encode('utf-8', errors='replace').decode('utf-8')}")
                        # Optional: Delete original uncompressed folder in CLI mode
                        # if input("Delete original uncompressed folder? (y/n): ").lower() == 'y':
                        #     shutil.rmtree(output_path)
                        #     print(f"Original folder '{output_path.encode('utf-8', errors='replace').decode('utf-8')}' deleted.")
                    except Exception as e:
                        print(f"Error during CLI compression: {e}")

    else:
        # Fallback to GUI mode if no folder_path is provided and GUI is available
        if 'DISPLAY' in os.environ or os.name == 'nt': # Basic check for GUI environment
            select_folder_and_run()
        else:
            print("No folder path provided and no GUI detected. Please run this script in an environment that supports Tkinter,")
            print("or provide the folder path as a command-line argument:")
            print("Usage: python script_name.py /path/to/your/folder [--verbose]")
