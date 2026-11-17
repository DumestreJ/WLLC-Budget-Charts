import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import openpyxl
from utility_methods import *  # Imports cleanly from your support module


def parse_account_label(raw_text):
    """Splits leading account numbers separated by a space (e.g. '4005 Pledged Giving')."""
    cleaned = raw_text.strip()
    match = re.match(r'^([\d\-\.]+)\s+(.*)$', cleaned)
    if match:
        return match.group(1), match.group(2).strip()
    return "", cleaned


def get_leading_spaces(val):
    if not isinstance(val, str):
        return 0
    return len(val) - len(val.lstrip(' '))


def import_financial_spreadsheet(monthly_view):
    """Opens unified Financial Statements import wizard: browse for the Excel workbook,
    pick Actuals and Forecast Budget tabs, and populate the Monthly Financials view.
    """
    desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
    default_dir = desktop_dir if os.path.exists(desktop_dir) else os.getcwd()

    dlg = tk.Toplevel(monthly_view.app.root)
    dlg.title("Import Financial Statements")
    dlg.configure(bg='#1c1c1c', highlightbackground='#00F0FF', highlightthickness=1)
    dlg.geometry("500x305")
    dlg.transient(monthly_view.app.root)
    dlg.grab_set()

    mx = monthly_view.app.root.winfo_x() + (monthly_view.app.root.winfo_width() // 2) - 250
    my = monthly_view.app.root.winfo_y() + (monthly_view.app.root.winfo_height() // 2) - 152
    dlg.geometry(f"+{max(20, mx)}+{max(20, my)}")

    tk.Label(dlg, text="IMPORT FINANCIAL STATEMENTS", bg='#1c1c1c', fg='#00F0FF',
             font=('Arial', 10, 'bold')).pack(pady=(14, 10))

    # 1. Excel File Browser Row
    frm_file = tk.Frame(dlg, bg='#1c1c1c')
    frm_file.pack(fill="x", padx=25, pady=6)
    tk.Label(frm_file, text="Excel File:", bg='#1c1c1c', fg='white',
             font=('Arial', 9, 'bold'), width=18, anchor="w").pack(side="left")

    file_display_var = tk.StringVar(value="No file selected")
    lbl_file = tk.Label(frm_file, textvariable=file_display_var, bg='#141414', fg='#aaaaaa',
                        font=('Arial', 8), anchor="w", padx=8, pady=4,
                        highlightbackground='#333333', highlightthickness=1)
    lbl_file.pack(side="left", fill="x", expand=True, padx=(0, 8))

    wb = None
    actual_var = tk.StringVar(value="Select file first...")
    budget_var = tk.StringVar(value="None (Use Budget Tab Average)")

    def browse_excel_file():
        nonlocal wb
        initial_dir = getattr(monthly_view.app, 'last_import_dir', default_dir) or default_dir
        picked_path = filedialog.askopenfilename(
            parent=dlg,
            title="Select Financial Statements Excel Workbook",
            initialdir=initial_dir,
            filetypes=[("Excel Files", "*.xlsx *.xlsm"), ("All Files", "*.*")]
        )
        if not picked_path:
            return
        monthly_view.app.last_import_dir = os.path.dirname(picked_path)
        try:
            loaded_wb = openpyxl.load_workbook(picked_path, data_only=True)
            s_names = loaded_wb.sheetnames
            if not s_names:
                messagebox.showerror("Import Error", "No sheets found in the selected workbook.", parent=dlg)
                return
            wb = loaded_wb
            file_display_var.set(os.path.basename(picked_path))
            lbl_file.config(fg='#00F0FF')

            def_act = s_names
            def_bud = "None (Use Budget Tab Average)"
            for name in s_names:
                low = name.lower()
                if "budget" in low and ("p&l" in low or "actual" in low or "operating" in low):
                    def_bud = name
                elif ("p&l" in low or "operating" in low) and "budget" not in low:
                    def_act = name

            cb_actual.config(values=s_names, state="readonly")
            actual_var.set(def_act)
            cb_budget.config(values=["None (Use Budget Tab Average)"] + s_names, state="readonly")
            budget_var.set(def_bud)
        except Exception as err:
            wb = None
            messagebox.showerror("Import Error", f"Could not open Excel workbook:\n{str(err)}", parent=dlg)

    tk.Button(frm_file, text="Browse...", command=browse_excel_file,
              bg='#2a2a2a', fg='#00F0FF', font=('Arial', 8, 'bold'),
              padx=10, pady=4, bd=1, relief="solid", cursor="hand2").pack(side="right")
    # 2. Actuals & Forecast Budget Tab Selectors
    frm1 = tk.Frame(dlg, bg='#1c1c1c')
    frm1.pack(fill="x", padx=25, pady=6)
    tk.Label(frm1, text="Actuals Tab:", bg='#1c1c1c', fg='white',
             font=('Arial', 9, 'bold'), width=18, anchor="w").pack(side="left")
    cb_actual = ttk.Combobox(frm1, textvariable=actual_var, values=["Select file first..."],
                             state="disabled", width=28)
    cb_actual.pack(side="right", fill="x", expand=True)

    frm2 = tk.Frame(dlg, bg='#1c1c1c')
    frm2.pack(fill="x", padx=25, pady=6)
    tk.Label(frm2, text="Forecast Budget Tab:", bg='#1c1c1c', fg='white',
             font=('Arial', 9, 'bold'), width=18, anchor="w").pack(side="left")
    cb_budget = ttk.Combobox(frm2, textvariable=budget_var, values=["None (Use Budget Tab Average)"],
                             state="disabled", width=28)
    cb_budget.pack(side="right", fill="x", expand=True)

    selection_result = {"confirmed": False}

    def on_confirm():
        if wb is None:
            messagebox.showwarning("File Required", "Please click 'Browse...' to select an Excel workbook first.", parent=dlg)
            return
        if actual_var.get() == "Select file first...":
            messagebox.showwarning("Tab Required", "Please choose an Actuals worksheet tab.", parent=dlg)
            return
        selection_result["confirmed"] = True
        dlg.grab_release()
        dlg.destroy()

    def on_cancel():
        dlg.grab_release()
        dlg.destroy()

    FINANCIAL_HELP_TEXT = (
        "HOW ACTUALS & FORECAST TABS ARE READ:\n\n"
        "1. Select Excel Workbook First:\n"
        "   • Click 'Browse...' to pick your QuickBooks Financial Statements Excel file (.xlsx or .xlsm).\n\n"
        "2. Actuals Tab (Flexible Layout):\n"
        "   • Works with EITHER a standard monthly P&L tab ('Jan 26'–'Dec 26') OR a 'Budget vs. Actuals' tab where each month spans 'Actual | Budget | Difference' sub-columns.\n"
        "   • Trailing future months with $0 Actual activity (such as Oct–Dec in a YTD September report) are automatically trimmed and filled as Forecast months.\n\n"
        "3. Forecast Budget Tab (Remaining Months):\n"
        "   • Any month after your last Actual month is populated automatically as Forecast (dotted lines).\n"
        "   • Select a monthly Budget / 'Budget vs. Actuals' tab to pull month-by-month budgeted figures, OR choose 'None (Use Budget Tab Average)' to spread your active Budget page totals evenly by 12."
    )

    btn_row = tk.Frame(dlg, bg='#1c1c1c')
    btn_row.pack(side="bottom", pady=18)
    tk.Button(btn_row, text="? Info",
              command=lambda: show_import_help(dlg, "Monthly Financials Import Guide", FINANCIAL_HELP_TEXT),
              bg='#2a2a2a', fg='#00F0FF', font=('Arial', 9, 'bold'),
              padx=12, pady=5, bd=1, relief="solid", cursor="hand2").pack(side="left", padx=(0, 10))
    tk.Button(btn_row, text="Cancel", command=on_cancel, bg='#2a2a2a', fg='white',
              font=('Arial', 9, 'bold'), padx=14, pady=5, bd=0, cursor="hand2").pack(side="left", padx=8)
    tk.Button(btn_row, text="Import Selected Tabs", command=on_confirm, bg='#00F0FF', fg='black',
              font=('Arial', 9, 'bold'), padx=14, pady=5, bd=0, cursor="hand2").pack(side="left", padx=8)

    dlg.bind("<Escape>", lambda e: on_cancel())
    monthly_view.app.root.wait_window(dlg)

    if not selection_result["confirmed"]:
        return

    try:
        actuals_data = parse_actuals_sheet(wb[actual_var.get()])
        budget_tab_name = budget_var.get()
        excel_budget_data = None
        if budget_tab_name != "None (Use Budget Tab Average)" and budget_tab_name in wb.sheetnames:
            excel_budget_data = parse_budget_vs_actual_sheet(wb[budget_tab_name])

        yr_m = re.search(r'\b(20\d{2})\b', f"{file_display_var.get()} {actual_var.get()}")
        imp_yr = yr_m.group(1) if yr_m else None
        monthly_view.apply_imported_financials(actuals_data, excel_budget_data, imported_year=imp_yr)
        if hasattr(monthly_view, 'data_source_var'):
            monthly_view.data_source_var.set(f"Source: {file_display_var.get()}")
    except Exception as e:
        messagebox.showerror("Parse Error", f"Failed to parse financial statement layout:\n{str(e)}")

def _parse_indented_columns(ws, col_pairs, start_row):
    """Shared indentation-aware parser for QuickBooks P&L sheets."""
    months_data = {
        m_name: {
            "income": 0.0, "expense": 0.0, "other_income": 0.0,
            "inc_cats": {}, "exp_cats": {}, "other_cats": {}
        }
        for _, m_name in col_pairs
    }

    current_section = None
    current_main_cat = None
    max_col = max(c for c, _ in col_pairs) + 1

    for r_idx in range(start_row, ws.max_row + 1):
        row_vals = [ws.cell(row=r_idx, column=c + 1).value for c in range(max_col)]
        raw_a = row_vals[0]
        if raw_a is None or not str(raw_a).strip():
            continue

        str_a = str(raw_a)
        indent = get_leading_spaces(str_a)
        clean_text = str_a.strip()
        low_text = clean_text.lower()

        if low_text.startswith("page ") or "accrual basis" in low_text:
            continue

        if indent == 0:
            if low_text == "income":
                current_section, current_main_cat = "Income", None
                continue
            elif low_text == "expenses":
                current_section, current_main_cat = "Expenses", None
                continue
            elif low_text == "other income":
                current_section, current_main_cat = "Other Income", None
                continue
            elif low_text == "total income":
                for c_idx, m_name in col_pairs:
                    months_data[m_name]["income"] = float(row_vals[c_idx] or 0.0)
                current_section = None
                continue
            elif low_text == "total expenses":
                for c_idx, m_name in col_pairs:
                    months_data[m_name]["expense"] = float(row_vals[c_idx] or 0.0)
                current_section = None
                continue
            elif low_text == "total other income":
                for c_idx, m_name in col_pairs:
                    months_data[m_name]["other_income"] = float(row_vals[c_idx] or 0.0)
                current_section = None
                continue
            elif low_text in ("gross profit", "net operating income", "net other income", "net income"):
                current_section = None
                continue

        if not current_section:
            continue

        if low_text.startswith("total "):
            if indent <= 3:
                current_main_cat = None
            continue

        cat_bucket = "inc_cats" if current_section == "Income" else ("exp_cats" if current_section == "Expenses" else "other_cats")
        if indent <= 3:
            current_main_cat = clean_text
            for c_idx, m_name in col_pairs:
                val = float(row_vals[c_idx] or 0.0)
                if val != 0.0:
                    months_data[m_name][cat_bucket].setdefault(current_main_cat, []).append((clean_text, val))
        else:
            parent = current_main_cat or "General"
            for c_idx, m_name in col_pairs:
                val = float(row_vals[c_idx] or 0.0)
                if val != 0.0:
                    months_data[m_name][cat_bucket].setdefault(parent, []).append((clean_text, val))

    return {"ordered_months": [m_name for _, m_name in col_pairs], "months": months_data}


def parse_actuals_sheet(ws):
    """Detects monthly columns (Jan..Dec) in QuickBooks Actuals tab and parses rows."""
    month_map = {"jan": "Jan", "feb": "Feb", "mar": "Mar", "apr": "Apr", "may": "May", "jun": "Jun",
                 "jul": "Jul", "aug": "Aug", "sep": "Sep", "oct": "Oct", "nov": "Nov", "dec": "Dec"}
    for r_idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
        found = []
        for c_idx, cell_val in enumerate(row):
            if c_idx == 0 or cell_val is None:
                continue
            s_val = str(cell_val).strip().lower()
            if "total" in s_val:
                break
            for prefix, m_short in month_map.items():
                if s_val.startswith(prefix):
                    found.append((c_idx, m_short))
                    break
        if found:
            parsed = _parse_indented_columns(ws, found, r_idx + 1)
            # Remove trailing un-occurred future months where operating Income and Expense are both $0
            while parsed.get("ordered_months"):
                last_m = parsed["ordered_months"][-1]
                rec = parsed["months"].get(last_m, {})
                if abs(rec.get("income", 0.0)) < 0.01 and abs(rec.get("expense", 0.0)) < 0.01:
                    parsed["ordered_months"].pop()
                    parsed["months"].pop(last_m, None)
                else:
                    break
            return parsed
    raise ValueError("Could not detect monthly columns (e.g., Jan 2026) in the selected Actuals tab.")


def parse_budget_vs_actual_sheet(ws):
    """Detects center 'Budget' columns under each month in QuickBooks Budget vs Actual tab."""
    month_map = {"jan": "Jan", "feb": "Feb", "mar": "Mar", "apr": "Apr", "may": "May", "jun": "Jun",
                 "jul": "Jul", "aug": "Aug", "sep": "Sep", "oct": "Oct", "nov": "Nov", "dec": "Dec"}
    for r_idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
        found = []
        for c_idx, val in enumerate(row):
            if c_idx == 0 or val is None:
                continue
            s_val = str(val).strip().lower()
            if "total" in s_val:
                break
            for prefix, m_short in month_map.items():
                if s_val.startswith(prefix):
                    found.append((c_idx, m_short))
                    break
        if found:
            sub_row = [ws.cell(row=r_idx + 1, column=c + 1).value for c in range(ws.max_column)]
            budget_cols = []
            for start_c, m_short in found:
                chosen_c = start_c + 1
                for offset in range(3):
                    if start_c + offset < len(sub_row) and sub_row[start_c + offset]:
                        if str(sub_row[start_c + offset]).strip().lower() == "budget":
                            chosen_c = start_c + offset
                            break
                budget_cols.append((chosen_c, m_short))
            return _parse_indented_columns(ws, budget_cols, r_idx + 2)
    return None
