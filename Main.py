import os
import sys
import tkinter as tk
from tkinter import messagebox, ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from Chart_Engine import *  # Imports cleanly from your support module
from budget_importer import import_excel_budget
import csv

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

        # Seed your active session save handle to point to the executable's current working directory by default
        self.last_import_dir = os.getcwd()

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
        """Creates a dynamic scrollable left panel that hugs its content height on tall screens,
        keeping the Net Position summary immediately beneath the Income/Expense lists.
        """
        # Hook directly back into your stable horizontal sliding sash paned container
        self.left_panel = tk.Frame(self.paned_window, bg='#111111')
        self.paned_window.add(self.left_panel)

        # ZONE 1: THE DYNAMIC SCROLLABLE VIEWPORT CANVAS DECK (TOP AREA)
        # This frame shrinks to wrap its content tightly
        scroll_outer_frame = tk.Frame(self.left_panel, bg='#111111')
        scroll_outer_frame.pack(side="top", fill="x", expand=False, padx=5, pady=(10, 5))

        # Explicitly set width=180 to guarantee it fits inside your 220px default startup sash
        self.scroll_canvas = tk.Canvas(scroll_outer_frame, bg='#111111', bd=0, highlightthickness=0, width=180)
        self.scroll_canvas.pack(side="left", fill="both", expand=True)

        # CUSTOM DARK STYLE: Use a ttk Scrollbar to mute the bright background color
        from tkinter import ttk
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Dark.Vertical.TScrollbar",
                        background="#2a2a2a",      # Thumb handle gray color
                        troughcolor="#111111",     # Track gutter dark background color
                        arrowcolor="#777777",      # Arrow head indicator color
                        bordercolor="#111111",     # Frame borders
                        lightcolor="#2a2a2a",
                        darkcolor="#2a2a2a")

        v_scrollbar = ttk.Scrollbar(scroll_outer_frame, orient="vertical", command=self.scroll_canvas.yview,
                                    style="Dark.Vertical.TScrollbar")
        self.scroll_canvas.configure(yscrollcommand=v_scrollbar.set)

        self.scrollable_inner_frame = tk.Frame(self.scroll_canvas, bg='#111111')
        self.canvas_window_id = self.scroll_canvas.create_window((0, 0), window=self.scrollable_inner_frame,
                                                                 anchor="nw")

        # Dynamic height & scrollbar visibility manager
        def sync_left_panel_layout(event=None):
            self.scroll_canvas.configure(scrollregion=self.scroll_canvas.bbox("all"))

            panel_h = self.left_panel.winfo_height()
            if panel_h < 50:
                return  # Wait until window finishes initial draw

            content_h = self.scrollable_inner_frame.winfo_reqheight()

            # Reserve vertical room for Net Summary (~55px) + 4 Action Buttons (~195px) + Padding (~30px)
            reserved_bottom_h = 280
            max_canvas_h = max(100, panel_h - reserved_bottom_h)

            if content_h <= max_canvas_h:
                # Tall screen: Hug the exact content height and hide the scrollbar
                self.scroll_canvas.configure(height=content_h)
                v_scrollbar.pack_forget()
                self.scroll_canvas.yview_moveto(0)
            else:
                # Short screen or many rows: Cap canvas height and show the scrollbar
                self.scroll_canvas.configure(height=max_canvas_h)
                if not v_scrollbar.winfo_ismapped():
                    v_scrollbar.pack(side="right", fill="y")

        self.scrollable_inner_frame.bind("<Configure>", sync_left_panel_layout)
        self.left_panel.bind("<Configure>", sync_left_panel_layout)

        def configure_canvas_width(event):
            # Dynamic updates adjust width cleanly when you manually drag the pane slider
            self.scroll_canvas.itemconfig(self.canvas_window_id, width=event.width)
        self.scroll_canvas.bind("<Configure>", configure_canvas_width)

        def handle_mouse_wheel(event):
            # Only scroll if the content is taller than the visible canvas viewport
            if self.scrollable_inner_frame.winfo_reqheight() > self.scroll_canvas.winfo_height():
                if event.num == 5 or event.delta < 0:
                    self.scroll_canvas.yview_scroll(1, "units")
                elif event.num == 4 or event.delta > 0:
                    self.scroll_canvas.yview_scroll(-1, "units")

        self.scroll_canvas.bind_all("<MouseWheel>", handle_mouse_wheel)
        self.scroll_canvas.bind_all("<Button-4>", handle_mouse_wheel)
        self.scroll_canvas.bind_all("<Button-5>", handle_mouse_wheel)

        # Main dynamic inner rows containers
        self.inc_frame = tk.Frame(self.scrollable_inner_frame, bg='#111111')
        self.inc_frame.pack(fill="x", expand=True, padx=(0, 15))

        self.exp_frame = tk.Frame(self.scrollable_inner_frame, bg='#111111')
        self.exp_frame.pack(fill="x", expand=True, padx=(0, 15))

        tk.Label(self.inc_frame, text="INCOME CONFIG", fg='#00F0FF', bg='#111111', font=('Arial', 9, 'bold')).pack(
            anchor="w", pady=(10, 4), padx=5)
        self.add_title_row(self.inc_frame, self.income_title_var, '#00F0FF')
        self.inc_title_row = self.inc_frame.pack_slaves()[-1]

        tk.Label(self.exp_frame, text="EXPENSE CONFIG", fg='#FF007F', bg='#111111', font=('Arial', 9, 'bold')).pack(
            anchor="w", pady=(20, 4), padx=5)
        self.add_title_row(self.exp_frame, self.expense_title_var, '#FF007F')
        self.exp_title_row = self.exp_frame.pack_slaves()[-1]

        self.inc_other_lbl = tk.Label(self.inc_frame, fg='#777777', bg='#111111', font=('Arial', 9, 'italic'))
        self.exp_other_lbl = tk.Label(self.exp_frame, fg='#777777', bg='#111111', font=('Arial', 9, 'italic'))

        # ZONE 2: THE NET POSITION SUMMARY BAR (HUGS CONTENT IMMEDIATELY BELOW)
        summary_outer_frame = tk.Frame(self.left_panel, bg='#111111')
        summary_outer_frame.pack(side="top", fill="x", padx=15, pady=(5, 5))

        top_sep = tk.Frame(summary_outer_frame, height=1, bg='#333333')
        top_sep.pack(fill="x", side="top", pady=(0, 4))

        self.net_summary_lbl = tk.Label(
            summary_outer_frame, text="Net Position: $0",
            fg='#ffffff', bg='#111111', font=('Arial', 10, 'bold'), anchor="w"
        )
        self.net_summary_lbl.pack(side="left", fill="x", expand=True, padx=5, pady=2)

        bot_sep = tk.Frame(summary_outer_frame, height=1, bg='#333333')
        bot_sep.pack(fill="x", side="bottom", pady=(4, 0))

        # ---------------------------------------------------------------------
        # ZONE 3: THE ORIGINAL 4 VERTICALLY STACKED SOLID NEON ACTION BUTTONS
        # ---------------------------------------------------------------------
        actions_frame = tk.Frame(self.left_panel, bg='#111111')
        actions_frame.pack(side="bottom", fill="x", padx=15, pady=(5, 15))

        btn_import = tk.Button(actions_frame, text="Import Spreadsheet Budget",
                               command=lambda: import_excel_budget(self),
                               bg='#FF00FF', fg='black', activebackground='#ff66ff', activeforeground='black',
                               font=('Arial', 9, 'bold'), bd=0, highlightthickness=0, height=2, cursor="hand2")
        btn_import.pack(fill="x", pady=4)

        btn_update = tk.Button(actions_frame, text="Update Charts", command=self.process_inputs,
                               bg='#00F0FF', fg='black', activebackground='#66f5ff', activeforeground='black',
                               font=('Arial', 9, 'bold'), bd=0, highlightthickness=0, height=2, cursor="hand2")
        btn_update.pack(fill="x", pady=4)

        self.btn_save = tk.Button(actions_frame, text="Create CSV File", command=self.save_to_csv,
                                  bg='#FFaa00', fg='black', activebackground='#ffcc66', activeforeground='black',
                                  font=('Arial', 9, 'bold'), bd=0, highlightthickness=0, height=2, cursor="hand2")
        self.btn_save.pack(fill="x", pady=4)

        btn_export_charts = tk.Button(actions_frame, text="Save Charts to Desktop", command=self.save_charts,
                                      bg='#00FF66', fg='black', activebackground='#66ff99', activeforeground='black',
                                      font=('Arial', 9, 'bold'), bd=0, highlightthickness=0, height=2, cursor="hand2")
        btn_export_charts.pack(fill="x", pady=4)

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

        # Single horizontal control bar at the bottom to preserve 100% of vertical chart height
        config_frame = tk.Frame(self.main_frame, bg='#111111')
        config_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=10)

        # 1. Left Control: Account Numbers Checkbox
        acct_chk = tk.Checkbutton(
            config_frame, text="Show Account Numbers",
            variable=self.show_acct_nums_var,
            bg='#111111', fg='#aaaaaa', selectcolor='#1e1e1e',
            activebackground='#111111', activeforeground='white',
            font=('Arial', 9, 'bold'), command=self.process_inputs
        )
        acct_chk.pack(side="left", padx=(0, 15))

        # 2. Middle Control: Confidentiality Profile Dropdown
        self.view_profile_var = tk.StringVar(value="Bookkeeper Mode (Full Details)")
        tk.Label(config_frame, text="View Profile:", bg='#111111', fg='#aaaaaa',
                 font=('Arial', 9, 'bold')).pack(side="left", padx=(5, 5))

        from tkinter import ttk
        profile_combo = ttk.Combobox(
            config_frame, textvariable=self.view_profile_var,
            values=["Bookkeeper Mode (Full Details)", "Public Mode (Hide Salaries)", "Silence All Tooltips"],
            state="readonly", font=('Arial', 9), width=23
        )
        profile_combo.pack(side="left", padx=(0, 15))
        profile_combo.bind("<<ComboboxSelected>>", lambda e: self.process_inputs())

        # 3. Right Control: Chart Visibility Radio Buttons (Both / Income / Expense)
        self.chart_view_mode_var = tk.StringVar(value="Both")
        radio_frame = tk.Frame(config_frame, bg='#111111')
        radio_frame.pack(side="right")

        tk.Label(radio_frame, text="Charts:", bg='#111111', fg='#aaaaaa',
                 font=('Arial', 9, 'bold')).pack(side="left", padx=(0, 5))

        for label_txt, mode_val, active_fg in [
            ("Both", "Both", "white"),
            ("Income", "Income", "#00F0FF"),
            ("Expense", "Expense", "#FF007F")
        ]:
            rb = tk.Radiobutton(
                radio_frame, text=label_txt, variable=self.chart_view_mode_var, value=mode_val,
                bg='#111111', fg=active_fg, selectcolor='#1e1e1e',
                activebackground='#111111', activeforeground=active_fg,
                font=('Arial', 9, 'bold'), cursor="hand2",
                command=lambda: self.on_resize(forced=True)
            )
            rb.pack(side="left", padx=4)

        # Connect interactive canvas listeners for hovers
        self.canvas_inc.mpl_connect("motion_notify_event", lambda e: self.handle_hover(e, "Income"))
        self.canvas_exp.mpl_connect("motion_notify_event", lambda e: self.handle_hover(e, "Expense"))

        # Unified Click Multiplexer
        def unified_click_handler(mpl_event, chart_type):
            if not mpl_event.inaxes:
                return
            if self.view_profile_var.get() == "Silence All Tooltips":
                return

            if mpl_event.button == 3 and not (hasattr(self, 'modal_active') and self.modal_active):
                wedges = self.income_wedges if chart_type == "Income" else self.expense_wedges
                labels = self.income_labels if chart_type == "Income" else self.expense_labels
                for idx, wedge in enumerate(wedges):
                    contained, _ = wedge.contains(mpl_event)
                    if contained and idx < len(labels):
                        self.zoom_modal_dispatcher(chart_type, idx, mpl_event)
                        return
            elif mpl_event.button == 1:
                self.handle_click(mpl_event, chart_type)

        self.canvas_inc.mpl_connect("button_press_event", lambda e: unified_click_handler(e, "Income"))
        self.canvas_exp.mpl_connect("button_press_event", lambda e: unified_click_handler(e, "Expense"))

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

        # CONTEXT MENU OPERATIONS
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

        def sync_category_name_change(*args):
            if hasattr(self, 'is_updating_display') and self.is_updating_display:
                return
            new_name = lbl_var.get().strip()
            # Target list index 0 explicitly to resolve scoping rules
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
                # Overwrite list index 0 element target safely
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
        # STRUCTURAL GUARD: Stand down instantly if a sanctuary zoom window is active
        if hasattr(self, 'modal_active') and self.modal_active:
            return

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
                        body_text += f"{sub_lbl}{' ' * max(1, pad_len)}{val_str}\n"

                # If item details are hidden, display the full Category Total instead of an "Other Balance" remainder
                rem_str = f"${int(remainder if show_breakdown_rows else expected_total)}"
                lbl_str = "Other Balance" if show_breakdown_rows else "Category Total"
                pad_len = col_width - len(lbl_str)
                body_text += f"{lbl_str}{' ' * max(1, pad_len)}{rem_str}"

                # PROFILE-AWARE DYNAMIC USER INVITATION TEXT GENERATOR
                if current_profile == "Public Mode (Hide Salaries)" and is_sensitive:
                    # Editing is locked for sensitive rows in public mode, only offer zoom
                    action_prompt = "[Right-Click to Zoom Entry Ledger]"
                else:
                    # Offer full editing and zoom mechanics for standard workflows
                    action_prompt = "[Left Double-Click to Edit | Right-Click to Zoom]"

                tooltip_text = body_text + "\n\n" + action_prompt
                border_color = '#00F0FF' if chart_type == "Income" else '#FF007F'

                self.tooltip = tk.Toplevel(self.root)
                self.tooltip.wm_overrideredirect(True)
                self.tooltip.configure(bg='#e0e0e0', highlightbackground=border_color, highlightcolor=border_color,
                                       highlightthickness=2, bd=0)

                header_lbl = tk.Label(self.tooltip, text=f"--- {display_cat_name} Ledger ---", bg='#e0e0e0',
                                      fg='#1a1a1a', font=('Arial', 10, 'bold'), padx=10)
                header_lbl.pack(fill="x", pady=(8, 4))

                body_lbl = tk.Label(self.tooltip, text=tooltip_text, bg='#e0e0e0', fg='#1a1a1a',
                                    font=('Consolas', 9, 'bold'), justify="left", padx=10)
                body_lbl.pack(fill="x", pady=(0, 8))

                # Safe fallbacks for right-clicking the floating card components directly
                def force_popup_trigger(e):
                    self.trigger_sanctuary_zoom(display_cat_name, border_color, max_lbl_len, show_breakdown_rows,
                                                cleaned_subs, remainder, expected_total)

                for component in [header_lbl, body_lbl]:
                    component.bind("<Button-3>", force_popup_trigger)
                    component.bind("<Button-2>", force_popup_trigger)

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

        # PUBLIC MODE INTERACTIVE CONFIDENTIALITY GUARD
        current_profile = self.view_profile_var.get()
        if current_profile == "Public Mode (Hide Salaries)":
            wedges = self.income_wedges if chart_type == "Income" else self.expense_wedges
            labels = self.income_labels if chart_type == "Income" else self.expense_labels

            for i, w in enumerate(wedges):
                if i >= len(labels): continue
                contained, _ = w.contains(event)
                if contained:
                    clicked_label = labels[i]

                    # Intercept click if category key contains sensitive compensation tokens
                    is_sensitive = any(
                        token in clicked_label.upper() for token in ["SALARY", "BENEFIT", "CLERGY", "LAY MIN"])
                    if is_sensitive:
                        # Silently return and block the editor modal window from ever opening
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
        """Creates scrollable Treeview modal centered cleanly over chart area with predictive selection states.
           Automatically resolves missing account number prefixes to prevent data layout collapse.
        """

        # DICTIONARY KEY ACCOUNT NUMBER ALIGNMENT ENGINE
        # Scan your data dictionary keys to find the true raw storage key match
        for raw_key in self.subcategories.keys():
            if category_name == raw_key or category_name == self.clean_label_text(raw_key):
                category_name = raw_key  # Overwrite with true raw key (e.g., "4101 · Giving")
                break

        modal = tk.Toplevel(self.root)
        modal.title(f"Subcategory Ledger: {self.clean_label_text(category_name)}")
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

    def zoom_modal_dispatcher(self, chart_type, index, mpl_event):
        """Processes right-click vector metadata slices, extracting details cleanly
        without collisions before launching the projection frame layout.
        """
        labels = self.income_labels if chart_type == "Income" else self.expense_labels
        sizes = self.income_sizes if chart_type == "Income" else self.expense_sizes
        hovered_label = labels[index]
        expected_total = sizes[index]

        sub_list = []
        display_cat_name = hovered_label
        raw_category_key = hovered_label
        for raw_key, items in self.subcategories.items():
            if hovered_label == raw_key or hovered_label == self.clean_label_text(raw_key):
                sub_list = items
                display_cat_name = self.clean_label_text(raw_key)
                raw_category_key = raw_key
                break

        is_sensitive = any(token in raw_category_key.upper() for token in ["SALARY", "BENEFIT", "CLERGY", "LAY MIN"])
        show_breakdown_rows = not (self.view_profile_var.get() == "Public Mode (Hide Salaries)" and is_sensitive)
        total_entered = sum(v for _, v in sub_list)
        remainder = expected_total - total_entered

        max_lbl_len = 13
        cleaned_subs = []
        if sub_list:
            for sub_lbl, sub_val in sub_list:
                c_lbl = self.clean_label_text(sub_lbl)
                cleaned_subs.append((c_lbl, sub_val))
                if show_breakdown_rows: max_lbl_len = max(max_lbl_len, len(c_lbl))

        border_color = '#00F0FF' if chart_type == "Income" else '#FF007F'
        self.trigger_sanctuary_zoom(display_cat_name, border_color, max_lbl_len, show_breakdown_rows, cleaned_subs,
                                    remainder, expected_total)

    def trigger_sanctuary_zoom(self, display_cat_name, border_color, max_lbl_len, show_breakdown_rows, cleaned_subs,
                               remainder, expected_total):
        """Launches a single centralized dark modal view container for sanctuary projection screens,
        utilizing an adaptive dual-axis scroll viewport that remains invisible until content overflows bounds.
        """
        if hasattr(self, 'modal_active') and self.modal_active:
            return

        self.modal_active = True
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

        self.zoom_modal = tk.Toplevel(self.root)
        self.zoom_modal.configure(bg='#161616', highlightbackground=border_color, highlightcolor=border_color,
                                  highlightthickness=2, bd=0)
        self.zoom_modal.wm_overrideredirect(True)

        app_w, app_h = self.root.winfo_width(), self.root.winfo_height()
        app_x, app_y = self.root.winfo_x(), self.root.winfo_y()

        modal_h = int(app_h * 0.80)
        modal_w = int(app_w * 0.45)
        if modal_w < 480: modal_w = 480

        self.zoom_modal.geometry(
            f"{modal_w}x{modal_h}+{app_x + (app_w // 2) - (modal_w // 2)}+{app_y + (app_h // 2) - (modal_h // 2)}")

        # High-Contrast Dot-Leader Alignment Matrix Calculations
        zoom_width = max_lbl_len + 12
        zoom_body_text = ""

        if show_breakdown_rows and cleaned_subs:
            for s_lbl, s_val in cleaned_subs:
                v_str = f"${int(s_val):,}"
                dots_needed = zoom_width - len(s_lbl) - len(v_str)
                dot_leader = " ." * (dots_needed // 2) + (" " if dots_needed % 2 != 0 else "")
                zoom_body_text += f" {s_lbl}{dot_leader}{v_str}\n"

        z_rem_str = f"${int(remainder if show_breakdown_rows else expected_total):,}"
        z_lbl_str = "Other Balance" if show_breakdown_rows else "Category Total"

        dots_needed = zoom_width - len(z_lbl_str) - len(z_rem_str)
        z_dot_leader = " ." * (dots_needed // 2) + (" " if dots_needed % 2 != 0 else "")
        zoom_body_text += f" {z_lbl_str}{z_dot_leader}{z_rem_str}"

        # Top Margin Padding & Structural Window Headers
        tk.Frame(self.zoom_modal, bg='#161616', height=25).pack()
        tk.Label(self.zoom_modal, text=f" {display_cat_name.upper()} LEDGER ", bg='#161616', fg='white',
                 font=('Arial', 16, 'bold')).pack(fill="x", pady=5)
        tk.Frame(self.zoom_modal, height=2, bg=border_color).pack(fill="x", padx=50, pady=(2, 10))

        # FEATURE IMPLEMENTATION: ADAPTIVE HIDDEN DUAL-AXIS SCROLL VIEWPORT
        # Core layout wrapper frame containing the canvas and adaptive scroll tracks
        viewport_frame = tk.Frame(self.zoom_modal, bg='#161616')
        viewport_frame.pack(fill="both", expand=True, padx=40, pady=5)

        zoom_canvas = tk.Canvas(viewport_frame, bg='#161616', bd=0, highlightthickness=0, yscrollincrement=10,
                                xscrollincrement=10)

        # Instantiate scrollbar hardware components safely linked to canvas matrix channels
        h_scrollbar = tk.Scrollbar(viewport_frame, orient="horizontal", command=zoom_canvas.xview)
        v_scrollbar = tk.Scrollbar(viewport_frame, orient="vertical", command=zoom_canvas.yview)
        zoom_canvas.configure(xscrollcommand=h_scrollbar.set, yscrollcommand=v_scrollbar.set)

        # Main inner container holding text blocks securely inside the viewport canvas
        inner_content_frame = tk.Frame(zoom_canvas, bg='#161616')
        canvas_win_id = zoom_canvas.create_window((0, 0), window=inner_content_frame, anchor="nw")

        # High-Contrast Ledger Body Label (Consolas Bold 14pt)
        m_body = tk.Label(inner_content_frame, text=zoom_body_text, bg='#161616', fg='#e0e0e0',
                          font=('Consolas', 14, 'bold'), justify="left")
        m_body.pack(fill="both", expand=True, padx=10, pady=10)

        def configure_adaptive_viewports(event):
            """Monitors content requirements dynamically, keeping scroll bars
            completely hidden unless text fields overlap container canvas margins.
            """
            inner_content_frame.update_idletasks()
            scroll_region = zoom_canvas.bbox("all")
            zoom_canvas.configure(scrollregion=scroll_region)

            canvas_w = zoom_canvas.winfo_width()
            canvas_h = zoom_canvas.winfo_height()
            content_w = inner_content_frame.winfo_reqwidth()
            content_h = inner_content_frame.winfo_reqheight()

            # Dynamic Horizontal Scrollbar Tracking
            if content_w > canvas_w:
                h_scrollbar.pack(side="bottom", fill="x")
            else:
                h_scrollbar.pack_forget()

            # Dynamic Vertical Scrollbar Tracking
            if content_h > canvas_h:
                v_scrollbar.pack(side="right", fill="y")
                zoom_canvas.pack(side="left", fill="both", expand=True)
            else:
                v_scrollbar.pack_forget()
                zoom_canvas.pack(side="top", fill="both", expand=True)

            # Symmetrical centering adjustments if content fits comfortably inside window bounds
            if content_w < canvas_w:
                x_offset = (canvas_w - content_w) // 2
                zoom_canvas.coords(canvas_win_id, x_offset, 0)
            else:
                zoom_canvas.coords(canvas_win_id, 0, 0)

        zoom_canvas.bind("<Configure>", configure_adaptive_viewports)
        inner_content_frame.bind("<Configure>", configure_adaptive_viewports)

        # Connect standard hardware mouse wheel gesture paths recursively into canvas channels
        def handle_modal_mouse_wheel(event):
            if event.num == 5 or event.delta < 0:
                zoom_canvas.yview_scroll(1, "units")
            elif event.num == 4 or event.delta > 0:
                zoom_canvas.yview_scroll(-1, "units")

        zoom_canvas.bind_all("<MouseWheel>", handle_modal_mouse_wheel)
        zoom_canvas.bind_all("<Button-4>", handle_modal_mouse_wheel)
        zoom_canvas.bind_all("<Button-5>", handle_modal_mouse_wheel)

        # Dismount Closure Release Routines
        def close_modal(*args):
            if hasattr(self, 'zoom_modal') and self.zoom_modal:
                self.zoom_modal.grab_release()
                self.zoom_modal.destroy()
                self.zoom_modal = None
            self.modal_active = False

        tk.Button(self.zoom_modal, text="[ Close Ledger View ]", command=close_modal,
                  bg='#161616', fg='#aaaaaa', activebackground='#161616', activeforeground='white',
                  font=('Arial', 12, 'bold'), bd=0, highlightthickness=0, cursor="hand2").pack(side="bottom", pady=25)

        self.zoom_modal.update_idletasks()
        self.zoom_modal.transient(self.root)
        self.zoom_modal.grab_set()
        self.zoom_modal.focus_force()
        self.zoom_modal.bind("<Escape>", close_modal)

    def load_initial_data(self):
        """Loads budget dataset configurations from the Current Working Directory (CWD),
        falling back to the Desktop, or defaults to hardcoded allocations seamlessly.
        """
        # -----------------------------------------------------------------
        # SILENT DIRECTORY DISPATCHER PATHS (PREVENTS EARLY CRASHES)
        # -----------------------------------------------------------------
        exec_dir = os.getcwd()
        cwd_csv_filename = os.path.join(exec_dir, "budget_data.csv")

        desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
        desktop_csv_filename = os.path.join(desktop_dir, "budget_data.csv")

        # Check which file takes precedence without interrupting thread initialization
        if os.path.exists(cwd_csv_filename):
            csv_filename = cwd_csv_filename
            self.last_import_dir = exec_dir
        elif os.path.exists(desktop_csv_filename):
            csv_filename = desktop_csv_filename
            self.last_import_dir = desktop_dir
        else:
            self.load_hardcoded_defaults()
            # Ensure the text safely locks to "Create" if both paths come up empty
            if hasattr(self, 'btn_save') and self.btn_save:
                self.btn_save.config(text="Create CSV File")
            return

        # If the file path check succeeds and we parse rows, ensure the text reads "Update"
        if hasattr(self, 'btn_save') and self.btn_save:
            self.btn_save.config(text="Update CSV File")

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
                        # Removed the internal conditional loop block that was printing
                        # duplicate EXPENSE CONFIG label rows down the scrolling panel frame tree.
                        if category == "Expense Title":
                            self.expense_title_var.set(row.get('Title text', 'Budget Expenses Breakdown'))
                        elif "Total" in category:
                            _, self.exp_total_val = self.add_input_row(self.exp_frame, category, amount, is_total=True)
                        else:
                            self.expense_inputs.append(self.add_input_row(self.exp_frame, category, amount))

            # Re-attach operational addition buttons right beneath sorted data list elements
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
        safely utilizing pre-registered layout headers from create_left_panel.
        """
        # Populate Income allocation entry rows
        _, self.inc_total_val = self.add_input_row(self.inc_frame, "Total Income", 429000, is_total=True)
        self.income_inputs.append(self.add_input_row(self.inc_frame, "Giving", 383000))
        self.income_inputs.append(self.add_input_row(self.inc_frame, "Partners", 42000))

        tk.Button(self.inc_frame, text="+ Add Income Item", command=lambda: self.add_blank_row("Income"),
                  bg='#111111', fg='#00F0FF', font=('Arial', 8, 'bold'), bd=0, cursor="hand2").pack(anchor="w", padx=7,
                                                                                                    pady=5)

        # Populate Expense allocation entry rows
        _, self.exp_total_val = self.add_input_row(self.exp_frame, "Total Expense", 453400, is_total=True)

        # Enforce the uniform Pink/Red theme color directly on the Expense Total widget row fields
        total_row_frame = self.exp_frame.pack_slaves()[-1]
        for child in total_row_frame.winfo_children():
            if isinstance(child, tk.Entry):
                child.config(disabledforeground='#FF007F', fg='#FF007F')

        self.expense_inputs.append(self.add_input_row(self.exp_frame, "Clergy", 211400))
        self.expense_inputs.append(self.add_input_row(self.exp_frame, "Lay Ministry", 109400))
        self.expense_inputs.append(self.add_input_row(self.exp_frame, "Building", 64900))
        self.expense_inputs.append(self.add_input_row(self.exp_frame, "Admin", 20000))
        self.expense_inputs.append(self.add_input_row(self.exp_frame, "Worship", 7700))
        self.expense_inputs.append(self.add_input_row(self.exp_frame, "Faith Form.", 5000))

        tk.Button(self.exp_frame, text="+ Add Expense Item", command=lambda: self.add_blank_row("Expense"),
                  bg='#111111', fg='#FF007F', font=('Arial', 8, 'bold'), bd=0, cursor="hand2").pack(anchor="w", padx=7,
                                                                                                    pady=5)

        # Attach real-time modification listener traces and force rendering update pass
        self.income_title_var.trace_add("write", lambda *args: self.process_inputs(is_live=True))
        self.expense_title_var.trace_add("write", lambda *args: self.process_inputs(is_live=True))
        self.process_inputs(is_live=False)

    def process_inputs(self, is_live=False):
        if hasattr(self, 'is_updating') and self.is_updating:
            return
        try:
            self.is_updating = True

            # Added a rigid structural guard to ensure plain text fields are never locked out
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
            # Extract tuple numeric values index x[1] for proper mathematical summation
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
            # Extract tuple numeric values index x[1] for proper mathematical summation
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

            if hasattr(self, 'net_summary_lbl'):
                try:
                    net_position_val = self.total_income - self.total_expenses
                    if net_position_val >= 0:
                        self.net_summary_lbl.config(text=f"Net Surplus: +${int(net_position_val):,}", fg='#00F0FF')
                    else:
                        self.net_summary_lbl.config(text=f"Net Deficit: -${int(abs(net_position_val)):,}", fg='#FF007F')
                except (ValueError, TypeError, AttributeError):
                    pass


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

        view_mode = self.chart_view_mode_var.get() if hasattr(self, 'chart_view_mode_var') else "Both"
        available_h = w_height - 90

        # Toggle grid visibility and calculate available width based on single vs. dual chart mode
        if view_mode == "Both":
            self.canvas_inc.get_tk_widget().grid(row=0, column=0, padx=15, pady=5)
            self.canvas_exp.get_tk_widget().grid(row=0, column=1, padx=15, pady=5)
            available_w = (right_panel_w - 85) // 2
        elif view_mode == "Income":
            self.canvas_exp.get_tk_widget().grid_remove()
            self.canvas_inc.get_tk_widget().grid(row=0, column=0, padx=15, pady=5)
            available_w = right_panel_w - 50
        else:  # "Expense"
            self.canvas_inc.get_tk_widget().grid_remove()
            self.canvas_exp.get_tk_widget().grid(row=0, column=0, padx=15, pady=5)
            available_w = right_panel_w - 50

        size_pixels_h = max(150, available_h)
        # Cap single-chart width slightly relative to height so the circle stays centered without excessive horizontal blank space
        max_reasonable_w = int(size_pixels_h * 1.45) if view_mode != "Both" else available_w
        size_pixels_w = max(150, min(available_w, max_reasonable_w))

        size_inches_h = size_pixels_h / 100.0
        size_inches_w = size_pixels_w / 100.0

        # Boost font size slightly when presenting a single chart on a projector
        base_font = 8.2 if view_mode != "Both" else 7.2
        font_sz = min(11.0, max(base_font, base_font + (size_inches_h * 0.40)))
        thresh = min(0.24, max(0.15, 0.26 - (size_inches_h * 0.022)))

        if view_mode in ("Both", "Income"):
            self.fig_income.set_size_inches(size_inches_w, size_inches_h)
            self.income_wedges = create_smart_pie(
                self.fig_income, self.income_sizes, self.income_labels, self.total_income,
                self.income_title_var.get(), '#00F0FF', font_sz, thresh
            )
            if self.canvas_inc:
                self.canvas_inc.get_tk_widget().configure(width=size_pixels_w, height=size_pixels_h)
                self.canvas_inc.draw()

        if view_mode in ("Both", "Expense"):
            self.fig_expense.set_size_inches(size_inches_w, size_inches_h)
            self.expense_wedges = create_smart_pie(
                self.fig_expense, self.expense_sizes, self.expense_labels, self.total_expenses,
                self.expense_title_var.get(), '#FF007F', font_sz, thresh
            )
            if self.canvas_exp:
                self.canvas_exp.get_tk_widget().configure(width=size_pixels_w, height=size_pixels_h)
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
        """Secure saving routine that routes dataset files directly into the last
        imported Excel directory source folder, falling back to the Desktop natively.
        """

        # DYNAMIC PATH ROUTING ENGINE
        # Check if an Excel directory or startup directory has been registered during this session
        if hasattr(self, 'last_import_dir') and self.last_import_dir:
            target_dir = self.last_import_dir
            location_description = f"Current Session Target Folder:\n{target_dir}"
        else:
            # Fall back directly to the running executable's parent application folder
            target_dir = os.getcwd()
            location_description = f"Local Application Executable Folder:\n{target_dir}"

        csv_filename = os.path.join(target_dir, "budget_data.csv")

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

            # Dynamically flip the label to "Update" right as the file writes successfully
            if hasattr(self, 'btn_save') and self.btn_save:
                self.btn_save.config(text="Update CSV File")

            # Inform the user explicitly of the folder location where the file compiled
            messagebox.showinfo("Success",
                                f"Budget dataset modifications saved successfully to:\n\n{location_description}\n\nFile Name: budget_data.csv")
        except Exception as e:
            messagebox.showerror("Save Error", f"Could not compile local file storage paths:\n{str(e)}")


if __name__ == "__main__":
    root = tk.Tk()
    app = InteractiveDashboard(root)
    root.update()
    app.on_resize()
    root.mainloop()
