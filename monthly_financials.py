import csv
import os
import re
import tkinter as tk
from tkinter import messagebox, ttk
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from monthly_importer import import_financial_spreadsheet
from Chart_Engine import create_monthly_line_chart

ALL_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


class MonthlyFinancialsView:
    """Self-contained Monthly Financials view (Left Input Table + Right Dual-Line Chart)."""

    def __init__(self, app, left_container, right_container):
        self.app = app
        self.left_container = left_container
        self.right_container = right_container

        self.initialized = False
        self.tooltip = None
        self.tooltip_frozen = False
        self.tooltip_hint_lbl = None
        self.modal_active = False
        self.zoom_modal = None
        self.zoom_font_size = 14
        self.hover_vline = None
        self.hover_dot = None

        self.title_var = tk.StringVar(value="2026 Monthly Financial Results")
        self.include_surplus_var = tk.BooleanVar(value=True)
        self.show_forecast_var = tk.BooleanVar(value=True)
        self.chart_mode_var = tk.StringVar(value="Cumulative")
        self.view_profile_var = tk.StringVar(value="Bookkeeper Mode (Full Details)")
        self.show_acct_nums_var = tk.BooleanVar(value=False)

        self.records = []
        self.row_widgets = []

        self.fig = Figure(figsize=(8, 5), dpi=100, facecolor='#111111')
        self.ax = None
        self.canvas = None

        self.build_ui()

    def ensure_initialized(self):
        """Initializes Monthly Financials on first visit, and refreshes any Forecast ('Fcst')
        months from the active Budget tab whenever no saved monthly_financials.csv overrides them.
        """
        if not self.initialized:
            self.initialized = True
            self.load_initial_financial_data()
            return

        # If no monthly_financials.csv exists yet, keep all Forecast ('Fcst') rows synced
        # with the latest numbers on the Budget tab (including newly imported Budget Excel data)
        exec_dir = os.getcwd()
        cwd_csv = os.path.join(exec_dir, "monthly_financials.csv")
        desktop_csv = os.path.join(os.path.expanduser("~"), "Desktop", "monthly_financials.csv")

        if not os.path.exists(cwd_csv) and not os.path.exists(desktop_csv):
            base = self.get_budget_monthly_baseline()
            for rec in self.records:
                if rec.get("is_forecast", True):
                    rec["income"] = round(base["income"], 2)
                    rec["expense"] = round(base["expense"], 2)
                    rec["other_income"] = round(base["other_income"], 2)
                    rec["inc_cats"] = {k: list(v) for k, v in base["inc_cats"].items()}
                    rec["exp_cats"] = {k: list(v) for k, v in base["exp_cats"].items()}
                    rec["other_cats"] = {k: list(v) for k, v in base["other_cats"].items()}
                    # Refresh snapshot so 'Restore' matches the new Budget baseline
                    rec["_orig_snapshot"] = {
                        "month": rec["month"],
                        "income": rec["income"],
                        "other_income": rec["other_income"],
                        "expense": rec["expense"],
                        "is_forecast": rec["is_forecast"]
                    }
            self.rebuild_left_table()

        self.redraw_chart()

    def clean_label(self, raw_text):
        """Strips leading account numbers if 'Acct #s' is unchecked."""
        if self.show_acct_nums_var.get():
            return raw_text.strip()
        cleaned = re.sub(r'^[\d\-\.]+\s+', '', raw_text.strip())
        return cleaned if cleaned else raw_text.strip()

    def build_ui(self):
        # ---------------- LEFT PANEL ----------------
        title_box = tk.Frame(self.left_container, bg='#111111')
        title_box.pack(side="top", fill="x", padx=12, pady=(8, 4))
        tk.Label(title_box, text="FINANCIAL CHART TITLE", fg='#00F0FF', bg='#111111',
                 font=('Arial', 8, 'bold')).pack(anchor="w")
        title_ent = tk.Entry(title_box, textvariable=self.title_var, bg='#1e1e1e', fg='white',
                             insertbackground='white', bd=1, relief="solid", font=('Arial', 9, 'bold'))
        title_ent.pack(fill="x", pady=(2, 4))
        self.title_var.trace_add("write", lambda *args: self.redraw_chart())

        # Table Column Headers (Grid-aligned with data rows below)
        hdr_frame = tk.Frame(self.left_container, bg='#1a1a1a')
        hdr_frame.pack(side="top", fill="x", padx=8, pady=(4, 0))
        hdr_frame.columnconfigure(0, minsize=38)
        hdr_frame.columnconfigure(1, weight=1)
        hdr_frame.columnconfigure(2, weight=1)
        hdr_frame.columnconfigure(3, minsize=36)

        tk.Label(hdr_frame, text="Mo", bg='#1a1a1a', fg='#aaaaaa', font=('Arial', 8, 'bold'), anchor="w").grid(row=0, column=0, sticky="w", padx=3, pady=2)
        tk.Label(hdr_frame, text="Income", bg='#1a1a1a', fg='#00F0FF', font=('Arial', 8, 'bold'), anchor="e").grid(row=0, column=1, sticky="e", padx=4, pady=2)
        tk.Label(hdr_frame, text="Expense", bg='#1a1a1a', fg='#FF007F', font=('Arial', 8, 'bold'), anchor="e").grid(row=0, column=2, sticky="e", padx=4, pady=2)
        tk.Label(hdr_frame, text="Type", bg='#1a1a1a', fg='#888888', font=('Arial', 8, 'bold'), anchor="center").grid(row=0, column=3, sticky="ew", padx=2, pady=2)

        self.scroll_outer = tk.Frame(self.left_container, bg='#111111')
        self.scroll_outer.pack(side="top", fill="x", expand=False, padx=8, pady=(2, 4))

        self.scroll_canvas = tk.Canvas(self.scroll_outer, bg='#111111', bd=0, highlightthickness=0, width=180)
        self.scroll_canvas.pack(side="left", fill="both", expand=True)

        self.v_scrollbar = ttk.Scrollbar(self.scroll_outer, orient="vertical", command=self.scroll_canvas.yview,
                                         style="Dark.Vertical.TScrollbar")
        self.scroll_canvas.configure(yscrollcommand=self.v_scrollbar.set)

        self.rows_inner_frame = tk.Frame(self.scroll_canvas, bg='#111111')
        self.canvas_win_id = self.scroll_canvas.create_window((0, 0), window=self.rows_inner_frame, anchor="nw")

        self.rows_inner_frame.bind("<Configure>", self.sync_left_scroll_height)
        self.left_container.bind("<Configure>", self.sync_left_scroll_height)
        self.scroll_canvas.bind("<Configure>", lambda e: self.scroll_canvas.itemconfig(self.canvas_win_id, width=e.width))
        summary_frame = tk.Frame(self.left_container, bg='#111111')
        summary_frame.pack(side="top", fill="x", padx=12, pady=(4, 4))

        tk.Frame(summary_frame, height=1, bg='#333333').pack(fill="x", pady=(0, 4))
        self.tot_inc_lbl = tk.Label(summary_frame, text="Total Income: $0", fg='#00F0FF', bg='#111111',
                                    font=('Arial', 9, 'bold'), anchor="w")
        self.tot_inc_lbl.pack(fill="x")
        self.tot_exp_lbl = tk.Label(summary_frame, text="Total Expenses: $0", fg='#FF007F', bg='#111111',
                                    font=('Arial', 9, 'bold'), anchor="w")
        self.tot_exp_lbl.pack(fill="x")
        self.net_pos_lbl = tk.Label(summary_frame, text="Net Position: $0", fg='white', bg='#111111',
                                    font=('Arial', 10, 'bold'), anchor="w")
        self.net_pos_lbl.pack(fill="x", pady=(2, 0))
        tk.Frame(summary_frame, height=1, bg='#333333').pack(fill="x", pady=(4, 0))

        actions_frame = tk.Frame(self.left_container, bg='#111111')
        actions_frame.pack(side="bottom", fill="x", padx=15, pady=(5, 15))

        tk.Button(actions_frame, text="Import Financial Spreadsheet",
                  command=lambda: import_financial_spreadsheet(self),
                  bg='#FF00FF', fg='black', activebackground='#ff66ff', activeforeground='black',
                  font=('Arial', 9, 'bold'), bd=0, height=2, cursor="hand2").pack(fill="x", pady=4)

        tk.Button(actions_frame, text="Update Chart", command=self.redraw_chart,
                  bg='#00F0FF', fg='black', activebackground='#66f5ff', activeforeground='black',
                  font=('Arial', 9, 'bold'), bd=0, height=2, cursor="hand2").pack(fill="x", pady=4)

        self.btn_save_csv = tk.Button(actions_frame, text="Create CSV File", command=self.save_to_csv,
                                      bg='#FFaa00', fg='black', activebackground='#ffcc66', activeforeground='black',
                                      font=('Arial', 9, 'bold'), bd=0, height=2, cursor="hand2")
        self.btn_save_csv.pack(fill="x", pady=4)

        tk.Button(actions_frame, text="Save Chart to Desktop", command=self.prompt_and_export_chart,
                  bg='#00FF66', fg='black', activebackground='#66ff99', activeforeground='black',
                  font=('Arial', 9, 'bold'), bd=0, height=2, cursor="hand2").pack(fill="x", pady=4)

        # ---------------- RIGHT PANEL ----------------
        self.right_container.rowconfigure(0, weight=1)
        self.right_container.columnconfigure(0, weight=1)

        chart_holder = tk.Frame(self.right_container, bg='#111111')
        chart_holder.grid(row=0, column=0, sticky="nsew", padx=15, pady=5)
        chart_holder.rowconfigure(0, weight=1)
        chart_holder.columnconfigure(0, weight=1)

        self.canvas = FigureCanvasTkAgg(self.fig, master=chart_holder)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

        ctrl_bar = tk.Frame(self.right_container, bg='#111111')
        ctrl_bar.grid(row=1, column=0, sticky="ew", padx=20, pady=10)

        tk.Checkbutton(
            ctrl_bar, text="Include PY Surplus", variable=self.include_surplus_var,
            bg='#111111', fg='#aaaaaa', selectcolor='#1e1e1e',
            activebackground='#111111', activeforeground='white',
            font=('Arial', 9, 'bold'), command=self.on_surplus_toggle
        ).pack(side="left", padx=(0, 10))

        tk.Checkbutton(
            ctrl_bar, text="Show 12-Mo Forecast", variable=self.show_forecast_var,
            bg='#111111', fg='#aaaaaa', selectcolor='#1e1e1e',
            activebackground='#111111', activeforeground='white',
            font=('Arial', 9, 'bold'), command=self.redraw_chart
        ).pack(side="left", padx=(0, 10))

        tk.Checkbutton(
            ctrl_bar, text="Acct #s", variable=self.show_acct_nums_var,
            bg='#111111', fg='#aaaaaa', selectcolor='#1e1e1e',
            activebackground='#111111', activeforeground='white',
            font=('Arial', 9, 'bold'), command=self.redraw_chart
        ).pack(side="left", padx=(0, 12))

        profile_combo = ttk.Combobox(
            ctrl_bar, textvariable=self.view_profile_var,
            values=["Bookkeeper Mode (Full Details)", "Public Mode (Hide Salaries)", "Silence All Tooltips"],
            state="readonly", font=('Arial', 9), width=22
        )
        profile_combo.pack(side="left", padx=(0, 12))

        mode_frame = tk.Frame(ctrl_bar, bg='#111111')
        mode_frame.pack(side="right")
        for lbl, val in [("Monthly", "Monthly"), ("Cumulative YTD", "Cumulative")]:
            tk.Radiobutton(
                mode_frame, text=lbl, variable=self.chart_mode_var, value=val,
                bg='#111111', fg='#00F0FF' if val == "Cumulative" else 'white',
                selectcolor='#1e1e1e', activebackground='#111111', activeforeground='white',
                font=('Arial', 9, 'bold'), cursor="hand2", command=self.redraw_chart
            ).pack(side="left", padx=4)

        self.canvas.mpl_connect("motion_notify_event", self.handle_hover)
        self.canvas.mpl_connect("button_press_event", self.handle_click)
        self.right_container.bind("<Configure>", lambda e: self.redraw_chart())

    def sync_left_scroll_height(self, event=None):
        self.scroll_canvas.configure(scrollregion=self.scroll_canvas.bbox("all"))
        panel_h = self.left_container.winfo_height()
        if panel_h < 80:
            return
        content_h = self.rows_inner_frame.winfo_reqheight()
        max_canvas_h = max(90, panel_h - 365)
        if content_h <= max_canvas_h:
            self.scroll_canvas.configure(height=content_h)
            self.v_scrollbar.pack_forget()
            self.scroll_canvas.yview_moveto(0)
        else:
            self.scroll_canvas.configure(height=max_canvas_h)
            if not self.v_scrollbar.winfo_ismapped():
                self.v_scrollbar.pack(side="right", fill="y")
    def load_initial_financial_data(self):
        exec_dir = os.getcwd()
        cwd_csv = os.path.join(exec_dir, "monthly_financials.csv")
        desktop_csv = os.path.join(os.path.expanduser("~"), "Desktop", "monthly_financials.csv")

        if os.path.exists(cwd_csv):
            self.load_from_csv(cwd_csv)
            self.btn_save_csv.config(text="Update CSV File")
        elif os.path.exists(desktop_csv):
            self.load_from_csv(desktop_csv)
            self.btn_save_csv.config(text="Update CSV File")
        else:
            self.seed_from_active_budget()
            self.btn_save_csv.config(text="Create CSV File")

        self.rebuild_left_table()
        self.redraw_chart()

    def get_budget_monthly_baseline(self):
        """Calculates monthly average Income, Other Income (PY Surplus), and Expenses from active Budget tab,
        including any implied 'Other' remainder between category sums and Budget Totals.
        """
        inc_operating, other_surplus = 0.0, 0.0
        inc_cats, other_cats = {}, {}

        for lbl_var, val_var in self.app.income_inputs:
            raw_lbl = lbl_var.get().strip()
            try:
                monthly_val = float(val_var.get() or 0.0) / 12.0
            except ValueError:
                monthly_val = 0.0

            subs = []
            for k, items in self.app.subcategories.items():
                if raw_lbl == k or raw_lbl == self.app.clean_label_text(k):
                    subs = [(s_l, s_v / 12.0) for s_l, s_v in items]
                    break
            if not subs and monthly_val != 0:
                subs = [(raw_lbl, monthly_val)]

            if "surplus" in raw_lbl.lower():
                other_surplus += monthly_val
                other_cats[raw_lbl] = subs
            else:
                inc_operating += monthly_val
                inc_cats[raw_lbl] = subs

        # Include implied "Other" income if Budget Total Income exceeds sum of entered income categories
        budget_tot_inc_mo = float(getattr(self.app.budget_view, 'total_income', 0.0)) / 12.0
        inc_other_rem = round(budget_tot_inc_mo - (inc_operating + other_surplus), 2)
        if inc_other_rem > 0.01:
            inc_operating += inc_other_rem
            inc_cats["Other Income (Implied)"] = [("Other", inc_other_rem)]

        exp_total, exp_cats = 0.0, {}
        for lbl_var, val_var in self.app.expense_inputs:
            raw_lbl = lbl_var.get().strip()
            try:
                monthly_val = float(val_var.get() or 0.0) / 12.0
            except ValueError:
                monthly_val = 0.0
            exp_total += monthly_val

            subs = []
            for k, items in self.app.subcategories.items():
                if raw_lbl == k or raw_lbl == self.app.clean_label_text(k):
                    subs = [(s_l, s_v / 12.0) for s_l, s_v in items]
                    break
            if not subs and monthly_val != 0:
                subs = [(raw_lbl, monthly_val)]
            exp_cats[raw_lbl] = subs

        # Include implied "Other" expense if Budget Total Expenses exceeds sum of entered expense categories
        budget_tot_exp_mo = float(getattr(self.app.budget_view, 'total_expenses', 0.0)) / 12.0
        exp_other_rem = round(budget_tot_exp_mo - exp_total, 2)
        if exp_other_rem > 0.01:
            exp_total += exp_other_rem
            exp_cats["Other Expenses (Implied)"] = [("Other", exp_other_rem)]

        return {
            "income": inc_operating, "other_income": other_surplus, "expense": exp_total,
            "inc_cats": inc_cats, "other_cats": other_cats, "exp_cats": exp_cats
        }

    def seed_from_active_budget(self):
        base = self.get_budget_monthly_baseline()
        self.records = []
        for m in ALL_MONTHS:
            self.records.append({
                "month": m, "income": round(base["income"], 2), "expense": round(base["expense"], 2),
                "other_income": round(base["other_income"], 2), "is_forecast": True,
                "inc_cats": {k: list(v) for k, v in base["inc_cats"].items()},
                "exp_cats": {k: list(v) for k, v in base["exp_cats"].items()},
                "other_cats": {k: list(v) for k, v in base["other_cats"].items()}
            })

    def apply_imported_financials(self, actuals_data, excel_budget_data):
        budget_tab_base = self.get_budget_monthly_baseline()

        if excel_budget_data and excel_budget_data["ordered_months"]:
            b_months = excel_budget_data["ordered_months"]
            n_b = len(b_months)
            xl_avg_inc = sum(excel_budget_data["months"][m]["income"] + excel_budget_data["months"][m]["other_income"] for m in b_months) / n_b
            xl_avg_exp = sum(excel_budget_data["months"][m]["expense"] for m in b_months) / n_b
            app_avg_inc = budget_tab_base["income"] + budget_tab_base["other_income"]
            app_avg_exp = budget_tab_base["expense"]

            if abs(xl_avg_inc - app_avg_inc) > 1.0 or abs(xl_avg_exp - app_avg_exp) > 1.0:
                messagebox.showinfo(
                    "Budget Comparison Notice",
                    "The monthly budget averages in the Financial spreadsheet differ from the active Budget tab:\n\n"
                    f"Monthly Budgeted Income:\n  • Financial Excel Tab:  ${xl_avg_inc:,.2f}\n  • App Budget Tab:       ${app_avg_inc:,.2f}\n\n"
                    f"Monthly Budgeted Expenses:\n  • Financial Excel Tab:  ${xl_avg_exp:,.2f}\n  • App Budget Tab:       ${app_avg_exp:,.2f}\n\n"
                    "Proceeding with the imported financial data."
                )

        actual_months_set = set(actuals_data["ordered_months"])
        if excel_budget_data and excel_budget_data["ordered_months"]:
            b_m_list = excel_budget_data["ordered_months"]
            n_bm = len(b_m_list)
            fallback_forecast = {
                "income": sum(excel_budget_data["months"][m]["income"] for m in b_m_list) / n_bm,
                "other_income": sum(excel_budget_data["months"][m]["other_income"] for m in b_m_list) / n_bm,
                "expense": sum(excel_budget_data["months"][m]["expense"] for m in b_m_list) / n_bm,
                "inc_cats": excel_budget_data["months"][b_m_list[-1]]["inc_cats"],
                "other_cats": excel_budget_data["months"][b_m_list[-1]]["other_cats"],
                "exp_cats": excel_budget_data["months"][b_m_list[-1]]["exp_cats"],
            }
        else:
            fallback_forecast = budget_tab_base

        new_records = []
        for m in ALL_MONTHS:
            if m in actual_months_set:
                m_obj = actuals_data["months"][m]
                new_records.append({
                    "month": m, "income": round(m_obj["income"], 2), "expense": round(m_obj["expense"], 2),
                    "other_income": round(m_obj["other_income"], 2), "is_forecast": False,
                    "inc_cats": m_obj["inc_cats"], "exp_cats": m_obj["exp_cats"], "other_cats": m_obj["other_cats"]
                })
            else:
                src = excel_budget_data["months"][m] if (excel_budget_data and m in excel_budget_data["months"]) else fallback_forecast
                new_records.append({
                    "month": m, "income": round(src["income"], 2), "expense": round(src["expense"], 2),
                    "other_income": round(src["other_income"], 2), "is_forecast": True,
                    "inc_cats": {k: list(v) for k, v in src["inc_cats"].items()},
                    "exp_cats": {k: list(v) for k, v in src["exp_cats"].items()},
                    "other_cats": {k: list(v) for k, v in src["other_cats"].items()}
                })

        self.records = new_records
        self.rebuild_left_table()
        self.redraw_chart()

    def on_surplus_toggle(self):
        """Updates displayed monthly Income entries in the left table and redraws the chart."""
        self._suppress_live_trace = True
        inc_surplus = self.include_surplus_var.get()
        for idx, (mo_v, inc_v, exp_v, fc_v) in enumerate(self.row_widgets):
            if idx >= len(self.records):
                break
            rec = self.records[idx]
            disp_inc = rec["income"] + (rec["other_income"] if inc_surplus else 0.0)
            inc_v.set(f"{disp_inc:.0f}")
        self._suppress_live_trace = False
        self.redraw_chart()

    def rebuild_left_table(self):
        for w in self.rows_inner_frame.winfo_children():
            w.destroy()
        self.row_widgets = []
        self._suppress_live_trace = True
        inc_surplus = self.include_surplus_var.get()

        # Save a complete snapshot of each row's values (including other_income / PY Surplus)
        for rec in self.records:
            if "_orig_snapshot" not in rec:
                rec["_orig_snapshot"] = {
                    "month": rec["month"],
                    "income": rec["income"],
                    "other_income": rec.get("other_income", 0.0),
                    "expense": rec["expense"],
                    "is_forecast": rec["is_forecast"]
                }

        def show_row_context_menu(event, r_idx):
            menu = tk.Menu(self.app.root, tearoff=0, bg='#1e1e1e', fg='white',
                           activebackground='#00F0FF', activeforeground='black', font=('Arial', 9, 'bold'))
            mo_name = self.records[r_idx]["month"]
            menu.add_command(label=f"Clear '{mo_name}' ($0)", command=lambda: clear_row(r_idx))
            menu.add_command(label=f"Restore '{mo_name}'", command=lambda: restore_row(r_idx))
            menu.tk_popup(event.x_root, event.y_root)

        def clear_row(r_idx):
            if 0 <= r_idx < len(self.records):
                self._suppress_live_trace = True
                self.records[r_idx]["income"] = 0.0
                self.records[r_idx]["other_income"] = 0.0
                self.records[r_idx]["expense"] = 0.0
                _, inc_v, exp_v, _ = self.row_widgets[r_idx]
                inc_v.set("0")
                exp_v.set("0")
                self._suppress_live_trace = False
                self.redraw_chart()

        def restore_row(r_idx):
            if 0 <= r_idx < len(self.records) and "_orig_snapshot" in self.records[r_idx]:
                snap = self.records[r_idx]["_orig_snapshot"]
                self._suppress_live_trace = True
                self.records[r_idx]["month"] = snap["month"]
                self.records[r_idx]["income"] = snap["income"]
                self.records[r_idx]["other_income"] = snap.get("other_income", 0.0)
                self.records[r_idx]["expense"] = snap["expense"]
                self.records[r_idx]["is_forecast"] = snap["is_forecast"]
                mo_v, inc_v, exp_v, fc_v = self.row_widgets[r_idx]
                disp_i = snap["income"] + (snap.get("other_income", 0.0) if self.include_surplus_var.get() else 0.0)
                mo_v.set(snap["month"])
                inc_v.set(f"{disp_i:.0f}")
                exp_v.set(f"{snap['expense']:.0f}")
                fc_v.set(snap["is_forecast"])
                self._suppress_live_trace = False
                self.redraw_chart()

        def on_live_edit(r_idx):
            if getattr(self, '_suppress_live_trace', False) or r_idx >= len(self.records):
                return
            rec = self.records[r_idx]
            mo_v, inc_v, exp_v, fc_v = self.row_widgets[r_idx]
            rec["month"] = mo_v.get().strip() or rec["month"]
            try:
                typed_inc = float(inc_v.get().replace(',', '') or 0.0)
                if self.include_surplus_var.get():
                    rec["income"] = typed_inc - rec.get("other_income", 0.0)
                else:
                    rec["income"] = typed_inc
            except ValueError:
                pass
            try:
                rec["expense"] = float(exp_v.get().replace(',', '') or 0.0)
            except ValueError:
                pass
            self.redraw_chart()

        for idx, rec in enumerate(self.records):
            row_f = tk.Frame(self.rows_inner_frame, bg='#111111')
            row_f.pack(fill="x", pady=1)
            row_f.columnconfigure(0, minsize=38)
            row_f.columnconfigure(1, weight=1)
            row_f.columnconfigure(2, weight=1)
            row_f.columnconfigure(3, minsize=36)

            disp_inc = rec["income"] + (rec["other_income"] if inc_surplus else 0.0)
            mo_var = tk.StringVar(value=rec["month"])
            inc_var = tk.StringVar(value=f"{disp_inc:.0f}")
            exp_var = tk.StringVar(value=f"{rec['expense']:.0f}")
            fc_var = tk.BooleanVar(value=rec["is_forecast"])

            fg_tint = '#888888' if rec["is_forecast"] else 'white'
            ent_mo = tk.Entry(row_f, textvariable=mo_var, bg='#1a1a1a', fg=fg_tint, insertbackground='white',
                              bd=1, relief="solid", font=('Arial', 8, 'bold'), width=4)
            ent_mo.grid(row=0, column=0, sticky="ew", padx=2)

            ent_inc = tk.Entry(row_f, textvariable=inc_var, bg='#1a1a1a', fg='#00F0FF', insertbackground='white',
                               bd=1, relief="solid", font=('Arial', 8, 'bold'), width=7, justify="right")
            ent_inc.grid(row=0, column=1, sticky="ew", padx=2)

            ent_exp = tk.Entry(row_f, textvariable=exp_var, bg='#1a1a1a', fg='#FF007F', insertbackground='white',
                               bd=1, relief="solid", font=('Arial', 8, 'bold'), width=7, justify="right")
            ent_exp.grid(row=0, column=2, sticky="ew", padx=2)

            def toggle_forecast_flag(r_idx=idx, var=fc_var, btn=None):
                new_state = not var.get()
                var.set(new_state)
                self.records[r_idx]["is_forecast"] = new_state
                if btn:
                    btn.config(text="Fcst" if new_state else "Act", fg='#ffaa00' if new_state else '#00FF66')
                self.redraw_chart()

            type_btn = tk.Button(row_f, text="Fcst" if rec["is_forecast"] else "Act", bg='#1e1e1e',
                                 fg='#ffaa00' if rec["is_forecast"] else '#00FF66',
                                 font=('Arial', 7, 'bold'), bd=0, width=4, cursor="hand2")
            type_btn.config(command=lambda i=idx, v=fc_var, b=type_btn: toggle_forecast_flag(i, v, b))
            type_btn.grid(row=0, column=3, sticky="ew", padx=2)

            for w in (row_f, ent_mo, ent_inc, ent_exp, type_btn):
                w.bind("<Button-3>", lambda e, i=idx: show_row_context_menu(e, i))

            mo_var.trace_add("write", lambda *args, i=idx: on_live_edit(i))
            inc_var.trace_add("write", lambda *args, i=idx: on_live_edit(i))
            exp_var.trace_add("write", lambda *args, i=idx: on_live_edit(i))

            self.row_widgets.append((mo_var, inc_var, exp_var, fc_var))

        self._suppress_live_trace = False
        self.sync_left_scroll_height()

    def sync_from_entries_and_redraw(self):
        inc_surplus = self.include_surplus_var.get()
        for idx, (mo_v, inc_v, exp_v, fc_v) in enumerate(self.row_widgets):
            if idx >= len(self.records):
                break
            rec = self.records[idx]
            rec["month"] = mo_v.get().strip() or rec["month"]
            try:
                typed_inc = float(inc_v.get().replace(',', '') or 0.0)
                # Keep operating income and other_income cleanly separated without double-counting
                if inc_surplus:
                    rec["income"] = max(0.0, typed_inc - rec.get("other_income", 0.0))
                else:
                    rec["income"] = typed_inc
            except ValueError:
                pass
            try:
                rec["expense"] = float(exp_v.get().replace(',', '') or 0.0)
            except ValueError:
                pass
            rec["is_forecast"] = fc_v.get()
        self.redraw_chart()

    def add_month_row(self):
        next_mo = ALL_MONTHS[len(self.records) % 12]
        self.records.append({
            "month": next_mo, "income": 0.0, "expense": 0.0, "other_income": 0.0,
            "is_forecast": True, "inc_cats": {}, "exp_cats": {}, "other_cats": {}
        })
        self.rebuild_left_table()
        self.redraw_chart()

    def sync_from_entries_and_redraw(self):
        for idx, (mo_v, inc_v, exp_v, fc_v) in enumerate(self.row_widgets):
            if idx >= len(self.records):
                break
            self.records[idx]["month"] = mo_v.get().strip() or self.records[idx]["month"]
            try:
                self.records[idx]["income"] = float(inc_v.get().replace(',', '') or 0.0)
            except ValueError:
                pass
            try:
                self.records[idx]["expense"] = float(exp_v.get().replace(',', '') or 0.0)
            except ValueError:
                pass
            self.records[idx]["is_forecast"] = fc_v.get()
        self.redraw_chart()

    def save_to_csv(self):
        # Do NOT call sync_from_entries_and_redraw() here — live edits already update self.records,
        # and skipping re-parse preserves exact decimal precision and prevents double-counting PY Surplus.
        target_dir = getattr(self.app, 'last_import_dir', os.getcwd()) or os.getcwd()
        csv_path = os.path.join(target_dir, "monthly_financials.csv")

        try:
            with open(csv_path, mode='w', newline='', encoding='utf-8-sig') as f:
                fieldnames = ['RowType', 'Month', 'Category', 'Subcategory', 'Amount', 'IsForecast', 'TitleText']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerow({'RowType': 'Meta', 'Month': '', 'Category': 'Title', 'Subcategory': '',
                                 'Amount': '', 'IsForecast': '', 'TitleText': self.title_var.get()})
                for rec in self.records:
                    writer.writerow({
                        'RowType': 'MonthSummary', 'Month': rec['month'], 'Category': '', 'Subcategory': '',
                        'Amount': f"{rec['income']}|{rec['expense']}|{rec['other_income']}",
                        'IsForecast': '1' if rec['is_forecast'] else '0', 'TitleText': ''
                    })
                    for bucket_name, b_key in [('IncCat', 'inc_cats'), ('ExpCat', 'exp_cats'), ('OtherCat', 'other_cats')]:
                        for cat_lbl, sub_list in rec.get(b_key, {}).items():
                            for s_lbl, s_val in sub_list:
                                writer.writerow({
                                    'RowType': bucket_name, 'Month': rec['month'], 'Category': cat_lbl,
                                    'Subcategory': s_lbl, 'Amount': float(s_val),
                                    'IsForecast': '1' if rec['is_forecast'] else '0', 'TitleText': ''
                                })
            self.btn_save_csv.config(text="Update CSV File")
            messagebox.showinfo("Saved", f"Monthly financials saved to:\n\n{csv_path}")
        except Exception as e:
            messagebox.showerror("Save Error", f"Could not write monthly_financials.csv:\n{str(e)}")

    def load_from_csv(self, csv_path):
        try:
            rec_map, ordered_mos = {}, []
            with open(csv_path, mode='r', newline='', encoding='utf-8-sig') as f:
                for row in csv.DictReader(f):
                    rtype = row.get('RowType', '').strip()
                    if rtype == 'Meta' and row.get('Category') == 'Title':
                        self.title_var.set(row.get('TitleText', '2026 Monthly Financial Results'))
                    elif rtype == 'MonthSummary':
                        mo = row['Month'].strip()
                        parts = row['Amount'].split('|')
                        rec_map[mo] = {
                            'month': mo,
                            'income': float(parts[0]) if len(parts) > 0 else 0.0,
                            'expense': float(parts[1]) if len(parts) > 1 else 0.0,
                            'other_income': float(parts[2]) if len(parts) > 2 else 0.0,
                            'is_forecast': row.get('IsForecast', '0') == '1',
                            'inc_cats': {}, 'exp_cats': {}, 'other_cats': {}
                        }
                        ordered_mos.append(mo)
                    elif rtype in ('IncCat', 'ExpCat', 'OtherCat'):
                        mo = row['Month'].strip()
                        if mo in rec_map:
                            b_key = 'inc_cats' if rtype == 'IncCat' else ('exp_cats' if rtype == 'ExpCat' else 'other_cats')
                            rec_map[mo][b_key].setdefault(row['Category'], []).append((row['Subcategory'], float(row['Amount'] or 0.0)))
            if ordered_mos:
                self.records = [rec_map[m] for m in ordered_mos]
        except Exception as e:
            messagebox.showerror("Load Error", f"Could not load monthly_financials.csv:\n{str(e)}")
            self.seed_from_active_budget()

    def get_active_series(self):
        include_surplus = self.include_surplus_var.get()
        show_forecast = self.show_forecast_var.get()
        is_cumulative = self.chart_mode_var.get() == "Cumulative"

        active_recs = [r for r in self.records if show_forecast or not r["is_forecast"]]
        if not active_recs:
            active_recs = self.records[:1]

        months = [r["month"] for r in active_recs]
        inc_vals, exp_vals, is_fc_flags = [], [], []
        run_inc, run_exp = 0.0, 0.0

        for r in active_recs:
            m_inc = r["income"] + (r["other_income"] if include_surplus else 0.0)
            m_exp = r["expense"]
            if is_cumulative:
                run_inc += m_inc
                run_exp += m_exp
                inc_vals.append(run_inc)
                exp_vals.append(run_exp)
            else:
                inc_vals.append(m_inc)
                exp_vals.append(m_exp)
            is_fc_flags.append(r["is_forecast"])

        tot_i = sum(r["income"] + (r["other_income"] if include_surplus else 0.0) for r in active_recs)
        tot_e = sum(r["expense"] for r in active_recs)
        net = tot_i - tot_e
        self.tot_inc_lbl.config(text=f"Total Income: ${tot_i:,.0f}")
        self.tot_exp_lbl.config(text=f"Total Expenses: ${tot_e:,.0f}")
        # Use white when balanced within $1.00 so tiny rounding fractions never flash red
        if abs(net) < 1.0:
            net_txt = "Net Position: $0"
            net_fg = "#ffffff"
        elif net > 0:
            net_txt = f"Net Position: +${net:,.0f}"
            net_fg = "#00FF66"
        else:
            net_txt = f"Net Position: -${abs(net):,.0f}"
            net_fg = "#FF3300"

        self.net_pos_lbl.config(text=net_txt, fg=net_fg)
        return active_recs, months, np.array(inc_vals), np.array(exp_vals), is_fc_flags

    def redraw_chart(self, theme="dark"):
        if not self.initialized or not self.records:
            return
        _, months, inc_arr, exp_arr, is_fc_flags = self.get_active_series()
        is_cumulative = self.chart_mode_var.get() == "Cumulative"
        mode_tag = "Cumulative YTD" if is_cumulative else "Monthly"
        surplus_tag = "Incl. PY Surplus" if self.include_surplus_var.get() else "Operating Only"

        # Derive average monthly budget from Total Expenses on the active Budget page
        budget_tot_exp = float(getattr(self.app.budget_view, 'total_expenses', 0.0))
        monthly_budget = budget_tot_exp / 12.0

        self.ax, self.hover_vline, self.hover_dot = create_monthly_line_chart(
            self.fig, months, inc_arr, exp_arr, is_fc_flags,
            self.title_var.get(), mode_tag, surplus_tag,
            theme=theme, monthly_budget=monthly_budget, is_cumulative=is_cumulative
        )
        if theme == "dark":
            self.canvas.draw()

    def resolve_hovered_target(self, event):
        if not event.inaxes or not self.records or event.xdata is None or event.ydata is None:
            return None
        active_recs, _, inc_arr, exp_arr, _ = self.get_active_series()
        idx = int(round(event.xdata))
        if idx < 0 or idx >= len(active_recs):
            return None

        inc_y, exp_y, cursor_y = inc_arr[idx], exp_arr[idx], event.ydata
        dist_inc, dist_exp = abs(cursor_y - inc_y), abs(cursor_y - exp_y)

        # Tie-breaker: if lines are identical/equidistant, above = Income, below = Expense
        if abs(inc_y - exp_y) < 1.0 or abs(dist_inc - dist_exp) < 1.0:
            line_type = "Income" if cursor_y >= inc_y else "Expense"
        else:
            line_type = "Income" if dist_inc < dist_exp else "Expense"

        return idx, active_recs[idx], line_type, (inc_y if line_type == "Income" else exp_y)

    def get_aggregated_categories(self, target_idx, line_type):
        """Returns ordered list of category dicts for target month or Cumulative YTD."""
        profile = self.view_profile_var.get()
        is_cumulative = self.chart_mode_var.get() == "Cumulative"
        active_recs, _, _, _, _ = self.get_active_series()
        recs_to_sum = active_recs[:target_idx + 1] if is_cumulative else [active_recs[target_idx]]

        ordered_cats = []
        cat_map = {}
        total_val = 0.0

        for r in recs_to_sum:
            if line_type == "Income":
                buckets = [r.get("inc_cats", {})] + ([r.get("other_cats", {})] if self.include_surplus_var.get() else [])
                total_val += r["income"] + (r["other_income"] if self.include_surplus_var.get() else 0.0)
            else:
                buckets = [r.get("exp_cats", {})]
                total_val += r["expense"]

            for bucket in buckets:
                for cat_key, sub_items in bucket.items():
                    if cat_key not in cat_map:
                        is_sens = any(tok in cat_key.upper() for tok in ["SALARY", "BENEFIT", "CLERGY", "LAY MIN", "PASTOR", "DEACON"])
                        cat_obj = {"raw_key": cat_key, "label": self.clean_label(cat_key), "total": 0.0, "subs": {}, "locked": (profile == "Public Mode (Hide Salaries)" and is_sens)}
                        cat_map[cat_key] = cat_obj
                        ordered_cats.append(cat_obj)
                    c_obj = cat_map[cat_key]
                    for s_lbl, s_val in sub_items:
                        c_obj["total"] += s_val
                        c_obj["subs"][s_lbl] = c_obj["subs"].get(s_lbl, 0.0) + s_val

        tot_label = f"YTD {line_type} thru {active_recs[target_idx]['month']}" if is_cumulative else f"Total {line_type}"
        return ordered_cats, tot_label, total_val

    def handle_hover(self, event):
        if self.modal_active or self.tooltip_frozen:
            return
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None
        if self.view_profile_var.get() == "Silence All Tooltips":
            return

        hit = self.resolve_hovered_target(event)
        if not hit:
            if self.hover_vline and self.hover_vline.get_visible():
                self.hover_vline.set_visible(False)
                self.hover_dot.set_visible(False)
                self.canvas.draw_idle()
            return

        idx, rec, line_type, target_y = hit
        border_color = '#00F0FF' if line_type == "Income" else '#FF007F'

        if self.hover_vline and self.hover_dot:
            self.hover_vline.set_xdata([idx, idx])
            self.hover_vline.set_visible(True)
            self.hover_dot.set_data([idx], [target_y])
            self.hover_dot.set_markeredgecolor(border_color)
            self.hover_dot.set_visible(True)
            self.canvas.draw_idle()

        cats, tot_label, total_val = self.get_aggregated_categories(idx, line_type)
        rows = [(c["label"], c["total"]) for c in cats] + [(tot_label, total_val)]
        max_lbl_len = max(len(r[0]) for r in rows)
        max_val_len = max(len(f"${r[1]:,.0f}") for r in rows)
        total_w = max_lbl_len + max_val_len + 8
        master_grid = (" ." * ((total_w // 2) + 2))[:total_w]

        lines = [f"{lbl} {master_grid[len(lbl)+1:total_w-len(f'${val:,.0f}')-1]} ${val:,.0f}" for lbl, val in rows]
        tag_suffix = " (Forecast)" if rec["is_forecast"] else " (Actual)"
        scope_prefix = "YTD thru " if self.chart_mode_var.get() == "Cumulative" else ""
        body_txt = "\n".join(lines)

        self.tooltip = tk.Toplevel(self.app.root)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.configure(bg='#e0e0e0', highlightbackground=border_color, highlightthickness=2, bd=0)
        tk.Label(self.tooltip, text=f"--- {scope_prefix}{rec['month']} {line_type}{tag_suffix} ---", bg='#e0e0e0', fg='#1a1a1a', font=('Arial', 10, 'bold'), padx=10).pack(fill="x", pady=(8, 4))
        tk.Label(self.tooltip, text=body_txt, bg='#e0e0e0', fg='#1a1a1a', font=('Consolas', 9, 'bold'), justify="left", padx=10).pack(fill="x", pady=(0, 4))
        self.tooltip_hint_lbl = tk.Label(self.tooltip, text="[Left-Click to Pin | Right-Click to Zoom]", bg='#e0e0e0', fg='#444444', font=('Arial', 8, 'italic'), padx=10)
        self.tooltip_hint_lbl.pack(fill="x", pady=(0, 8))

        # Allow clicking directly on the pinned tooltip card itself to unpin it
        for w in self.tooltip.winfo_children() + [self.tooltip]:
            w.bind("<Button-1>", lambda e: self.toggle_tooltip_freeze())

        self.tooltip.update_idletasks()
        tip_w, tip_h = self.tooltip.winfo_reqwidth(), self.tooltip.winfo_reqheight()
        px, py = self.app.root.winfo_pointerx(), self.app.root.winfo_pointery()
        sw, sh = self.app.root.winfo_screenwidth(), self.app.root.winfo_screenheight()
        self.tooltip.wm_geometry(f"+{px + (15 if px + 15 + tip_w <= sw else -(tip_w + 15))}+{py + (15 if py + 15 + tip_h <= sh else -(tip_h + 15))}")

    def toggle_tooltip_freeze(self):
        if self.tooltip_frozen:
            self.tooltip_frozen = False
            if self.tooltip:
                self.tooltip.destroy()
                self.tooltip = None
        elif self.tooltip:
            self.tooltip_frozen = True
            if self.tooltip_hint_lbl and self.tooltip_hint_lbl.winfo_exists():
                self.tooltip_hint_lbl.config(text="[Pinned — Left-Click to Unpin]", fg='#006688')

    def handle_click(self, event):
        if self.modal_active or self.view_profile_var.get() == "Silence All Tooltips":
            return
        if event.button == 1:
            self.toggle_tooltip_freeze()
        elif event.button == 3:
            if self.tooltip_frozen:
                self.tooltip_frozen = False
            hit = self.resolve_hovered_target(event)
            if hit:
                idx, rec, line_type, _ = hit
                self.open_sanctuary_zoom(idx, rec, line_type)

    def open_sanctuary_zoom(self, idx, rec, line_type):
        if self.modal_active:
            return
        self.modal_active = True
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

        border_color = '#00F0FF' if line_type == "Income" else '#FF007F'
        cats, tot_label, total_val = self.get_aggregated_categories(idx, line_type)
        expanded_keys = set()

        scope_prefix = "YTD THRU " if self.chart_mode_var.get() == "Cumulative" else ""
        tag_suffix = "(FORECAST)" if rec["is_forecast"] else "(ACTUAL)"
        modal_title = f" {scope_prefix}{rec['month'].upper()} {line_type.upper()} {tag_suffix} "

        self.zoom_modal = tk.Toplevel(self.app.root)
        self.zoom_modal.configure(bg='#161616', highlightbackground=border_color, highlightthickness=2, bd=0)
        self.zoom_modal.wm_overrideredirect(True)

        tk.Frame(self.zoom_modal, bg='#161616', height=18).pack(side="top")
        title_lbl = tk.Label(self.zoom_modal, text=modal_title, bg='#161616', fg='white', font=('Arial', 16, 'bold'))
        title_lbl.pack(side="top", fill="x", padx=30, pady=4)
        tk.Frame(self.zoom_modal, height=2, bg=border_color).pack(side="top", fill="x", padx=35, pady=(2, 8))

        def close_modal(*args):
            if self.zoom_modal:
                self.zoom_modal.grab_release()
                self.zoom_modal.destroy()
                self.zoom_modal = None
            self.modal_active = False

        footer = tk.Frame(self.zoom_modal, bg='#161616')
        footer.pack(side="bottom", fill="x", pady=(6, 16))
        hint_lbl = tk.Label(footer, text="Click Category to Expand/Collapse  |  Wheel or ↑/↓ to Resize Text  |  ESC to Close", bg='#161616', fg='#777777', font=('Arial', 9, 'italic'))
        hint_lbl.pack(side="top", pady=(0, 8))
        tk.Button(footer, text="[ Close Ledger View ]", command=close_modal, bg='#161616', fg='#aaaaaa', font=('Arial', 12, 'bold'), bd=0, cursor="hand2").pack(side="top")

        vp = tk.Frame(self.zoom_modal, bg='#161616')
        vp.pack(side="top", fill="both", expand=True, padx=25, pady=5)
        z_can = tk.Canvas(vp, bg='#161616', bd=0, highlightthickness=0)
        h_sb, v_sb = tk.Scrollbar(vp, orient="horizontal", command=z_can.xview), tk.Scrollbar(vp, orient="vertical", command=z_can.yview)
        z_can.configure(xscrollcommand=h_sb.set, yscrollcommand=v_sb.set)
        inner_f = tk.Frame(z_canvas := z_can, bg='#161616')
        win_id = z_can.create_window((0, 0), window=inner_f, anchor="nw")

        def sync_vp(e=None):
            inner_f.update_idletasks(); z_can.update_idletasks()
            z_can.configure(scrollregion=z_can.bbox("all"))
            cw, ch = z_can.winfo_width(), z_can.winfo_height()
            if cw <= 1 or ch <= 1: return
            rw, rh = inner_f.winfo_reqwidth(), inner_f.winfo_reqheight()
            h_sb.pack(side="bottom", fill="x", before=z_can) if rw > cw + 4 else h_sb.pack_forget()
            v_sb.pack(side="right", fill="y", before=z_can) if rh > ch + 4 else v_sb.pack_forget()
            z_can.coords(win_id, max(0, (cw - rw) // 2) if rw <= cw + 4 else 0, 0)

        def resize_modal():
            self.zoom_modal.update_idletasks(); inner_f.update_idletasks()
            aw, ah, ax, ay = self.app.root.winfo_width(), self.app.root.winfo_height(), self.app.root.winfo_x(), self.app.root.winfo_y()
            fw = min(max(inner_f.winfo_reqwidth() + 70, title_lbl.winfo_reqwidth() + 80, hint_lbl.winfo_reqwidth() + 60, 360), max(340, aw - 40))
            fh = min(18 + title_lbl.winfo_reqheight() + 20 + inner_f.winfo_reqheight() + footer.winfo_reqheight() + 35, max(240, ah - 40))
            self.zoom_modal.geometry(f"{fw}x{fh}+{ax + (aw - fw) // 2}+{ay + (ah - fh) // 2}")
            self.zoom_modal.update_idletasks(); sync_vp()

        def render_accordion_rows():
            for w in inner_f.winfo_children():
                w.destroy()

            # Build display rows list: (label_str, val_float, is_cat_header, cat_raw_key, clickable)
            display_rows = []
            for c in cats:
                has_subs = len(c["subs"]) > 1 or (len(c["subs"]) == 1 and list(c["subs"].keys())[0] != c["raw_key"])
                is_exp = c["raw_key"] in expanded_keys
                prefix = "🔒 " if c["locked"] else (("▼ " if is_exp else "▶ ") if has_subs else "  ")
                display_rows.append((f"{prefix}{c['label']}", c["total"], True, c["raw_key"], has_subs and not c["locked"]))
                if is_exp and not c["locked"]:
                    for s_raw, s_val in c["subs"].items():
                        display_rows.append((f"    • {self.clean_label(s_raw)}", s_val, False, None, False))

            display_rows.append((f"  {tot_label}", total_val, True, None, False))
            max_l = max(len(r[0]) for r in display_rows)
            max_v = max(len(f"${r[1]:,.0f}") for r in display_rows)
            grid_w = max_l + max_v + 10
            m_grid = (" ." * ((grid_w // 2) + 2))[:grid_w]

            for r_lbl, r_val, is_hdr, c_key, can_click in display_rows:
                v_str = f"${r_val:,.0f}"
                dots = m_grid[len(r_lbl)+1:grid_w-len(v_str)-1]
                line_txt = f" {r_lbl} {dots} {v_str} "
                fg_c = "white" if is_hdr else "#bbbbbb"
                lbl_w = tk.Label(inner_f, text=line_txt, bg='#161616', fg=fg_c,
                                 font=('Consolas', self.zoom_font_size, 'bold' if is_hdr else 'normal'),
                                 anchor="w", cursor="hand2" if can_click else "")
                lbl_w.pack(fill="x", padx=6, pady=1)
                if can_click:
                    lbl_w.bind("<Enter>", lambda e, w=lbl_w: w.config(bg='#242424', fg=border_color))
                    lbl_w.bind("<Leave>", lambda e, w=lbl_w: w.config(bg='#161616', fg='white'))
                    lbl_w.bind("<Button-1>", lambda e, k=c_key: toggle_cat(k))

            resize_modal()

        def toggle_cat(c_key):
            if c_key in expanded_keys:
                expanded_keys.remove(c_key)
            else:
                expanded_keys.add(c_key)
            render_accordion_rows()

        def step_font(d):
            self.zoom_font_size = min(32, max(10, self.zoom_font_size + d))
            render_accordion_rows()

        z_can.pack(side="left", fill="both", expand=True)
        z_can.bind("<Configure>", sync_vp); inner_f.bind("<Configure>", sync_vp)
        self.zoom_modal.bind("<MouseWheel>", lambda e: step_font(1 if e.delta > 0 else -1))
        self.zoom_modal.bind("<Button-4>", lambda e: step_font(1)); self.zoom_modal.bind("<Button-5>", lambda e: step_font(-1))
        self.zoom_modal.bind("<Up>", lambda e: step_font(1)); self.zoom_modal.bind("<Down>", lambda e: step_font(-1))
        self.zoom_modal.bind("<Escape>", close_modal)

        render_accordion_rows()
        self.zoom_modal.transient(self.app.root); self.zoom_modal.grab_set(); self.zoom_modal.focus_force()

    def prompt_and_export_chart(self):
        dlg = tk.Toplevel(self.app.root)
        dlg.title("Export Chart Background")
        dlg.configure(bg='#1c1c1c', highlightbackground='#00FF66', highlightthickness=1)
        dlg.geometry(f"360x210+{self.app.root.winfo_x() + (self.app.root.winfo_width()//2) - 180}+{self.app.root.winfo_y() + (self.app.root.winfo_height()//2) - 105}")
        dlg.transient(self.app.root); dlg.grab_set()
        tk.Label(dlg, text="CHOOSE EXPORT BACKGROUND STYLE", bg='#1c1c1c', fg='#00FF66', font=('Arial', 10, 'bold')).pack(pady=(15, 6))
        chosen = {"theme": None}
        def pick(t): chosen["theme"] = t; dlg.grab_release(); dlg.destroy()
        for lbl, val, bg, fg in [("Dark Theme (Black)", "dark", "#111111", "#00F0FF"), ("White Background (Newsletter / Print)", "white", "#FFFFFF", "#1a1a1a"), ("Transparent Background", "transparent", "#2a2a2a", "white")]:
            tk.Button(dlg, text=lbl, command=lambda v=val: pick(v), bg=bg, fg=fg, font=('Arial', 9, 'bold'), pady=5, cursor="hand2").pack(fill="x", padx=25, pady=3)
        dlg.bind("<Escape>", lambda e: pick(None)); self.app.root.wait_window(dlg)
        if not chosen["theme"]: return
        out_path = os.path.join(os.path.expanduser("~"), "Desktop", "monthly_financials_chart.png")
        try:
            self.redraw_chart(theme=chosen["theme"])
            self.fig.savefig(out_path, dpi=200, transparent=(chosen["theme"] == "transparent"), facecolor=self.fig.get_facecolor())
            self.redraw_chart(theme="dark")
            messagebox.showinfo("Exported", f"Chart saved to Desktop:\n\n{out_path}")
        except Exception as e:
            self.redraw_chart(theme="dark"); messagebox.showerror("Export Error", str(e))
