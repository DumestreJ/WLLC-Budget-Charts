import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from Chart_Engine import *  # Imports cleanly from your support module


class InteractiveDashboard:
    def __init__(self, window):
        self.root = window
        self.root.title("Interactive Church Budget Dashboard")
        self.root.configure(bg='#111111')
        self.root.geometry("1300x750")
        self.root.minsize(1000, 550)

        # Proportional weights (1:5 ratio) for a clean sidebar split
        self.root.columnconfigure(0, weight=1, uniform="group1")
        self.root.columnconfigure(1, weight=5, uniform="group1")
        self.root.rowconfigure(0, weight=1)

        self.income_inputs, self.expense_inputs = [], []
        self.income_sizes, self.income_labels = [], []
        self.expense_sizes, self.expense_labels = [], []
        self.total_income, self.total_expenses = 429000, 453400

        # Master geometry size caching variables
        self.current_width = 0
        self.current_height = 0

        # Initialize master figure containers
        self.fig_income = plt.figure(figsize=(4.5, 4.5), facecolor='#111111')
        self.fig_expense = plt.figure(figsize=(4.5, 4.5), facecolor='#111111')

        # Keep track of active canvas container properties to prevent background leaks
        self.canvas_inc = None
        self.canvas_exp = None

        self.create_left_panel()
        self.create_right_panel()
        self.load_initial_data()

        # Clean, unified event listeners (no duplicate hooks or experimental bindings)
        self.root.bind("<Configure>", self.on_resize)
        self.root.bind("<Map>", lambda e: self.root.after(60, self.force_full_maximize))

        # Intercepts clicking the native window "X" handle and kills the background engine immediately
        self.root.protocol("WM_DELETE_WINDOW", lambda: (self.root.destroy(), sys.exit()))

    def force_full_maximize(self):
        """Forces a clean layout bypass to ensure charts auto-maximize on full screen handles."""
        self.on_resize(forced=True)

    def create_left_panel(self):
        panel_container = tk.Frame(self.root, bg='#1e1e1e')
        panel_container.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        panel_container.rowconfigure(0, weight=1)
        panel_container.rowconfigure(1, weight=0)
        panel_container.columnconfigure(0, weight=1)

        scroll_container = tk.Frame(panel_container, bg='#1e1e1e')
        scroll_container.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)

        canvas = tk.Canvas(scroll_container, bg='#1e1e1e', highlightthickness=0)
        scrollbar = ttk.Scrollbar(scroll_container, orient="vertical", command=canvas.yview)

        # CHANGED: Dedicated self.scroll_frame container to hold rows and handles
        self.scroll_frame = tk.Frame(canvas, bg='#1e1e1e')
        self.scroll_frame.columnconfigure(0, weight=1)

        # Blocks typing updates or click events from triggering false container focus resets
        self.scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")) if e.widget == self.scroll_frame else None)
        canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, padx=2, pady=5)
        scrollbar.pack(side="right", fill="y")

        actions_frame = tk.Frame(panel_container, bg='#1e1e1e')
        actions_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")

        update_btn = tk.Button(actions_frame, text="Update Charts", command=self.process_inputs,
                               bg='#00F0FF', fg='black', font=('Arial', 10, 'bold'), relief=tk.RAISED, pady=5)
        update_btn.pack(fill="x", pady=3)

        csv_btn = tk.Button(actions_frame, text="Update CSV File", command=self.save_to_csv,
                            bg='#FFB800', fg='black', font=('Arial', 10, 'bold'), relief=tk.RAISED, pady=5)
        csv_btn.pack(fill="x", pady=3)

        save_btn = tk.Button(actions_frame, text="Save Charts to Folder", command=self.save_charts,
                             bg='#00FF66', fg='black', font=('Arial', 10, 'bold'), relief=tk.RAISED, pady=5)
        save_btn.pack(fill="x", pady=3)

    def create_right_panel(self):
        self.main_frame = tk.Frame(self.root, bg='#111111')
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

        self.main_frame.rowconfigure(0, weight=1)
        self.main_frame.columnconfigure(0, weight=1)

        self.chart_holder = tk.Frame(self.main_frame, bg='#111111')
        self.chart_holder.grid(row=0, column=0, sticky="")

        self.canvas_inc = FigureCanvasTkAgg(self.fig_income, master=self.chart_holder)
        self.canvas_inc.get_tk_widget().grid(row=0, column=0, padx=15, pady=5)

        self.canvas_exp = FigureCanvasTkAgg(self.fig_expense, master=self.chart_holder)
        self.canvas_exp.get_tk_widget().grid(row=0, column=1, padx=15, pady=5)

    def add_input_row(self, master, label_text, default_val, is_total=False):
        row = tk.Frame(master, bg='#1e1e1e')
        row.pack(fill="x", pady=4, padx=5)

        lbl_var = tk.StringVar(value=label_text)
        lbl_entry = tk.Entry(row, textvariable=lbl_var, bg='#2a2a2a', fg='white', insertbackground='white',
                             font=('Arial', 9), width=11)
        lbl_entry.pack(side="left", padx=2)
        if is_total:
            lbl_entry.config(state="disabled", disabledbackground='#1e1e1e', disabledforeground='#00F0FF')

        val_var = tk.StringVar(value=str(default_val))
        val_entry = tk.Entry(row, textvariable=val_var, bg='#2a2a2a', fg='white', insertbackground='white',
                             font=('Arial', 9, 'bold'), width=8, justify="right")
        val_entry.pack(side="right", padx=2)

        # --- ADD THESE CODES TO FORCE FOCUS RETENTION ---
        # When you left-click (<Button-1>) any text box, it lets Tkinter handle its internal scroll
        # configurations first, and 10 milliseconds later, it yanks your active cursor focus right back!
        if not is_total:
            lbl_entry.bind("<Button-1>", lambda e: self.root.after(10, lambda: lbl_entry.focus_set()))
        val_entry.bind("<Button-1>", lambda e: self.root.after(10, lambda: val_entry.focus_set()))

        return lbl_var, val_var

    def add_input_row(self, master, label_text, default_val, is_total=False):
        row = tk.Frame(master, bg='#1e1e1e')
        row.pack(fill="x", pady=4, padx=5)

        lbl_var = tk.StringVar(value=label_text)
        lbl_entry = tk.Entry(row, textvariable=lbl_var, bg='#2a2a2a', fg='white', insertbackground='white',
                             font=('Arial', 9), width=11)
        lbl_entry.pack(side="left", padx=2)
        if is_total:
            lbl_entry.config(state="disabled", disabledbackground='#1e1e1e', disabledforeground='#00F0FF')

        val_var = tk.StringVar(value=str(default_val))
        val_entry = tk.Entry(row, textvariable=val_var, bg='#2a2a2a', fg='white', insertbackground='white',
                             font=('Arial', 9, 'bold'), width=8, justify="right")
        val_entry.pack(side="right", padx=2)

        return lbl_var, val_var

    def load_initial_data(self):
        desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
        csv_filename = os.path.join(desktop_dir, "budget_data.csv")

        # CHANGED: Create separate structural frames to cleanly group new rows sequentially
        self.inc_frame = tk.Frame(self.scroll_frame, bg='#1e1e1e')
        self.inc_frame.pack(fill="x", expand=True)

        self.exp_frame = tk.Frame(self.scroll_frame, bg='#1e1e1e')
        self.exp_frame.pack(fill="x", expand=True)

        if not os.path.exists(csv_filename):
            messagebox.showwarning("File Not Found", "Budget file not found on Desktop. Loading hardcoded defaults.")
            self.load_hardcoded_defaults()
            return

        import csv
        try:
            with open(csv_filename, mode='r', newline='', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)

                # Render the Income section headers
                tk.Label(self.inc_frame, text="INCOME CONFIG", fg='#00F0FF', bg='#1e1e1e',
                         font=('Arial', 9, 'bold')).pack(anchor="w", pady=(10, 4), padx=5)
                expense_header_printed = False

                for row in reader:
                    dtype = row['Type'].strip()
                    category = row['Category'].strip()
                    amount = float(row['Amount'])

                    if dtype == "Income":
                        if "Total" in category:
                            _, self.inc_total_val = self.add_input_row(self.inc_frame, category, amount, is_total=True)
                        else:
                            self.income_inputs.append(self.add_input_row(self.inc_frame, category, amount))

                    elif dtype == "Expense":
                        if not expense_header_printed:
                            # Render the Expense section headers
                            tk.Label(self.exp_frame, text="EXPENSE CONFIG", fg='#FF007F', bg='#1e1e1e',
                                     font=('Arial', 9, 'bold')).pack(anchor="w", pady=(20, 4), padx=5)
                            expense_header_printed = True

                        if "Total" in category:
                            _, self.exp_total_val = self.add_input_row(self.exp_frame, category, amount, is_total=True)
                        else:
                            self.expense_inputs.append(self.add_input_row(self.exp_frame, category, amount))

            # --- ADD THIS: Render the dynamic add buttons right beneath their sections ---
            tk.Button(self.inc_frame, text="+ Add Income Item", command=lambda: self.add_blank_row("Income"),
                      bg='#111111', fg='#00F0FF', font=('Arial', 8, 'bold'), bd=0, cursor="hand2").pack(anchor="w",
                                                                                                        padx=7, pady=5)

            tk.Button(self.exp_frame, text="+ Add Expense Item", command=lambda: self.add_blank_row("Expense"),
                      bg='#111111', fg='#FF007F', font=('Arial', 8, 'bold'), bd=0, cursor="hand2").pack(anchor="w",
                                                                                                        padx=7, pady=5)

            self.process_inputs()
        except Exception as e:
            messagebox.showerror("CSV Load Error", f"Could not parse CSV:\n{str(e)}")
            self.load_hardcoded_defaults()

    def load_hardcoded_defaults(self):
        # Render the Income section headers and core text boxes
        tk.Label(self.inc_frame, text="INCOME CONFIG", fg='#00F0FF', bg='#1e1e1e', font=('Arial', 9, 'bold')).pack(
            anchor="w", pady=(10, 4), padx=5)
        _, self.inc_total_val = self.add_input_row(self.inc_frame, "Total Income", 429000, is_total=True)
        self.income_inputs.append(self.add_input_row(self.inc_frame, "Giving", 383000))
        self.income_inputs.append(self.add_input_row(self.inc_frame, "Partners", 42000))

        # --- FIXED: Append the "+ Add Income Item" button to the hardcoded fallback layout ---
        tk.Button(self.inc_frame, text="+ Add Income Item", command=lambda: self.add_blank_row("Income"),
                  bg='#111111', fg='#00F0FF', font=('Arial', 8, 'bold'), bd=0, cursor="hand2").pack(anchor="w", padx=7,
                                                                                                    pady=5)

        # Render the Expense section headers and core text boxes
        tk.Label(self.exp_frame, text="EXPENSE CONFIG", fg='#FF007F', bg='#1e1e1e', font=('Arial', 9, 'bold')).pack(
            anchor="w", pady=(20, 4), padx=5)
        _, self.exp_total_val = self.add_input_row(self.exp_frame, "Total Expense", 453400, is_total=True)
        self.expense_inputs.append(self.add_input_row(self.exp_frame, "Clergy", 211400))
        self.expense_inputs.append(self.add_input_row(self.exp_frame, "Lay Ministry", 109400))
        self.expense_inputs.append(self.add_input_row(self.exp_frame, "Building", 64900))
        self.expense_inputs.append(self.add_input_row(self.exp_frame, "Admin", 20000))
        self.expense_inputs.append(self.add_input_row(self.exp_frame, "Worship", 7700))
        self.expense_inputs.append(self.add_input_row(self.exp_frame, "Faith Form.", 5000))

        # --- FIXED: Append the "+ Add Expense Item" button to the hardcoded fallback layout ---
        tk.Button(self.exp_frame, text="+ Add Expense Item", command=lambda: self.add_blank_row("Expense"),
                  bg='#111111', fg='#FF007F', font=('Arial', 8, 'bold'), bd=0, cursor="hand2").pack(anchor="w", padx=7,
                                                                                                    pady=5)

        self.process_inputs()

    def process_inputs(self):
        try:
            self.is_updating = True
            self.total_income = float(self.inc_total_val.get())
            inc_candidates = [(l.get().strip(), float(v.get() or 0.0)) for l, v in self.income_inputs]
            inc_candidates.sort(key=lambda x: x[1], reverse=True)
            other_inc = max(0.0, self.total_income - sum(x[1] for x in inc_candidates))

            # Pack categories into final lists, dropping 'Other Income' if it is near zero
            self.income_labels = [x[0] for x in inc_candidates]
            self.income_sizes = [x[1] for x in inc_candidates]
            if other_inc >= 1.0:  # Threshold filter: skips if less than $1
                self.income_labels.append("Other Income")
                self.income_sizes.append(other_inc)

            self.total_expenses = float(self.exp_total_val.get())
            exp_candidates = [(l.get().strip(), float(v.get() or 0.0)) for l, v in self.expense_inputs]
            exp_candidates.sort(key=lambda x: x[1], reverse=True)
            other_exp = max(0.0, self.total_expenses - sum(x[1] for x in exp_candidates))

            # Pack categories into final lists, dropping 'Other Expenses' if it is near zero
            self.expense_labels = [x[0] for x in exp_candidates]
            self.expense_sizes = [x[1] for x in exp_candidates]
            if other_exp >= 1.0:  # Threshold filter: skips if less than $1
                self.expense_labels.append("Other Expenses")
                self.expense_sizes.append(other_exp)

            # Clear cache and run the clean layout pass
            self.current_width = 0
            self.root.update_idletasks()
            self.on_resize()
            self.is_updating = False

        except ValueError:
            self.is_updating = False  # Reset on error pass
            messagebox.showerror("Parsing Error", "Please ensure all entry boxes contain valid numeric digits.")


    def add_blank_row(self, section_type):
        """Spins up a completely blank input field row at the bottom of the targeted section framework."""
        if section_type == "Income":
            # Appends row to your active tracking data structures
            new_row = self.add_input_row(self.inc_frame, "New Income", 0.0)
            self.income_inputs.append(new_row)
        else:
            new_row = self.add_input_row(self.exp_frame, "New Expense", 0.0)
            self.expense_inputs.append(new_row)

        # Forces the layout engine scroll boundary parameters to update immediately
        self.scroll_frame.update_idletasks()

    def on_resize(self, event=None, forced=False):
        # 1. STRICT ISOLATION GATE: Only execute if it's a direct programmatic call,
        # or if the signal matches the root window exactly.
        if event and event.widget != self.root:
            return

        w_width, w_height = self.root.winfo_width(), self.root.winfo_height()
        if w_width < 10 or w_height < 10:
            return

        # Cache variables track layout properties directly
        self.current_width = w_width
        self.current_height = w_height

        # Proportional scalar calculations (fixes the jittering)
        right_panel_w = (w_width * 5 // 6)
        available_w = (right_panel_w - 85) // 2
        available_h = w_height - 85
        size_pixels = max(150, min(available_w, available_h))
        size_inches = size_pixels / 100.0

        font_sz = min(9.5, max(7.2, 7.2 + (size_inches * 0.40)))
        thresh = min(0.24, max(0.15, 0.26 - (size_inches * 0.022)))

        # Update the figures cleanly in place (no fig.clf(), no ax.clear() conflicts)
        create_smart_pie(self.fig_income, self.income_sizes, self.income_labels, self.total_income,
                         'Budget Income Breakdown', '#00F0FF', font_sz, thresh)
        create_smart_pie(self.fig_expense, self.expense_sizes, self.expense_labels, self.total_expenses,
                         'Budget Expenses Breakdown', '#FF007F', font_sz, thresh)

        self.fig_income.set_size_inches(size_inches, size_inches)
        self.fig_expense.set_size_inches(size_inches, size_inches)

        # FIXED: Explicitly refresh the layout boxes without destroying the widgets.
        # This completely preserves text focus across PyCharm and the compiled EXE!
        if self.canvas_inc and self.canvas_exp:
            self.canvas_inc.get_tk_widget().configure(width=size_pixels, height=size_pixels)
            self.canvas_exp.get_tk_widget().configure(width=size_pixels, height=size_pixels)
            self.canvas_inc.draw()
            self.canvas_exp.draw()

    def save_charts(self):
        desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
        folder_selected = filedialog.askdirectory(title="Select Folder to Save PNG Charts", initialdir=desktop_dir)
        if folder_selected:
            try:
                inc_path = os.path.join(folder_selected, "income_budget.png")
                exp_path = os.path.join(folder_selected, "expenses_budget.png")

                create_smart_pie(self.fig_income, self.income_sizes, self.income_labels, self.total_income,
                                 'Budget Income Breakdown', '#00F0FF', 9.5, 0.16)
                create_smart_pie(self.fig_expense, self.expense_sizes, self.expense_labels, self.total_expenses,
                                 'Budget Expenses Breakdown', '#FF007F', 9.5, 0.16)

                self.fig_income.savefig(inc_path, dpi=300, facecolor='#111111', bbox_inches='tight')
                self.fig_expense.savefig(exp_path, dpi=300, facecolor='#111111', bbox_inches='tight')

                self.current_width = 0
                self.on_resize()
                messagebox.showinfo("Success", f"Saved successfully to:\n{folder_selected}")
            except Exception as e:
                messagebox.showerror("Error", f"Could not save charts:\n{str(e)}")

    def save_to_csv(self):
        """Reads the current active GUI input boxes, filters out empty rows, and saves to the Desktop CSV."""
        desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
        csv_filename = os.path.join(desktop_dir, "budget_data.csv")

        import csv
        try:
            with open(csv_filename, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Type', 'Category', 'Amount'])

                # 1. Export active Income rows (including the locked limit row)
                writer.writerow(['Income', 'Total Income Limit', self.inc_total_val.get().strip()])
                for lbl_var, val_var in self.income_inputs:
                    lbl = lbl_var.get().strip()
                    val_str = val_var.get().strip()

                    # DELETION FILTER: If the user erased the label and the number, skip writing this row!
                    if not lbl and (val_str == "" or val_str == "0" or val_str == "0.0"):
                        continue
                    writer.writerow(['Income', lbl if lbl else "Unnamed Category", val_str if val_str else "0"])

                # 2. Export active Expense rows (including the locked target row)
                writer.writerow(['Expense', 'Total Expenses Target', self.exp_total_val.get().strip()])
                for lbl_var, val_var in self.expense_inputs:
                    lbl = lbl_var.get().strip()
                    val_str = val_var.get().strip()

                    # DELETION FILTER: If the user erased the label and the number, skip writing this row!
                    if not lbl and (val_str == "" or val_str == "0" or val_str == "0.0"):
                        continue
                    writer.writerow(['Expense', lbl if lbl else "Unnamed Category", val_str if val_str else "0"])

            # Instantly re-read the rows to refresh the sidebar layout and clear out deleted entry tracks
            self.process_inputs()
            messagebox.showinfo("Success", f"Spreadsheet successfully cleaned and saved at:\n{csv_filename}")

        except Exception as e:
            messagebox.showerror("CSV Save Error",
                                 f"Could not write data back to the spreadsheet file safely:\n{str(e)}")


# Master Main Runner
# --- REPLACE THE APPS RUNNER BLOCK AT THE VERY BOTTOM OF main.py ---

if __name__ == "__main__":
    root = tk.Tk()
    app = InteractiveDashboard(root)

    # 1. Force a complete, immediate physical draw of the desktop layout windows.
    # Unlike update_idletasks, root.update() commands the operating system to map
    # the entire window onto your monitor screen instantly, locking in its true sizes.
    root.update()

    # 2. Directly trigger the layout engine calculation loop pass.
    # Because root.update() has already locked the correct horizontal pixel width counts,
    # the charts maximize perfectly and maintain their true 6 o'clock start positions on the very first try!
    app.on_resize()

    root.mainloop()
