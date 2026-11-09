import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from Chart_Engine import *  # Imports cleanly from your support module
from budget_importer import import_excel_budget

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

        # Horizontal slider panes
        self.paned_window = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, bg='#111111', bd=0, sashwidth=6)
        self.paned_window.grid(row=0, column=0, columnspan=2, sticky="nsew")

        # Custom chart header variables
        self.income_title_var = tk.StringVar(value='Budget Income Breakdown')
        self.expense_title_var = tk.StringVar(value='Budget Expenses Breakdown')

        # Relational data dictionary tracking all subcategory rows
        # Format: { "Category Name": [ ["Subcat Label", 500], ["Subcat 2", 1200] ] }
        self.subcategories = {}

        self.income_inputs, self.expense_inputs = [], []
        self.income_sizes, self.income_labels = [], []
        self.expense_sizes, self.expense_labels = [], []
        self.total_income, self.total_expenses = 429000, 453400

        # Master geometry size caching variables
        self.current_width = 0
        self.current_height = 0

        # Primary figures and click tracking lists
        self.fig_income = plt.figure(figsize=(4.5, 4.5), facecolor='#111111')
        self.fig_expense = plt.figure(figsize=(4.5, 4.5), facecolor='#111111')
        self.income_wedges = []
        self.expense_wedges = []

        # Keep track of active canvas container properties to prevent background leaks
        self.canvas_inc = None
        self.canvas_exp = None

        # FEATURE IMPLEMENTATION: Single shared floating tooltip window tracker
        self.tooltip = None

        self.create_left_panel()
        self.create_right_panel()
        self.load_initial_data()

        # Place the slider position on initialization
        self.root.update()
        self.paned_window.sash_place(0, 220, 0)

        self.root.bind("<Configure>", self.on_resize)
        self.root.bind("<Map>", lambda e: self.root.after(60, self.force_full_maximize))
        # Forces keyboard focus back to the root window container after Matplotlib draws,
        # completely preventing the startup entry field lockup.
        self.root.after(50, lambda: self.root.focus_force())


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

        self.scroll_frame.bind("<Configure>", lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")) if e.widget == self.scroll_frame else None)
        canvas_frame_id = canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(canvas_frame_id, width=e.width))

        canvas.pack(side="left", fill="both", expand=True, padx=2, pady=5)
        scrollbar.pack(side="right", fill="y")

        actions_frame = tk.Frame(panel_container, bg='#1e1e1e')
        actions_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")

        import_btn = tk.Button(actions_frame, text="Import Spreadsheet Budget",
                               command=lambda: import_excel_budget(self),
                               bg='#FF00FF', fg='black', font=('Arial', 10, 'bold'), relief=tk.RAISED, pady=5)
        import_btn.pack(fill="x", pady=3)

        update_btn = tk.Button(actions_frame, text="Update Charts", command=self.process_inputs,
                               bg='#00F0FF', fg='black', font=('Arial', 10, 'bold'), relief=tk.RAISED, pady=5)
        update_btn.pack(fill="x", pady=3)

        csv_btn = tk.Button(actions_frame, text="Update CSV File", command=self.save_to_csv,
                            bg='#FFB800', fg='black', font=('Arial', 10, 'bold'), relief=tk.RAISED, pady=5)
        csv_btn.pack(fill="x", pady=3)

        save_btn = tk.Button(actions_frame, text="Save Charts to Desktop", command=self.save_charts,
                             bg='#00FF66', fg='black', font=('Arial', 10, 'bold'), relief=tk.RAISED, pady=5)
        save_btn.pack(fill="x", pady=3)

    def create_right_panel(self):
        # Parent set to self.paned_window and added to the sash layout splits
        self.main_frame = tk.Frame(self.paned_window, bg='#111111')
        self.paned_window.add(self.main_frame, minsize=400)

        # Bind real-time panel stretching straight to the layout engine
        self.main_frame.bind("<Configure>", lambda e: self.on_resize(forced=True))

        self.main_frame.rowconfigure(0, weight=1)
        self.main_frame.columnconfigure(0, weight=1)

        self.chart_holder = tk.Frame(self.main_frame, bg='#111111')
        self.chart_holder.grid(row=0, column=0, sticky="")

        self.canvas_inc = FigureCanvasTkAgg(self.fig_income, master=self.chart_holder)
        self.canvas_inc.get_tk_widget().grid(row=0, column=0, padx=15, pady=5)

        self.canvas_exp = FigureCanvasTkAgg(self.fig_expense, master=self.chart_holder)
        self.canvas_exp.get_tk_widget().grid(row=0, column=1, padx=15, pady=5)

        # Global account number display configuration toggle variable
        self.show_acct_nums_var = tk.BooleanVar(value=False)

        config_frame = tk.Frame(self.main_frame, bg='#111111')
        config_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=10)

        acct_chk = tk.Checkbutton(
            config_frame, text="Show Account Numbers on Charts & Tooltips",
            variable=self.show_acct_nums_var,
            bg='#111111', fg='#aaaaaa', selectcolor='#1e1e1e',
            activebackground='#111111', activeforeground='white',
            font=('Arial', 9, 'bold'), command=self.process_inputs
        )
        acct_chk.pack(anchor="w")

        # FEATURE IMPLEMENTATION: Define our tiered confidentiality profile tracker variable
        self.view_profile_var = tk.StringVar(value="Bookkeeper Mode (Full Details)")

        # Injects the drop-down selector container layer safely into your control deck
        tk.Label(config_frame, text="Confidentiality View Profile:", bg='#111111', fg='#aaaaaa',
                 font=('Arial', 9, 'bold')).pack(side="left", padx=(15, 5))

        from tkinter import ttk
        profile_combo = ttk.Combobox(
            config_frame, textvariable=self.view_profile_var,
            values=["Bookkeeper Mode (Full Details)", "Public Mode (Hide Salaries)", "Silence All Tooltips"],
            state="readonly", font=('Arial', 9), width=24
        )
        profile_combo.pack(side="left", padx=5)

        # Re-trigger calculation cycles to update tooltip restrictions instantly on toggle
        profile_combo.bind("<<ComboboxSelected>>", lambda e: self.process_inputs())

        # FEATURE IMPLEMENTATION: Connect interactive canvas listeners for clicks and hovers
        self.canvas_inc.mpl_connect("motion_notify_event", lambda e: self.handle_hover(e, "Income"))
        self.canvas_inc.mpl_connect("button_press_event", lambda e: self.handle_click(e, "Income"))
        self.canvas_exp.mpl_connect("motion_notify_event", lambda e: self.handle_hover(e, "Expense"))
        self.canvas_exp.mpl_connect("button_press_event", lambda e: self.handle_click(e, "Expense"))

    def clean_label_text(self, text):
        """FEATURE IMPLEMENTATION: Dynamically strips account codes and separators on the fly

        if the global display configuration checkbox toggle is unchecked.
        """
        if self.show_acct_nums_var.get():
            return text  # Return original label untouched

        import re
        # Pattern splits: Optional "Total ", 4 digits, optional decimal points/digits,
        # and captures any surrounding dash (-), dot (·), or space separators safely.
        cleaned = re.sub(r'^(Total\s+)?\d+(\.\d+)?\s*[\-·•]\s*', '', text)
        return cleaned.strip()

    def add_title_row(self, master, title_var, text_color):
        """Creates an editable title text box for budget headings."""
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

        # A single-item list wrapper used to pass local variables across nested namespaces safely
        old_label_holder = [label_text.strip()]

        display_name = self.clean_label_text(label_text)
        lbl_var = tk.StringVar(value=display_name)
        lbl_entry = tk.Entry(row, textvariable=lbl_var, bg='#2a2a2a', fg='white', insertbackground='white',
                             font=('Arial', 9), width=1)
        lbl_entry.pack(side="left", fill="x", expand=True, padx=2)

        lbl_entry.raw_data_key = label_text.strip()

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

        # =========================================================================
        # CONTEXT MENU OPERATIONS
        # =========================================================================
        if not is_total:
            context_menu = tk.Menu(self.root, tearoff=0, bg='#2a2a2a', fg='white',
                                   activebackground='#00F0FF', activeforeground='black', bd=1)

            def do_clear():
                lbl_var.set("")
                val_var.set("0")
                self.process_inputs(is_live=True)

            def do_restore():
                lbl_var.set(self.clean_label_text(label_text))
                val_var.set(val_str)
                self.process_inputs(is_live=True)

            def do_delete():
                if (lbl_var, val_var) in self.income_inputs:
                    self.income_inputs.remove((lbl_var, val_var))
                elif (lbl_var, val_var) in self.expense_inputs:
                    self.expense_inputs.remove((lbl_var, val_var))

                self.subcategories.pop(lbl_entry.raw_data_key, None)
                self.subcategories.pop(lbl_var.get().strip(), None)

                row.destroy()
                self.process_inputs()

            context_menu.add_command(label="Clear Entry Fields", command=do_clear)
            context_menu.add_command(label="Restore Default Values", command=do_restore)
            context_menu.add_separator()
            context_menu.add_command(label="Delete Category Row", command=do_delete)

            def show_popup(event):
                context_menu.post(event.x_root, event.y_root)

            for widget in [row, lbl_entry, val_entry]:
                widget.bind("<Button-3>", show_popup)
                widget.bind("<Button-2>", show_popup)

        # =========================================================================

        def sync_category_name_change(*args):
            if hasattr(self, 'is_updating_display') and self.is_updating_display:
                return
            new_name = lbl_var.get().strip()
            # FIXED: Target list index 0 explicitly to resolve scoping rules
            old_name = old_label_holder[0]

            if old_name and new_name and old_name != new_name:
                true_old_key = lbl_entry.raw_data_key.strip()
                true_new_key = new_name

                # Smart Prefix Preservation Engine
                # If account numbers are currently hidden, extract the prefix from our cached raw key handle
                # and automatically prepend it onto the user's new label string.
                import re
                prefix_match = re.match(r'^(\d+(\.\d+)?\s*[\-·•]\s*)', lbl_entry.raw_data_key)
                true_new_key = f"{prefix_match.group(1)}{new_name}" if (
                            prefix_match and not re.match(r'^\d+', new_name)) else new_name
                if lbl_entry.raw_data_key in self.subcategories:
                    self.subcategories[true_new_key] = self.subcategories.pop(lbl_entry.raw_data_key)
                # FIXED: Overwrite list index 0 element target safely
                old_label_holder[0] = new_name
                lbl_entry.raw_data_key = true_new_key
            self.process_inputs(is_live=True)

        lbl_var.trace_add("write", sync_category_name_change)
        val_var.trace_add("write", lambda *args: self.process_inputs(is_live=True))

        return lbl_var, val_var

    def handle_hover(self, event, chart_type):
        """Manages hovering mechanics, secures item details in public modes,

        and preserves parent category math balance readouts perfectly.
        """
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

        if not event.inaxes:
            return

        current_profile = self.view_profile_var.get()
        if current_profile == "Silence All Tooltips":
            return

        wedges = self.income_wedges if chart_type == "Income" else self.expense_wedges
        labels = self.income_labels if chart_type == "Income" else self.expense_labels
        sizes = self.income_sizes if chart_type == "Income" else self.expense_sizes

        for i, w in enumerate(wedges):
            if i >= len(labels): continue
            contained, _ = w.contains(event)
            if contained:
                hovered_label = labels[i]
                expected_total = sizes[i]

                sub_list = []
                display_cat_name = hovered_label
                raw_category_key = hovered_label

                for raw_key, items in self.subcategories.items():
                    if hovered_label == raw_key or hovered_label == self.clean_label_text(raw_key):
                        sub_list = items
                        display_cat_name = self.clean_label_text(raw_key)
                        raw_category_key = raw_key
                        break

                # Identify if this category contains sensitive compensation information
                is_sensitive = any(
                    token in raw_category_key.upper() for token in ["SALARY", "BENEFIT", "CLERGY", "LAY MIN"])

                # FLAG SEPARATION: Determine whether to show item lines vs showing the overall category math
                show_breakdown_rows = True
                if current_profile == "Public Mode (Hide Salaries)" and is_sensitive:
                    show_breakdown_rows = False

                # Always calculate the true totals from the dataset, completely independent of view locks
                total_entered = sum(v for _, v in sub_list)
                remainder = expected_total - total_entered

                max_lbl_len = 13
                cleaned_subs = []
                if sub_list:
                    for sub_lbl, sub_val in sub_list:
                        c_lbl = self.clean_label_text(sub_lbl)
                        cleaned_subs.append((c_lbl, sub_val))
                        if show_breakdown_rows:
                            max_lbl_len = max(max_lbl_len, len(c_lbl))

                col_width = max_lbl_len + 4
                body_text = ""

                # Only append the line item rows if our profile mode permits it
                if show_breakdown_rows and cleaned_subs:
                    for sub_lbl, sub_val in cleaned_subs:
                        val_str = f"${int(sub_val)}"
                        pad_len = col_width - len(sub_lbl)
                        pad_space = " " * max(1, pad_len)
                        body_text += f"{sub_lbl}{pad_space}{val_str}\n"

                # If item details are hidden, display the full Category Total instead of an "Other Balance" remainder
                rem_str = f"${int(remainder if show_breakdown_rows else expected_total)}"
                lbl_str = "Other Balance" if show_breakdown_rows else "Category Total"
                pad_len = col_width - len(lbl_str)
                pad_space = " " * max(1, pad_len)
                body_text += f"{lbl_str}{pad_space}{rem_str}"

                border_color = '#00F0FF' if chart_type == "Income" else '#FF007F'

                self.tooltip = tk.Toplevel(self.root)
                self.tooltip.wm_overrideredirect(True)
                self.tooltip.configure(bg='#e0e0e0', highlightbackground=border_color, highlightcolor=border_color,
                                       highlightthickness=2, bd=0)

                header_lbl = tk.Label(self.tooltip, text=f"--- {display_cat_name} Ledger ---", bg='#e0e0e0',
                                      fg='#1a1a1a', font=('Arial', 10, 'bold'), padx=10)
                header_lbl.pack(fill="x", pady=(8, 4))

                body_lbl = tk.Label(self.tooltip, text=body_text, bg='#e0e0e0', fg='#1a1a1a',
                                    font=('Consolas', 9, 'bold'), justify="left", padx=10)
                body_lbl.pack(fill="x", pady=(0, 8))

                self.tooltip.update_idletasks()
                tip_w = self.tooltip.winfo_reqwidth()
                tip_h = self.tooltip.winfo_reqheight()

                pointer_x = self.root.winfo_pointerx()
                pointer_y = self.root.winfo_pointery()
                screen_w = self.root.winfo_screenwidth()
                screen_h = self.root.winfo_screenheight()

                x_offset = 15
                y_offset = 15

                if pointer_x + x_offset + tip_w > screen_w: x_offset = -(tip_w + 15)
                if pointer_y + y_offset + tip_h > screen_h: y_offset = -(tip_h + 15)

                self.tooltip.wm_geometry(f"+{pointer_x + x_offset}+{pointer_y + y_offset}")
                break

    def handle_click(self, event, chart_type):
        """FEATURE IMPLEMENTATION: Intercepts mouse click events and registers true double click events."""
        if not event.inaxes or not event.dblclick:
            return

        wedges = self.income_wedges if chart_type == "Income" else self.expense_wedges
        labels = self.income_labels if chart_type == "Income" else self.expense_labels
        sizes = self.income_sizes if chart_type == "Income" else self.expense_sizes

        for i, w in enumerate(wedges):
            if i >= len(labels): continue
            contained, _ = w.contains(event)
            if contained:
                self.open_ledger_modal(labels[i], sizes[i])
                break

    def open_ledger_modal(self, category_name, expected_total):
        """Creates scrollable Treeview modal centered cleanly over chart area with predictive selection states."""
        modal = tk.Toplevel(self.root)
        modal.title(f"Subcategory Ledger: {category_name}")
        modal.configure(bg='#1e1e1e')
        modal.geometry("450x380")
        modal.transient(self.root)
        modal.grab_set()

        mx = self.root.winfo_x() + (self.root.winfo_width() // 2) - 225
        my = self.root.winfo_y() + (self.root.winfo_height() // 2) - 190
        modal.geometry(f"+{mx}+{my}")

        style = ttk.Style()
        # Forces the treeview selection engine to respect custom tag backgrounds
        style.map("Treeview", background=[("selected", "background")])

        style.theme_use("clam")
        style.configure("Treeview", background="#2a2a2a", fieldbackground="#2a2a2a", foreground="white",
                        font=('Arial', 9))
        style.configure("Treeview.Heading", background="#111111", foreground="white", font=('Arial', 9, 'bold'))

        tree_frame = tk.Frame(modal, bg='#1e1e1e')
        tree_frame.pack(fill="both", expand=True, padx=10, pady=10)

        tree = ttk.Treeview(tree_frame, columns=("Subcategory", "Value"), show="headings", height=8)
        tree.heading("Subcategory", text="Subcategory")
        tree.heading("Value", text="Value")
        tree.column("Subcategory", width=250, anchor="w")
        tree.column("Value", width=150, anchor="e")

        tree.tag_configure("gray_lbl", foreground="#777777")
        tree.tag_configure("red_lbl", foreground="#FF3300", background="#550011")

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        form_frame = tk.Frame(modal, bg='#1e1e1e')
        form_frame.pack(fill="x", padx=10, pady=5)

        sub_var = tk.StringVar()
        sub_ent = tk.Entry(form_frame, textvariable=sub_var, bg='#2a2a2a', fg='white', width=20)
        sub_ent.pack(side="left", padx=2)

        val_var = tk.StringVar()
        val_ent = tk.Entry(form_frame, textvariable=val_var, bg='#2a2a2a', fg='white', width=8, justify="right")
        val_ent.pack(side="left", padx=2)

        editing_index = None

        def refresh_tree_view():
            nonlocal editing_index
            editing_index = None
            for item in tree.get_children():
                tree.delete(item)

            sub_list = self.subcategories.get(category_name, [])
            total_entered = sum(v for _, v in sub_list)
            remainder = expected_total - total_entered

            # Cleans the labels right as they are being pushed onto the Treeview grid
            for idx, (sub_lbl, sub_val) in enumerate(sub_list):
                display_sub_lbl = self.clean_label_text(sub_lbl)
                tree.insert("", "end", iid=str(idx), values=(display_sub_lbl, int(sub_val)))

            if remainder >= 0:
                tree.insert("", "end", iid="other", values=("Other Balance", int(remainder)), tags=("gray_lbl",))
            else:
                tree.insert("", "end", iid="other", values=("Other Balance", int(remainder)), tags=("red_lbl",))

            # Automatically highlights the "Other Balance" row to safely reset the interface state
            tree.selection_set("other")

            sub_var.set("")
            val_var.set("")
            add_btn.config(state="normal", text="+ Add Item")
            remove_btn.config(state="disabled")

        def add_or_update_ledger_item():
            nonlocal editing_index
            lbl = sub_var.get().strip()
            try:
                val = float(val_var.get() or 0.0)
                if not lbl or lbl == "Other Balance": return

                if category_name not in self.subcategories:
                    self.subcategories[category_name] = []
                sub_list = self.subcategories[category_name]

                if editing_index is not None and editing_index < len(sub_list):
                    sub_list[editing_index] = [lbl, val]
                else:
                    sub_list.append([lbl, val])

                refresh_tree_view()
            except ValueError:
                messagebox.showerror("Error", "Please input a valid numeric digit.")

        def remove_ledger_item():
            selected_items = tree.selection()
            if not selected_items: return

            sub_list = self.subcategories.get(category_name, [])
            indices_to_delete = []
            for item_id in selected_items:
                if item_id == "other": continue
                indices_to_delete.append(int(item_id))

            indices_to_delete.sort(reverse=True)
            for idx in indices_to_delete:
                if idx < len(sub_list):
                    sub_list.pop(idx)
            refresh_tree_view()

        def handle_selection_change(event):
            nonlocal editing_index
            selected = tree.selection()

            if len(selected) != 1:
                editing_index = None
                sub_var.set("")
                val_var.set("")
                add_btn.config(state="disabled", text="+ Add Item")
                remove_btn.config(state="normal" if len(selected) > 0 else "disabled")
                return

            item_id = selected[0]

            if item_id == "other":
                editing_index = None
                sub_var.set("")
                val_var.set("")
                add_btn.config(state="normal", text="+ Add Item")
                remove_btn.config(state="disabled")
                return

            editing_index = int(item_id)
            item_vals = tree.item(item_id, "values")
            if item_vals:
                sub_var.set(item_vals[0])
                val_var.set(item_vals[1])
                add_btn.config(state="normal", text="Save Edit")
                remove_btn.config(state="normal")

        tree.bind("<<TreeviewSelect>>", handle_selection_change)

        add_btn = tk.Button(form_frame, text="+ Add Item", command=add_or_update_ledger_item,
                            bg='#00F0FF', fg='black', font=('Arial', 9, 'bold'))
        add_btn.pack(side="left", padx=5)

        remove_btn = tk.Button(form_frame, text="- Remove Item", command=remove_ledger_item,
                               bg='#FF3300', fg='white', font=('Arial', 9, 'bold'), state="disabled")
        remove_btn.pack(side="left", padx=5)

        refresh_tree_view()

    def load_initial_data(self):
        """Loads budget dataset configurations from the Desktop CSV or defaults to

        hardcoded allocations, assigning explicit class title trackers for the layout engine.
        """
        desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
        csv_filename = os.path.join(desktop_dir, "budget_data.csv")

        self.inc_frame = tk.Frame(self.scroll_frame, bg='#1e1e1e')
        self.inc_frame.pack(fill="x", expand=True)

        self.exp_frame = tk.Frame(self.scroll_frame, bg='#1e1e1e')
        self.exp_frame.pack(fill="x", expand=True)

        # 1. Initialize Income headers and save explicit title frame row reference
        tk.Label(self.inc_frame, text="INCOME CONFIG", fg='#00F0FF', bg='#1e1e1e',
                 font=('Arial', 9, 'bold')).pack(anchor="w", pady=(10, 4), padx=5)
        self.add_title_row(self.inc_frame, self.income_title_var, '#00F0FF')
        self.inc_title_row = self.inc_frame.pack_slaves()[-1]
        expense_header_printed = False

        # Persistent gray readouts initialization
        self.inc_other_lbl = tk.Label(self.inc_frame, fg='#777777', bg='#1e1e1e', font=('Arial', 9, 'italic'))
        self.exp_other_lbl = tk.Label(self.exp_frame, fg='#777777', bg='#1e1e1e', font=('Arial', 9, 'italic'))

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

                    if dtype == "Subcategory":
                        if "::" in category:
                            main_cat, sub_lbl = category.split("::", 1)
                            if main_cat not in self.subcategories:
                                self.subcategories[main_cat] = []
                            self.subcategories[main_cat].append([sub_lbl, amount])

                    elif dtype == "Income":
                        if category == "Income Title":
                            self.income_title_var.set(row.get('Title text', 'Budget Income Breakdown'))
                        elif "Total" in category:
                            _, self.inc_total_val = self.add_input_row(self.inc_frame, category, amount, is_total=True)
                        else:
                            self.income_inputs.append(self.add_input_row(self.inc_frame, category, amount))

                    elif dtype == "Expense":
                        if not expense_header_printed:
                            # 2. Initialize Expense headers and save explicit title frame row reference
                            tk.Label(self.exp_frame, text="EXPENSE CONFIG", fg='#FF007F', bg='#1e1e1e',
                                     font=('Arial', 9, 'bold')).pack(anchor="w", pady=(20, 4), padx=5)
                            self.add_title_row(self.exp_frame, self.expense_title_var, '#FF007F')
                            self.exp_title_row = self.exp_frame.pack_slaves()[-1]
                            expense_header_printed = True

                        if category == "Expense Title":
                            self.expense_title_var.set(row.get('Title text', 'Budget Expenses Breakdown'))
                        elif "Total" in category:
                            _, self.exp_total_val = self.add_input_row(self.exp_frame, category, amount, is_total=True)
                        else:
                            self.expense_inputs.append(self.add_input_row(self.exp_frame, category, amount))

            tk.Button(self.inc_frame, text="+ Add Income Item", command=lambda: self.add_blank_row("Income"),
                      bg='#111111', fg='#00F0FF', font=('Arial', 8, 'bold'), bd=0, cursor="hand2").pack(anchor="w", padx=7, pady=5)

            tk.Button(self.exp_frame, text="+ Add Expense Item", command=lambda: self.add_blank_row("Expense"),
                      bg='#111111', fg='#FF007F', font=('Arial', 8, 'bold'), bd=0, cursor="hand2").pack(anchor="w", padx=7, pady=5)

            self.income_title_var.trace_add("write", lambda *args: self.process_inputs(is_live=True))
            self.expense_title_var.trace_add("write", lambda *args: self.process_inputs(is_live=True))

            self.process_inputs()
        except Exception as e:
            messagebox.showerror("CSV Load Error", f"Could not parse CSV:\n{str(e)}")
            self.load_hardcoded_defaults()

    def load_hardcoded_defaults(self):
        """FALLBACK IMPLEMENTATION: Loads baseline data if the desktop spreadsheet is missing,

        safely registering anchor title rows for the layout sorting manager.
        """
        _, self.inc_total_val = self.add_input_row(self.inc_frame, "Total Income", 429000, is_total=True)
        self.income_inputs.append(self.add_input_row(self.inc_frame, "Giving", 383000))
        self.income_inputs.append(self.add_input_row(self.inc_frame, "Partners", 42000))

        tk.Button(self.inc_frame, text="+ Add Income Item", command=lambda: self.add_blank_row("Income"),
                  bg='#111111', fg='#00F0FF', font=('Arial', 8, 'bold'), bd=0, cursor="hand2").pack(anchor="w", padx=7,
                                                                                                    pady=5)

        tk.Label(self.exp_frame, text="EXPENSE CONFIG", fg='#FF007F', bg='#1e1e1e', font=('Arial', 9, 'bold')).pack(
            anchor="w", pady=(20, 4), padx=5)

        # FIXED: Explicitly register title references inside the fallback tracker
        self.add_title_row(self.exp_frame, self.expense_title_var, '#FF007F')
        self.exp_title_row = self.exp_frame.pack_slaves()[-1]

        # Ensure income title row tracker is assigned an anchor as well if missing
        if not hasattr(self, 'inc_title_row'):
            self.inc_title_row = self.inc_frame.pack_slaves()[1]

        _, self.exp_total_val = self.add_input_row(self.exp_frame, "Total Expense", 453400, is_total=True)
        self.expense_inputs.append(self.add_input_row(self.exp_frame, "Clergy", 211400))
        self.expense_inputs.append(self.add_input_row(self.exp_frame, "Lay Ministry", 109400))
        self.expense_inputs.append(self.add_input_row(self.exp_frame, "Building", 64900))
        self.expense_inputs.append(self.add_input_row(self.exp_frame, "Admin", 20000))
        self.expense_inputs.append(self.add_input_row(self.exp_frame, "Worship", 7700))
        self.expense_inputs.append(self.add_input_row(self.exp_frame, "Faith Form.", 5000))

        tk.Button(self.exp_frame, text="+ Add Expense Item", command=lambda: self.add_blank_row("Expense"),
                  bg='#111111', fg='#FF007F', font=('Arial', 8, 'bold'), bd=0, cursor="hand2").pack(anchor="w", padx=7,
                                                                                                    pady=5)

        self.income_title_var.trace_add("write", lambda *args: self.process_inputs(is_live=True))
        self.expense_title_var.trace_add("write", lambda *args: self.process_inputs(is_live=True))
        self.process_inputs()

    def process_inputs(self, is_live=False):
        if hasattr(self, 'is_updating') and self.is_updating:
            return
        try:
            self.is_updating = True

            # FIXED: Added a rigid structural guard to ensure plain text fields are never locked out
            self.is_updating_display = True
            for frame in [self.inc_frame, self.exp_frame]:
                for row_frame in frame.winfo_children():
                    if isinstance(row_frame, tk.Frame):
                        for child in row_frame.winfo_children():
                            if isinstance(child, tk.Entry) and hasattr(child, 'raw_data_key'):
                                # Regular expression checks if the raw cache key actually contains an account prefix code
                                import re
                                has_acct_prefix = bool(re.match(r'^\d', child.raw_data_key.strip()))

                                # ONLY format or rewrite the text box if it's an official spreadsheet account code
                                if has_acct_prefix:
                                    current_text = child.get().strip()
                                    target_clean_text = self.clean_label_text(child.raw_data_key)
                                    if current_text != target_clean_text:
                                        child.delete(0, "end")
                                        child.insert(0, target_clean_text)
            self.is_updating_display = False

            self.total_income = float(self.inc_total_val.get() or 0.0)
            inc_candidates = []
            other_inc_accumulator = 0.0

            for l, v in self.income_inputs:
                lbl = l.get().strip()
                val = float(v.get() or 0.0)
                if lbl or val > 0:
                    if val < 100.0:
                        other_inc_accumulator += val
                    else:
                        inc_candidates.append((lbl if lbl else "New Income", val))

            inc_candidates.sort(key=lambda x: x[1], reverse=True)
            # FIXED: Extract tuple numeric values index x[1] for proper mathematical summation
            other_inc = (self.total_income - sum(x[1] for x in inc_candidates)) + other_inc_accumulator

            self.income_labels = [self.clean_label_text(x[0]) for x in inc_candidates]
            self.income_sizes = [x[1] for x in inc_candidates]

            if other_inc < 0:
                self.inc_other_lbl.config(text=f"Other Balance: {int(other_inc)}", fg='#FF3300')
            else:
                self.inc_other_lbl.config(text=f"Other Balance: {int(other_inc)}", fg='#777777')

            if other_inc != 0 or len(inc_candidates) > 0:
                if other_inc >= 1.0:
                    self.income_labels.append("Other Income")
                    self.income_sizes.append(other_inc)
                self.inc_other_lbl.pack(anchor="w", padx=7, pady=2, before=self.inc_frame.pack_slaves()[-1])

            self.total_expenses = float(self.exp_total_val.get() or 0.0)
            exp_candidates = []
            other_exp_accumulator = 0.0

            for l, v in self.expense_inputs:
                lbl = l.get().strip()
                val = float(v.get() or 0.0)
                if lbl or val > 0:
                    if val < 100.0:
                        other_exp_accumulator += val
                    else:
                        exp_candidates.append((lbl if lbl else "New Expense", val))

            exp_candidates.sort(key=lambda x: x[1], reverse=True)
            # FIXED: Extract tuple numeric values index x[1] for proper mathematical summation
            other_exp = (self.total_expenses - sum(x[1] for x in exp_candidates)) + other_exp_accumulator

            self.expense_labels = [self.clean_label_text(x[0]) for x in exp_candidates]
            self.expense_sizes = [x[1] for x in exp_candidates]

            if other_exp < 0:
                self.exp_other_lbl.config(text=f"Other Balance: {int(other_exp)}", fg='#FF3300')
            else:
                self.exp_other_lbl.config(text=f"Other Balance: {int(other_exp)}", fg='#777777')

            if other_exp != 0 or len(exp_candidates) > 0:
                if other_exp >= 1.0:
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

    def add_blank_row(self, section_type):
        if section_type == "Income":
            new_row = self.add_input_row(self.inc_frame, "", 0)
            self.income_inputs.append(new_row)
        else:
            new_row = self.add_input_row(self.exp_frame, "", 0)
            self.expense_inputs.append(new_row)

    def on_resize(self, event=None, forced=False):
        if event and event.widget != self.root and event.widget != self.main_frame:
            return

        w_width, w_height = self.root.winfo_width(), self.root.winfo_height()
        if w_width < 10 or w_height < 10:
            return

        self.current_width = w_width
        self.current_height = w_height

        right_panel_w = self.main_frame.winfo_width()
        if right_panel_w < 50:
            right_panel_w = (w_width * 5 // 6)

        available_w = (right_panel_w - 85) // 2
        available_h = w_height - 85
        size_pixels = max(150, min(available_w, available_h))
        size_inches = size_pixels / 100.0

        font_sz = min(9.5, max(7.2, 7.2 + (size_inches * 0.40)))
        thresh = min(0.24, max(0.15, 0.26 - (size_inches * 0.022)))

        self.income_wedges = create_smart_pie(self.fig_income, self.income_sizes, self.income_labels, self.total_income,
                                              self.income_title_var.get(), '#00F0FF', font_sz, thresh)
        self.expense_wedges = create_smart_pie(self.fig_expense, self.expense_sizes, self.expense_labels,
                                               self.total_expenses,
                                               self.expense_title_var.get(), '#FF007F', font_sz, thresh)

        self.fig_income.set_size_inches(size_inches, size_inches)
        self.fig_expense.set_size_inches(size_inches, size_inches)

        if self.canvas_inc and self.canvas_exp:
            self.canvas_inc.get_tk_widget().configure(width=size_pixels, height=size_pixels)
            self.canvas_exp.get_tk_widget().configure(width=size_pixels, height=size_pixels)
            self.canvas_inc.draw()
            self.canvas_exp.draw()

    def save_charts(self):
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
            messagebox.showinfo("Success",
                                f"Saved successfully to your Desktop:\nincome_budget.png\nexpenses_budget.png")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save charts:\n{str(e)}")

    def save_to_csv(self):
        """FEATURE IMPLEMENTATION: Secure saving routine that guarantees data alignment

        by reading string variables directly from the master model input tracking arrays.
        """
        import csv
        import os
        desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
        csv_filename = os.path.join(desktop_dir, "budget_data.csv")

        try:
            with open(csv_filename, mode='w', newline='', encoding='utf-8-sig') as f:
                fieldnames = ['Type', 'Category', 'Amount', 'Title text']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()

                # 1. Save global dashboard configurations and chart title states
                writer.writerow({'Type': 'Income', 'Category': 'Income Title', 'Amount': '', 'Title text': self.income_title_var.get()})
                writer.writerow({'Type': 'Expense', 'Category': 'Expense Title', 'Amount': '', 'Title text': self.expense_title_var.get()})

                # 2. Save locked overall summary totals configurations securely
                writer.writerow({'Type': 'Income', 'Category': 'Total Income Limit', 'Amount': float(self.inc_total_val.get() or 0.0), 'Title text': ''})
                writer.writerow({'Type': 'Expense', 'Category': 'Total Expenses Target', 'Amount': float(self.exp_total_val.get() or 0.0), 'Title text': ''})

                # Create a smart dictionary translation map to re-attach full raw keys if text is hidden
                raw_key_map = {}
                for frame in [self.inc_frame, self.exp_frame]:
                    for row_frame in frame.winfo_children():
                        if isinstance(row_frame, tk.Frame):
                            for child in row_frame.winfo_children():
                                if isinstance(child, tk.Entry) and hasattr(child, 'raw_data_key'):
                                    # Cross-reference display variations back to their true full account text codes
                                    raw_key_map[child.get().strip()] = child.raw_data_key.strip()
                                    raw_key_map[self.clean_label_text(child.raw_data_key)] = child.raw_data_key.strip()
                                    raw_key_map[child.raw_data_key.strip()] = child.raw_data_key.strip()

                # 3. Streamlined Ingestion: Read values directly from model input structures
                for lbl_var, val_var in self.income_inputs:
                    current_lbl = lbl_var.get().strip()
                    true_raw_key = raw_key_map.get(current_lbl, current_lbl)
                    try:
                        val_num = float(val_var.get() or 0.0)
                    except ValueError:
                        val_num = 0.0
                    writer.writerow({'Type': 'Income', 'Category': true_raw_key, 'Amount': val_num, 'Title text': ''})

                for lbl_var, val_var in self.expense_inputs:
                    current_lbl = lbl_var.get().strip()
                    true_raw_key = raw_key_map.get(current_lbl, current_lbl)
                    try:
                        val_num = float(val_var.get() or 0.0)
                    except ValueError:
                        val_num = 0.0
                    writer.writerow({'Type': 'Expense', 'Category': true_raw_key, 'Amount': val_num, 'Title text': ''})

                # 4. Export deep-dive subcategories relational ledgers accurately
                for parent_cat, sub_items in self.subcategories.items():
                    true_parent_key = raw_key_map.get(parent_cat, parent_cat)
                    for sub_lbl, sub_val in sub_items:
                        compound_key = f"{true_parent_key}::{sub_lbl}"
                        writer.writerow({'Type': 'Subcategory', 'Category': compound_key, 'Amount': float(sub_val), 'Title text': ''})

            messagebox.showinfo("Success", "Budget dataset modifications archived safely to Desktop!")
        except Exception as e:
            messagebox.showerror("Save Error", f"Could not compile local file storage paths:\n{str(e)}")


if __name__ == "__main__":
    root = tk.Tk()
    app = InteractiveDashboard(root)
    root.update()
    app.on_resize()
    root.mainloop()
