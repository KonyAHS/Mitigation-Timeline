import tkinter as tk
from tkinter import ttk  # Import for the dropdown menu (Combobox)
import time
import threading
import keyboard
import sys
import os

class MitigationOverlay:
    def __init__(self):
        # Initialize the window
        self.root = tk.Tk()
        self.root.title("FFXIV Mitigation Overlay")
        
        # Set window size and position
        self.root.geometry("400x380")  # Adjusted height to accommodate the new dropdown
        self.root.attributes("-topmost", True)  # Always on top
        self.root.attributes("-alpha", 0.8)  # Transparency level

        # Dropdown for selecting the mitigation plan
        self.plan_label = tk.Label(self.root, text="Select Mitigation Plan:", font=("Helvetica", 12))
        self.plan_label.pack(pady=5)

        self.plan_combobox = ttk.Combobox(self.root, state="readonly")
        self.plan_combobox.pack(pady=5)
        self.populate_plan_dropdown()

        # Mechanic info
        self.mechanic_label = tk.Label(self.root, text="Mechanic: Waiting...", font=("Helvetica", 16))
        self.mechanic_label.pack(pady=10)

        self.notes_label = tk.Label(self.root, text="Notes: N/A", font=("Helvetica", 12))
        self.notes_label.pack(pady=10)

        self.mitigation_label = tk.Label(self.root, text="Mitigation: N/A", font=("Helvetica", 16))
        self.mitigation_label.pack(pady=10)

        # Timer
        self.timer_label = tk.Label(self.root, text="Time: 00:00", font=("Helvetica", 12))
        self.timer_label.pack(pady=10)

        # "Mechanic happening in X seconds" field
        self.next_mechanic_time_label = tk.Label(self.root, text="Mechanic happening in: N/A", font=("Helvetica", 12))
        self.next_mechanic_time_label.pack(pady=5)

        # Divider line
        self.canvas = tk.Canvas(self.root, height=1, bg="black")
        self.canvas.pack(fill=tk.X, padx=10, pady=5)

        # Next Mechanic Info (Left aligned)
        self.next_mechanic_label = tk.Label(self.root, text="Next: N/A", font=("Helvetica", 10), anchor="w", justify="left")
        self.next_mechanic_label.pack(fill=tk.X, padx=10, pady=5)

        self.next_mitigation_label = tk.Label(self.root, text="Mitigation: N/A", font=("Helvetica", 10), anchor="w", justify="left")
        self.next_mitigation_label.pack(fill=tk.X, padx=10, pady=5)

        # "Mechanic two ahead happening in X seconds" field
        self.two_ahead_mechanic_time_label = tk.Label(self.root, text="Mechanic two ahead happening in: N/A", font=("Helvetica", 12))
        self.two_ahead_mechanic_time_label.pack(pady=5)

        # Load the initial mitigation plan (will be overwritten when the fight starts)
        self.current_plan = None
        self.mechanics = []
        self.current_mechanic = 0
        self.start_time = None
        self.fight_started = False
        self.next_mechanic_time = None
        self.two_ahead_mechanic_time = None

        # Keybindings
        keyboard.add_hotkey('shift+T', self.start_fight)
        keyboard.add_hotkey('shift+right', self.advance_mechanic_manual)
        keyboard.add_hotkey('shift+left', self.go_back_mechanic_manual)
        keyboard.add_hotkey('shift+q', self.close_program)
        keyboard.add_hotkey('shift+}', self.restart_fight)

        # Start the GUI loop in a separate thread
        threading.Thread(target=self.update_timer, daemon=True).start()
        self.root.mainloop()

    def populate_plan_dropdown(self):
        """Populates the dropdown menu with all .txt files in the program's directory."""
        dir_path = os.path.dirname(os.path.realpath(__file__))
        txt_files = [f for f in os.listdir(dir_path) if f.endswith('.txt')]
        self.plan_combobox['values'] = txt_files
        if txt_files:
            self.plan_combobox.current(0) 

    def load_mechanics(self, filename):
        """Loads the mitigation plan from the selected file."""
        print(filename)
        file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), filename)
        print(file_path)
        mechanics = []
        with open(file_path, 'r') as file:
            mechanic = {}
            for line in file:
                line = line.strip()
                if line.startswith("Mechanic:"):
                    if mechanic:
                        mechanics.append(mechanic)
                    mechanic = {'name': line.split(": ")[1].strip()}
                elif line.startswith("Notes:"):
                    mechanic['notes'] = line.split(": ")[1].strip()
                elif line.startswith("Mitigation:"):
                    mechanic['mitigation'] = line.split(": ")[1].strip()
                elif line.startswith("Time:"):
                    mechanic['time'] = self.time_to_seconds(line.split(": ")[1].strip())
            if mechanic:
                mechanics.append(mechanic)
        return mechanics

    def time_to_seconds(self, time_str):
        minutes, seconds = map(int, time_str.split(":"))
        return minutes * 60 + seconds

    def close_program(self):
        """Closes the program when called."""
        print("Closing program...")
        self.root.quit()  # Stops the tkinter mainloop
        sys.exit(0)  # Exits the program

    def start_fight(self):
        if not self.fight_started:
            # Load the selected mitigation plan
            self.current_plan = self.plan_combobox.get()
            if self.current_plan:
                self.mechanics = self.load_mechanics(self.current_plan)
                self.start_time = time.time()
                self.fight_started = True
                self.update_mechanic_display()  # Preload the first mechanic
                print(f"Fight started with plan: {self.current_plan}")
                
                # Hide the dropdown and label after the fight starts
                self.plan_combobox.pack_forget()
                self.plan_label.pack_forget()
            else:
                print("No plan selected!")
        else:
            print("Fight already started!")

    def restart_fight(self):
        """Restarts the program from the beginning, resetting all values to the initial state."""
        self.current_mechanic = 0
        self.fight_started = False
        self.start_time = None
        self.next_mechanic_time = None
        self.two_ahead_mechanic_time = None

        self.reset_ui_elements()
        print("Fight reset!")


    def advance_mechanic_manual(self):
        if self.fight_started and self.current_mechanic < len(self.mechanics) - 1:
            self.start_time = time.time() - self.mechanics[self.current_mechanic]['time']
            # Set the timer to the current mechanic's time when manually advancing
            self.update_mechanic_display(manual=True)
            print(f"Advanced to mechanic {self.current_mechanic + 1}")

    def go_back_mechanic_manual(self):
        for _ in range(2):
            if self.fight_started and self.current_mechanic > 0:
                self.current_mechanic -= 1
                # Set the timer to the current mechanic's time when manually going back
                self.start_time = time.time() - self.mechanics[self.current_mechanic]['time']
                self.update_mechanic_display(manual=True)
                print(f"Went back to mechanic {self.current_mechanic + 1}")

    def advance_mechanic(self):
        if self.fight_started and self.current_mechanic < len(self.mechanics) - 1:
            self.current_mechanic += 1
            self.update_mechanic_display()
            print(f"Advanced to mechanic {self.current_mechanic + 1}")

    def go_back_mechanic(self):
        if self.fight_started and self.current_mechanic > 0:
            self.current_mechanic -= 1
            self.update_mechanic_display()
            print(f"Went back to mechanic {self.current_mechanic + 1}")

    def update_mechanic_display(self, manual=False):
        if self.fight_started and self.mechanics:
            mechanic = self.mechanics[self.current_mechanic]
            self.mechanic_label.config(text=f"Mechanic: {mechanic['name']}")
            self.notes_label.config(text=f"Notes: {mechanic['notes']}")
            self.mitigation_label.config(text=f"{mechanic['mitigation']}")
            
            # Don't reset the timer when automatically advancing mechanics
            if manual:
                self.start_time = time.time() - mechanic['time']  # Adjust start time only on manual input

            # Calculate and store the next mechanic's time (if available)
            if self.current_mechanic + 1 < len(self.mechanics):
                next_mechanic = self.mechanics[self.current_mechanic + 1]
                self.next_mechanic_label.config(text=f"Next: {next_mechanic['name']}")
                self.next_mitigation_label.config(text=f"{next_mechanic['mitigation']}")
                self.next_mechanic_time = next_mechanic['time']
            else:
                self.next_mechanic_label.config(text="Next: N/A")
                self.next_mitigation_label.config(text="Mitigation: N/A")
                self.next_mechanic_time = None  # No next mechanic

            # Update two-ahead mechanic information if available
            if self.current_mechanic + 1 < len(self.mechanics):
                two_ahead_mechanic = self.mechanics[self.current_mechanic + 1]
                self.two_ahead_mechanic_time = two_ahead_mechanic['time']
            else:
                self.two_ahead_mechanic_time_label.config(text="Mechanic two ahead happening in: N/A")
                self.two_ahead_mechanic_time = None  # No mechanic two ahead


    def update_timer(self):
        while True:
            if self.fight_started:
                elapsed_time = int(time.time() - self.start_time)
                minutes = elapsed_time // 60
                seconds = elapsed_time % 60
                self.timer_label.config(text=f"Time: {minutes:02}:{seconds:02}")

                # Countdown for the current mechanic
                current_mechanic_time = self.mechanics[self.current_mechanic]['time']
                time_until_current_mechanic = current_mechanic_time - elapsed_time

                if time_until_current_mechanic > 0:
                    self.next_mechanic_time_label.config(text=f"Mechanic happening in: {time_until_current_mechanic} seconds")
                else:
                    self.next_mechanic_time_label.config(text="Mechanic happening now!")
                    self.advance_mechanic()  # Automatically advance to next mechanic when time reaches 0

                # Countdown for the mechanic two ahead (if available)
                if self.two_ahead_mechanic_time is not None:
                    time_until_two_ahead_mechanic = self.two_ahead_mechanic_time - elapsed_time
                    if time_until_two_ahead_mechanic > 0:
                        self.two_ahead_mechanic_time_label.config(text=f"Mechanic two ahead happening in: {time_until_two_ahead_mechanic} seconds")
                    else:
                        self.two_ahead_mechanic_time_label.config(text="Mechanic two ahead happening now!")
                else:
                    self.two_ahead_mechanic_time_label.config(text="Mechanic two ahead happening in: N/A")

            time.sleep(1)

    def reset_ui_elements(self):
        """Removes and reloads the UI elements in the correct order."""
        # Remove all elements
        self.plan_combobox.pack_forget()
        self.plan_label.pack_forget()
        self.mechanic_label.pack_forget()
        self.notes_label.pack_forget()
        self.mitigation_label.pack_forget()
        self.timer_label.pack_forget()
        self.next_mechanic_time_label.pack_forget()
        self.canvas.pack_forget()
        self.next_mechanic_label.pack_forget()
        self.next_mitigation_label.pack_forget()
        self.two_ahead_mechanic_time_label.pack_forget()

        # Repack elements in correct order
        self.plan_label.pack(pady=5)
        self.plan_combobox.pack(pady=5)
        self.mechanic_label.pack(pady=10)
        self.notes_label.pack(pady=10)
        self.mitigation_label.pack(pady=10)
        self.timer_label.pack(pady=10)
        self.next_mechanic_time_label.pack(pady=5)
        self.canvas.pack(fill=tk.X, padx=10, pady=5)
        self.next_mechanic_label.pack(fill=tk.X, padx=10, pady=5)
        self.next_mitigation_label.pack(fill=tk.X, padx=10, pady=5)
        self.two_ahead_mechanic_time_label.pack(pady=5)

        self.mechanic_label.config(text="Mechanic: Waiting...")
        self.notes_label.config(text="Notes: N/A")
        self.mitigation_label.config(text="Mitigation: N/A")
        self.timer_label.config(text="Time: 00:00")
        self.next_mechanic_time_label.config(text="Mechanic happening in: N/A")
        self.next_mechanic_label.config(text="Next: N/A")
        self.next_mitigation_label.config(text="Mitigation: N/A")
        self.two_ahead_mechanic_time_label.config(text="Mechanic two ahead happening in: N/A")



if __name__ == "__main__":
    MitigationOverlay()
