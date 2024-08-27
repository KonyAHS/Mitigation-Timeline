import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os

class MitigationPlanDesigner:
    def __init__(self, root):
        self.root = root
        self.root.title("Mitigation Plan Designer")
        self.root.geometry("800x600")

        self.current_file = None  # To store the path of the imported file

        # Setup Treeview (like a spreadsheet)
        self.tree = ttk.Treeview(self.root, columns=("Mechanic", "Notes", "Mitigation", "Time"), show="headings")
        self.tree.heading("Mechanic", text="Mechanic")
        self.tree.heading("Notes", text="Notes")
        self.tree.heading("Mitigation", text="Mitigation")
        self.tree.heading("Time", text="Time")

        # Configure column width
        self.tree.column("Mechanic", width=150)
        self.tree.column("Notes", width=300)
        self.tree.column("Mitigation", width=200)
        self.tree.column("Time", width=100)

        # Add scrollbar for the Treeview
        self.tree_scroll = ttk.Scrollbar(self.root, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=self.tree_scroll.set)
        self.tree_scroll.pack(side="right", fill="y")
        self.tree.pack(expand=True, fill="both")

        # Add Buttons
        self.add_button = tk.Button(self.root, text="Add Row", command=self.add_row)
        self.add_button.pack(side="left", padx=10, pady=10)

        self.delete_button = tk.Button(self.root, text="Delete Row", command=self.delete_row)
        self.delete_button.pack(side="left", padx=10)

        self.edit_button = tk.Button(self.root, text="Edit Row", command=self.edit_row)
        self.edit_button.pack(side="left", padx=10)

        self.move_up_button = tk.Button(self.root, text="Move Up", command=lambda: self.move_row("up"))
        self.move_up_button.pack(side="left", padx=10)

        self.move_down_button = tk.Button(self.root, text="Move Down", command=lambda: self.move_row("down"))
        self.move_down_button.pack(side="left", padx=10)

        self.save_button = tk.Button(self.root, text="Export to .txt", command=self.export_to_txt)
        self.save_button.pack(side="left", padx=10)

        self.import_button = tk.Button(self.root, text="Import from .txt", command=self.import_from_txt)
        self.import_button.pack(side="left", padx=10)

        # Bind double-click event to start editing a row

        # Bind Shift+S to trigger export

        # Keybindings
        self.tree.bind("<Double-1>", self.on_double_click)
        self.root.bind("<Control-s>", lambda event: self.export_with_keybind())
        self.root.bind("<Shift-A>", lambda event: self.add_row())
        self.root.bind("<Shift-D>", lambda event: self.delete_row())
        self.root.bind("<Shift-E>", lambda event: self.edit_row())
        self.root.bind("<Shift-U>", lambda event: self.move_row("up"))
        self.root.bind("<Shift-M>", lambda event: self.move_row("down"))


        # To store the entry widgets
        self.entry_widgets = {}

    def disable_keybinds(self):
        """Disable global keybinds."""
        self.root.unbind("<Shift-D>")
        self.root.unbind("<Shift-E>")
        self.root.unbind("<Shift-U>")
        self.root.unbind("<Shift-A>")
        self.root.unbind("<Shift-M>")
        self.root.unbind("<Control-s>")

    def enable_keybinds(self):
        """Enable global keybinds."""
        self.root.bind("<Shift-A>", lambda event: self.add_row())
        self.root.bind("<Shift-D>", lambda event: self.delete_row())
        self.root.bind("<Shift-E>", lambda event: self.edit_row())
        self.root.bind("<Shift-U>", lambda event: self.move_row("up"))
        self.root.bind("<Shift-M>", lambda event: self.move_row("down"))
        self.root.bind("<Control-s>", lambda event: self.export_with_keybind())


    def add_row(self):
        """Add an empty row to the treeview."""
        self.tree.insert("", "end", values=("Enter Mechanic", "Enter Notes", "Enter Mitigation", "00:00"))

    def delete_row(self):
        """Delete the selected row from the treeview."""
        selected_item = self.tree.selection()
        if selected_item:
            self.tree.delete(selected_item)
        else:
            messagebox.showwarning("Warning", "No row selected for deletion.")

    def edit_row(self):
        """Start editing the selected row."""
        selected_item = self.tree.selection()
        if selected_item:
            self.on_double_click(None)
        else:
            messagebox.showwarning("Warning", "No row selected for editing.")

    def on_double_click(self, event):
        """Handle double-click event to edit a row."""
        selected_item = self.tree.selection()
        if selected_item:
            self.editing_row(selected_item)

    def editing_row(self, selected_item):
        """Enable editing of the selected row."""
        self.disable_keybinds()  # Disable keybinds while editing

        values = self.tree.item(selected_item, "values")

        # Create Entry widgets for each column in the row
        for idx, column in enumerate(self.tree["columns"]):
            x, y, width, height = self.tree.bbox(selected_item, column)
            entry = tk.Entry(self.root)
            entry.insert(0, values[idx])
            entry.place(x=x, y=y + self.tree.winfo_rooty() - self.root.winfo_rooty(), width=width, height=height)
            entry.bind("<Return>", lambda e, item=selected_item, idx=idx: self.save_edit(item, idx))

            # Store the entry widget reference
            self.entry_widgets[column] = entry


    def save_edit(self, item, col_idx):
        """Save the edited data back to the treeview."""
        # Retrieve new values from the entry widgets
        new_values = list(self.tree.item(item, "values"))

        # Validate the Time field first before saving anything
        for idx, column in enumerate(self.tree["columns"]):
            entry_widget = self.entry_widgets.get(column)
            if entry_widget:
                new_value = entry_widget.get()

                # Validate the Time field format first
                if column == "Time":
                    if not self.validate_time_format(new_value):
                        messagebox.showerror("Error", "Invalid Time format. Please use MM:SS.")
                        entry_widget.focus_set()
                        return  # Stop saving if Time is invalid, no widgets destroyed

                # If validation passes, update the new values for the row
                new_values[idx] = new_value

        # If all fields are valid, destroy the entry widgets and update the row
        for entry_widget in self.entry_widgets.values():
            entry_widget.destroy()

        # Update the treeview with the new values
        self.tree.item(item, values=new_values)

        # Clear entry widgets and exit edit mode
        self.entry_widgets.clear()

        # Re-enable keybinds after editing
        self.enable_keybinds()

        # Optionally: Provide feedback that the row has been updated
        # messagebox.showinfo("Success", "Row updated successfully!")



    def move_row(self, direction):
        """Move the selected row up or down."""
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Warning", "No row selected for movement.")
            return

        current_index = self.tree.index(selected_item)
        if direction == "up" and current_index > 0:
            self.tree.move(selected_item, self.tree.parent(selected_item), current_index - 1)
        elif direction == "down" and current_index < len(self.tree.get_children()) - 1:
            self.tree.move(selected_item, self.tree.parent(selected_item), current_index + 1)

    def export_to_txt(self):
        """Export the data to a .txt file."""
        if self.current_file:
            # If there is an existing file, overwrite it
            self.save_to_file(self.current_file)
        else:
            # Ask user for the file name to save as
            file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
            if file_path:
                self.current_file = file_path
                self.save_to_file(file_path)
                self.update_window_title()

    def save_to_file(self, file_path):
        """Helper function to save the data to the specified file."""
        # Get data from treeview
        with open(file_path, 'w') as file:
            for row_id in self.tree.get_children():
                row = self.tree.item(row_id)['values']
                file.write(f"Mechanic: {row[0]}\nNotes: {row[1]}\nMitigation: {row[2]}\nTime: {row[3]}\n\n")

        messagebox.showinfo("Success", f"Data saved to {file_path}")

    def export_with_keybind(self):
        """Triggered by Shift+S keybind to either export or overwrite the file."""
        if self.current_file:
            self.save_to_file(self.current_file)  # Overwrite the imported file
        else:
            self.export_to_txt()  # Prompt the user to save as a new file

    def import_from_txt(self):
        """Import data from a .txt file."""
        file_path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        if not file_path:
            return

        self.current_file = file_path  # Store the file path for future overwrites

        with open(file_path, 'r') as file:
            self.tree.delete(*self.tree.get_children())  # Clear current rows
            current_row = {}
            for line in file:
                line = line.strip()
                if line.startswith("Mechanic:"):
                    current_row['Mechanic'] = line.split(": ", 1)[1]
                elif line.startswith("Notes:"):
                    current_row['Notes'] = line.split(": ", 1)[1]
                elif line.startswith("Mitigation:"):
                    current_row['Mitigation'] = line.split(": ", 1)[1]
                elif line.startswith("Time:"):
                    current_row['Time'] = line.split(": ", 1)[1]
                    # When we have all 4 fields, insert the row and reset
                    self.tree.insert("", "end", values=(current_row['Mechanic'], current_row['Notes'], current_row['Mitigation'], current_row['Time']))
                    current_row = {}

        self.update_window_title()
        # messagebox.showinfo("Success", f"Data imported from {file_path}")

    def update_window_title(self):
        """Update the window title to reflect the current file."""
        if self.current_file:
            file_name = os.path.basename(self.current_file)
            self.root.title(f"Mitigation Plan Designer - {file_name}")
        else:
            self.root.title("Mitigation Plan Designer")
    
    def validate_time_format(self, time_str):
        """Validate the format of the Time field (MM:SS)."""
        try:
            # Split the time string into minutes and seconds
            minutes, seconds = time_str.split(":")
            
            # Check if both parts are exactly 2 digits long and are integers
            if len(minutes) == 2 and len(seconds) == 2 and minutes.isdigit() and seconds.isdigit():
                minutes = int(minutes)
                seconds = int(seconds)
                # Ensure that minutes are non-negative and seconds are between 0 and 59
                if 0 <= minutes <= 99 and 0 <= seconds <= 59:
                    return True
            return False
        except ValueError:
            return False




if __name__ == "__main__":
    root = tk.Tk()
    app = MitigationPlanDesigner(root)
    root.mainloop()
