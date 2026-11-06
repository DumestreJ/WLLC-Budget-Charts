import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
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

        # FEATURE IMPLEMENTATION: Draggable layout container replacing static grid splitting
        self.paned_window = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, bg='#111111', bd=0, sashwidth=6)
        self.paned_window.grid(row=0, column=0, columnspan=2, sticky="nsew")

        # FEATURE IMPLEMENTATION: Custom string variables tracking chart titles
        self.income_title_var = tk.StringVar(value='Budget Income Breakdown')
        self.expense_title_var = tk.StringVar(value='Budget Expenses Breakdown')

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

        # FEATURE IMPLEMENTATION: Place the slider position on initialization
        self.root.update()
        self.paned_window.sash_place(0, 220, 0)

        # Clean, unified event listeners (no duplicate hooks or experimental bindings)
        self.root.bind("<Configure>", self.on_resize)
        self.root.bind("<Map>", lambda e: self.root.after(60, self.force_full_maximize))

        # Intercepts clicking the native window "X" handle and kills the background engine immediately
        self.root.protocol("WM_DELETE_WINDOW", lambda: (self.root.destroy(), sys.exit()))

    def force_full_maximize(self):
        """Forces a clean layout bypass to ensure charts auto-maximize on full screen handles."""
        self.on_resize(forced=True)

    def create_left_panel(self):
        # Parent set to self.paned_window and added to the slider layout split
        panel_container = tk.Frame(self.paned_window, bg='#1e1e1e')
        self.paned_window.add(panel_container, minsize=200)

        panel_container.rowconfigure(0, weight=1)
        panel_container.rowconfigure(1, weight=0)
        panel_container.columnconfigure(0, weight=1)

        scroll_container = tk.Frame(panel_container, bg='#1e1e1e')
        scroll_container.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)

        canvas = tk.Canvas(scroll_container, bg='#1e1e1e', highlightthickness=0)
        scrollbar = ttk.Scrollbar(scroll_container, orient="vertical", command=canvas.yview)

        self.scroll_frame = tk.Frame(canvas, bg='#1e1e1e')
        self.scroll_frame.columnconfigure(0, weight=1)

        # FIXED: Forces the internal scroll frame to fill the dynamic canvas width on resize
        self.scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")) if e.widget == self.scroll_frame else None)
        canvas_frame_id = canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(canvas_frame_id, width=e.width))

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

        # FIXED: Updated label string to reflect the automated desktop destination path
        save_btn = tk.Button(actions_frame, text="Save Charts to Desktop", command=self.save_charts,
                             bg='#00FF66', fg='black', font=('Arial', 10, 'bold'), relief=tk.RAISED, pady=5)
        save_btn.pack(fill="x", pady=3)

    def create_right_panel(self):
        # FEATURE IMPLEMENTATION: Parent set to self.paned_window and added to the sash layout splits
        self.main_frame = tk.Frame(self.paned_window, bg='#111111')
        self.paned_window.add(self.main_frame, minsize=400)

        # FEATURE IMPLEMENTATION: Bind real-time panel stretching straight to the layout engine
        self.main_frame.bind("<Configure>", lambda e: self.on_resize(forced=True))

        self.main_frame.rowconfigure(0, weight=1)
        self.main_frame.columnconfigure(0, weight=1)

        self.chart_holder = tk.Frame(self.main_frame, bg='#111111')
        self.chart_holder.grid(row=0, column=0, sticky="")

        self.canvas_inc = FigureCanvasTkAgg(self.fig_income, master=self.chart_holder)
        self.canvas_inc.get_tk_widget().grid(row=0, column=0, padx=15, pady=5)

        self.canvas_exp = FigureCanvasTkAgg(self.fig_expense, master=self.chart_holder)
        self.canvas_exp.get_tk_widget().grid(row=0, column=1, padx=15, pady=5)

    def add_title_row(self, master, title_var, text_color):
        """FEATURE IMPLEMENTATION: Creates an editable title text box for budget headings."""
        row = tk.Frame(master, bg='#1e1e1e')
        row.pack(fill="x", pady=2, padx=5)

        lbl = tk.Label(row, text="Title:", fg='#aaaaaa', bg='#1e1e1e', font=('Arial', 8))
        lbl.pack(side="left", padx=2)

        title_entry = tk.Entry(row, textvariable=title_var, bg='#2a2a2a', fg=text_color,
                               insertbackground='white', font=('Arial', 9, 'italic'))
        title_entry.pack(side="left", fill="x", expand=True, padx=2)
        title_entry.bind("<Button-1>", lambda e: self.root.after(10, lambda: title_entry.focus_set()))

    def add_input_row(self, master, label_text, default_val, is_total=False):
        row = tk.Frame(master, bg='#1e1e1e')
        row.pack(fill="x", pady=4, padx=5)

        lbl_var = tk.StringVar(value=label_text)
        # FIXED: Added width=1 so Tkinter allows the entry box to compress down to a minimum footprint
        lbl_entry = tk.Entry(row, textvariable=lbl_var, bg='#2a2a2a', fg='white', insertbackground='white',
                             font=('Arial', 9), width=1)
        lbl_entry.pack(side="left", fill="x", expand=True, padx=2)

        if is_total:
            lbl_entry.config(state="disabled", disabledbackground='#1e1e1e', disabledforeground='#00F0FF')

        try:
            val_num = float(default_val)
            val_str = str(int(val_num)) if val_num.is_integer() else f"{val_num:.2f}"
        except (ValueError, TypeError):
            val_str = str(default_val)

        val_var = tk.StringVar(value=val_str)
        val_entry = tk.Entry(row, textvariable=val_var, bg='#2a2a2a', fg='white', insertbackground='white',
                             font=('Arial', 9, 'bold'), width=8, justify="right")
        val_entry.pack(side="right", padx=2, fill=None, expand=False)

        if not is_total:
            lbl_entry.bind("<Button-1>", lambda e: self.root.after(10, lambda: lbl_entry.focus_set()))
        val_entry.bind("<Button-1>", lambda e: self.root.after(10, lambda: val_entry.focus_set()))

        lbl_var.trace_add("write", lambda *args: self.process_inputs(is_live=True))
        val_var.trace_add("write", lambda *args: self.process_inputs(is_live=True))

        return lbl_var, val_var

    def load_initial_data(self):
        desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
        csv_filename = os.path.join(desktop_dir, "budget_data.csv")

        # CHANGED: Create separate structural frames to cleanly group new rows sequentially
        self.inc_frame = tk.Frame(self.scroll_frame, bg='#1e1e1e')
        self.inc_frame.pack(fill="x", expand=True)

        self.exp_frame = tk.Frame(self.scroll_frame, bg='#1e1e1e')
        self.exp_frame.pack(fill="x", expand=True)

        # FEATURE IMPLEMENTATION: Insert section subheaders and editable title text rows
        tk.Label(self.inc_frame, text="INCOME CONFIG", fg='#00F0FF', bg='#1e1e1e',
                 font=('Arial', 9, 'bold')).pack(anchor="w", pady=(10, 4), padx=5)
        self.add_title_row(self.inc_frame, self.income_title_var, '#00F0FF')
        expense_header_printed = False

        if not os.path.exists(csv_filename):
            messagebox.showwarning("File Not Found", "Budget file not found on Desktop. Loading hardcoded defaults.")
            self.load_hardcoded_defaults()
            return

        import csv
        try:
            with open(csv_filename, mode='r', newline='', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    dtype = row['Type'].strip()
                    category = row['Category'].strip()
                    amount_str = row.get('Amount', '0').strip()
                    amount = float(amount_str) if amount_str else 0.0

                    if dtype == "Income":
                        # FEATURE IMPLEMENTATION: Read customized header title from specific category flag
                        if category == "Income Title":
                            self.income_title_var.set(row.get('Title text', 'Budget Income Breakdown'))
                        elif "Total" in category:
                            _, self.inc_total_val = self.add_input_row(self.inc_frame, category, amount, is_total=True)
                        else:
                            self.income_inputs.append(self.add_input_row(self.inc_frame, category, amount))

                    elif dtype == "Expense":
                        if not expense_header_printed:
                            # Render the Expense section headers
                            tk.Label(self.exp_frame, text="EXPENSE CONFIG", fg='#FF007F', bg='#1e1e1e',
                                     font=('Arial', 9, 'bold')).pack(anchor="w", pady=(20, 4), padx=5)
                            self.add_title_row(self.exp_frame, self.expense_title_var, '#FF007F')
                            expense_header_printed = True

                        # FEATURE IMPLEMENTATION: Read customized header title from specific category flag
                        if category == "Expense Title":
                            self.expense_title_var.set(row.get('Title text', 'Budget Expenses Breakdown'))
                        elif "Total" in category:
                            _, self.exp_total_val = self.add_input_row(self.exp_frame, category, amount, is_total=True)
                        else:
                            self.expense_inputs.append(self.add_input_row(self.exp_frame, category, amount))

            # Generate the persistent uneditable gray readout widgets
            self.inc_other_lbl = tk.Label(self.inc_frame, fg='#777777', bg='#1e1e1e', font=('Arial', 9, 'italic'))
            self.exp_other_lbl = tk.Label(self.exp_frame, fg='#777777', bg='#1e1e1e', font=('Arial', 9, 'italic'))

            tk.Button(self.inc_frame, text="+ Add Income Item", command=lambda: self.add_blank_row("Income"),
                      bg='#111111', fg='#00F0FF', font=('Arial', 8, 'bold'), bd=0, cursor="hand2").pack(anchor="w",
                                                                                                        padx=7, pady=5)

            tk.Button(self.exp_frame, text="+ Add Expense Item", command=lambda: self.add_blank_row("Expense"),
                      bg='#111111', fg='#FF007F', font=('Arial', 8, 'bold'), bd=0, cursor="hand2").pack(anchor="w",
                                                                                                        padx=7, pady=5)
            # Add real-time event listener to update titles dynamically on window loop typing
            self.income_title_var.trace_add("write", lambda *args: self.process_inputs(is_live=True))
            self.expense_title_var.trace_add("write", lambda *args: self.process_inputs(is_live=True))

            self.process_inputs()

        except Exception as e:
            messagebox.showerror("CSV Load Error", f"Could not parse CSV:\n{str(e)}")
            self.load_hardcoded_defaults()

    def load_hardcoded_defaults(self):
        # Render the Income section headers and core text boxes
        _, self.inc_total_val = self.add_input_row(self.inc_frame, "Total Income", 429000, is_total=True)
        self.income_inputs.append(self.add_input_row(self.inc_frame, "Giving", 383000))
        self.income_inputs.append(self.add_input_row(self.inc_frame, "Partners", 42000))

        # Generate the persistent uneditable gray readout widgets
        self.inc_other_lbl = tk.Label(self.inc_frame, fg='#777777', bg='#1e1e1e', font=('Arial', 9, 'italic'))

        # --- FIXED: Append the "+ Add Income Item" button to the hardcoded fallback layout ---
        tk.Button(self.inc_frame, text="+ Add Income Item", command=lambda: self.add_blank_row("Income"),
                  bg='#111111', fg='#00F0FF', font=('Arial', 8, 'bold'), bd=0, cursor="hand2").pack(anchor="w", padx=7,
                                                                                                    pady=5)

        # Render the Expense section headers and core text boxes
        tk.Label(self.exp_frame, text="EXPENSE CONFIG", fg='#FF007F', bg='#1e1e1e', font=('Arial', 9, 'bold')).pack(
            anchor="w", pady=(20, 4), padx=5)
        self.add_title_row(self.exp_frame, self.expense_title_var, '#FF007F')
        _, self.exp_total_val = self.add_input_row(self.exp_frame, "Total Expense", 453400, is_total=True)
        self.expense_inputs.append(self.add_input_row(self.exp_frame, "Clergy", 211400))
        self.expense_inputs.append(self.add_input_row(self.exp_frame, "Lay Ministry", 109400))
        self.expense_inputs.append(self.add_input_row(self.exp_frame, "Building", 64900))
        self.expense_inputs.append(self.add_input_row(self.exp_frame, "Admin", 20000))
        self.expense_inputs.append(self.add_input_row(self.exp_frame, "Worship", 7700))
        self.expense_inputs.append(self.add_input_row(self.exp_frame, "Faith Form.", 5000))

        # Generate the persistent uneditable gray readout widgets
        self.exp_other_lbl = tk.Label(self.exp_frame, fg='#777777', bg='#1e1e1e', font=('Arial', 9, 'italic'))

        # --- FIXED: Append the "+ Add Expense Item" button to the hardcoded fallback layout ---
        tk.Button(self.exp_frame, text="+ Add Expense Item", command=lambda: self.add_blank_row("Expense"),
                  bg='#111111', fg='#FF007F', font=('Arial', 8, 'bold'), bd=0, cursor="hand2").pack(anchor="w", padx=7,
                                                                                                    pady=5)

        # FEATURE IMPLEMENTATION: Set fallbacks to trigger auto-updates on the text tracers
        self.income_title_var.trace_add("write", lambda *args: self.process_inputs(is_live=True))
        self.expense_title_var.trace_add("write", lambda *args: self.process_inputs(is_live=True))

        self.process_inputs()

    def add_blank_row(self, section_type):
        """Spins up a completely blank input field row at the bottom of the targeted section framework."""
        if section_type == "Income":
            # FIXED: Set baseline whole number integer initialization
            new_row = self.add_input_row(self.inc_frame, "", 0)
            self.income_inputs.append(new_row)
        else:
            # FIXED: Set baseline whole number integer initialization
            new_row = self.add_input_row(self.exp_frame, "", 0)
            self.expense_inputs.append(new_row)

    def process_inputs(self, is_live=False):
        if hasattr(self, 'is_updating') and self.is_updating:
            return
        try:
            self.is_updating = True

            # Read and calculate income remainder balances
            self.total_income = float(self.inc_total_val.get() or 0.0)
            inc_candidates = [(l.get().strip(), float(v.get() or 0.0)) for l, v in self.income_inputs]
            inc_candidates.sort(key=lambda x: x[1], reverse=True)

            # FIXED: Removed max() boundary filter to allow negative dynamic remainders
            other_inc = self.total_income - sum(x[1] for x in inc_candidates)

            self.income_labels = [x[0] for x in inc_candidates]
            self.income_sizes = [x[1] for x in inc_candidates]

            # FEATURE IMPLEMENTATION: Handle dynamic red alert foreground colors on negative balances
            if other_inc < 0:
                self.inc_other_lbl.config(text=f"Other Balance: {int(other_inc)}", fg='#FF3300')
            else:
                self.inc_other_lbl.config(text=f"Other Balance: {int(other_inc)}", fg='#777777')

            # FIXED: Always render and display the readout even when unallocated remainder hits 0
            if other_inc != 0 or len(inc_candidates) > 0:
                if other_inc > 0:  # Only append slice to pie graphic if positive allocation remains
                    self.income_labels.append("Other Income")
                    self.income_sizes.append(other_inc)
                self.inc_other_lbl.pack(anchor="w", padx=7, pady=2, before=self.inc_frame.pack_slaves()[-1])

            # Read and calculate expense remainder balances
            self.total_expenses = float(self.exp_total_val.get() or 0.0)
            exp_candidates = [(l.get().strip(), float(v.get() or 0.0)) for l, v in self.expense_inputs]
            exp_candidates.sort(key=lambda x: x[1], reverse=True)

            # FIXED: Removed max() boundary filter to allow negative dynamic remainders
            other_exp = self.total_expenses - sum(x[1] for x in exp_candidates)

            self.expense_labels = [x[0] for x in exp_candidates]
            self.expense_sizes = [x[1] for x in exp_candidates]

            # FEATURE IMPLEMENTATION: Handle dynamic red alert foreground colors on negative balances
            if other_exp < 0:
                self.exp_other_lbl.config(text=f"Other Balance: {int(other_exp)}", fg='#FF3300')
            else:
                self.exp_other_lbl.config(text=f"Other Balance: {int(other_exp)}", fg='#777777')

            # FIXED: Always render and display the readout even when unallocated remainder hits 0
            if other_exp != 0 or len(exp_candidates) > 0:
                if other_exp > 0:  # Only append slice to pie graphic if positive allocation remains
                    self.expense_labels.append("Other Expenses")
                    self.expense_sizes.append(other_exp)
                self.exp_other_lbl.pack(anchor="w", padx=7, pady=2, before=self.exp_frame.pack_slaves()[-1])

            self.current_width = 0
            self.root.update_idletasks()
            self.on_resize(forced=True)
            self.is_updating = False

        except ValueError:
            self.is_updating = False
            if not is_live:
                messagebox.showerror("Parsing Error", "Please ensure all entry boxes contain valid numeric digits.")

    def on_resize(self, event=None, forced=False):
        if event and event.widget != self.root and event.widget != self.main_frame:
            return

        w_width, w_height = self.root.winfo_width(), self.root.winfo_height()
        if w_width < 10 or w_height < 10:
            return

        self.current_width = w_width
        self.current_height = w_height

        # FEATURE IMPLEMENTATION: Extract pixel bounds from sliding panel container
        right_panel_w = self.main_frame.winfo_width()
        if right_panel_w < 50:
            right_panel_w = (w_width * 5 // 6)

        available_w = (right_panel_w - 85) // 2
        available_h = w_height - 85
        size_pixels = max(150, min(available_w, available_h))
        size_inches = size_pixels / 100.0

        font_sz = min(9.5, max(7.2, 7.2 + (size_inches * 0.40)))
        thresh = min(0.24, max(0.15, 0.26 - (size_inches * 0.022)))

        # FEATURE IMPLEMENTATION: Feed custom title variables to engine dynamically
        create_smart_pie(self.fig_income, self.income_sizes, self.income_labels, self.total_income,
                         self.income_title_var.get(), '#00F0FF', font_sz, thresh)
        create_smart_pie(self.fig_expense, self.expense_sizes, self.expense_labels, self.total_expenses,
                         self.expense_title_var.get(), '#FF007F', font_sz, thresh)

        self.fig_income.set_size_inches(size_inches, size_inches)
        self.fig_expense.set_size_inches(size_inches, size_inches)

        if self.canvas_inc and self.canvas_exp:
            self.canvas_inc.get_tk_widget().configure(width=size_pixels, height=size_pixels)
            self.canvas_exp.get_tk_widget().configure(width=size_pixels, height=size_pixels)
            self.canvas_inc.draw()
            self.canvas_exp.draw()

    def save_charts(self):
        """Saves PNG charts directly to the user's desktop, skipping folder selection dialogues."""
        desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
        try:
            inc_path = os.path.join(desktop_dir, "income_budget.png")
            exp_path = os.path.join(desktop_dir, "expenses_budget.png")

            create_smart_pie(self.fig_income, self.income_sizes, self.income_labels, self.total_income,
                             self.income_title_var.get(), '#00F0FF', 9.5, 0.16)
            create_smart_pie(self.fig_expense, self.expense_sizes, self.expense_labels, self.total_expenses,
                             self.expense_title_var.get(), '#FF007F', 9.5, 0.16)

            self.fig_income.savefig(inc_path, dpi=300, facecolor='#111111', bbox_inches='tight')
            self.fig_expense.savefig(exp_path, dpi=300, facecolor='#111111', bbox_inches='tight')

            self.current_width = 0
            self.on_resize()
            messagebox.showinfo("Success", f"Saved successfully to your Desktop:\nincome_budget.png\nexpenses_budget.png")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save charts:\n{str(e)}")

    def save_to_csv(self):
        desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
        csv_filename = os.path.join(desktop_dir, "budget_data.csv")

        import csv
        try:
            with open(csv_filename, mode='w', newline='', encoding='utf-8') as f:
                # FEATURE IMPLEMENTATION: Optional 4th meta column to keep custom title state safely
                writer = csv.writer(f)
                writer.writerow(['Type', 'Category', 'Amount', 'Title text'])

                writer.writerow(['Income', 'Income Title', '0', self.income_title_var.get().strip()])
                writer.writerow(['Income', 'Total Income Limit', self.inc_total_val.get().strip(), ''])
                for lbl_var, val_var in self.income_inputs:
                    lbl = lbl_var.get().strip()
                    val_str = val_var.get().strip()
                    if not lbl and (val_str == "" or val_str == "0" or val_str == "0.0"):
                        continue
                    writer.writerow(['Income', lbl if lbl else "Unnamed Category", val_str if val_str else "0", ''])

                writer.writerow(['Expense', 'Expense Title', '0', self.expense_title_var.get().strip()])
                writer.writerow(['Expense', 'Total Expenses Target', self.exp_total_val.get().strip(), ''])
                for lbl_var, val_var in self.expense_inputs:
                    lbl = lbl_var.get().strip()
                    val_str = val_var.get().strip()
                    if not lbl and (val_str == "" or val_str == "0" or val_str == "0.0"):
                        continue
                    writer.writerow(['Expense', lbl if lbl else "Unnamed Category", val_str if val_str else "0", ''])

            self.process_inputs()
            messagebox.showinfo("Success", f"Spreadsheet successfully cleaned and saved at:\n{csv_filename}")
        except Exception as e:
            messagebox.showerror("CSV Save Error", f"Could not write data safely:\n{str(e)}")


if __name__ == "__main__":
    root = tk.Tk()
    app = InteractiveDashboard(root)
    root.update()
    app.on_resize()
    root.mainloop()
