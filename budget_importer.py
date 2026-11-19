import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
import re
from monthly_importer import parse_budget_vs_actual_sheet
from utility_methods import *  # Imports cleanly from your support module


def _discover_sheet_columns(ws):
    """Finds the table header row (containing 'Budget Line' or 'Budget') and reads its column names."""
    header_row = None
    for row in ws.iter_rows(max_row=15, values_only=True):
        row_upper = [str(c).strip().upper() for c in row if c is not None]
        if any("BUDGET LINE" in txt or "YTD" in txt for txt in row_upper):
            header_row = row
            break
    if header_row is None:
        for row in ws.iter_rows(max_row=15, values_only=True):
            if sum(1 for c in row[6:] if c is not None and str(c).strip()) >= 3:
                header_row = row
                break

    col_labels = {}
    if header_row:
        for idx, cell in enumerate(header_row):
            if idx < 6 or cell is None:
                continue
            txt = str(cell).strip().replace("\n", " ")
            if txt:
                col_labels[idx] = f"Col {get_column_letter(idx + 1)} — {txt[:30]}"

    max_col = max(ws.max_column or 14, 14)
    options = []
    for idx in range(6, min(max_col, 26)):
        options.append((idx, col_labels.get(idx, f"Col {get_column_letter(idx + 1)}")))
    return options


def _extract_annual_from_monthly_bva(ws):
    """Extracts a full 12-month annual budget from a 'Budget vs. Actuals' sheet's monthly Budget columns.
    Extrapolates missing or $0 future months using the per-category monthly average and returns:
    (subcategories_dict, total_income, total_expenses, status_note_or_None).
    """
    parsed = parse_budget_vs_actual_sheet(ws)
    if not parsed or not parsed.get("ordered_months"):
        raise ValueError("Could not detect monthly 'Budget' columns in the selected worksheet tab.")

    active_months = []
    for m_name in parsed["ordered_months"]:
        rec = parsed["months"].get(m_name, {})
        tot_inc = rec.get("income", 0.0) + rec.get("other_income", 0.0)
        tot_exp = rec.get("expense", 0.0)
        if abs(tot_inc) >= 0.01 or abs(tot_exp) >= 0.01:
            active_months.append(m_name)

    n_avail = len(active_months)
    if n_avail == 0:
        raise ValueError("No non-zero monthly Budget figures were found in the selected tab.")

    # Check whether the available months have identical or varying monthly budgets
    first_rec = parsed["months"][active_months[0]]
    first_tot_inc = first_rec.get("income", 0.0) + first_rec.get("other_income", 0.0)
    first_tot_exp = first_rec.get("expense", 0.0)
    has_variation = False
    for m_name in active_months[1:]:
        rec = parsed["months"][m_name]
        tot_inc = rec.get("income", 0.0) + rec.get("other_income", 0.0)
        tot_exp = rec.get("expense", 0.0)
        if abs(tot_inc - first_tot_inc) > 1.0 or abs(tot_exp - first_tot_exp) > 1.0:
            has_variation = True
            break

    scale_factor = 12.0 / n_avail
    subcategories = {}
    avail_inc_sum = 0.0
    avail_exp_sum = 0.0

    for m_name in active_months:
        rec = parsed["months"][m_name]
        avail_inc_sum += rec.get("income", 0.0) + rec.get("other_income", 0.0)
        avail_exp_sum += rec.get("expense", 0.0)

        for bucket_key in ("inc_cats", "other_cats", "exp_cats"):
            for cat_key, sub_items in rec.get(bucket_key, {}).items():
                # Strip QuickBooks report-ordering prefix (e.g., "1-6050" -> "6050") and normalize separator
                clean_cat = re.sub(r'^\d+-', '', str(cat_key).strip())
                clean_cat = re.sub(r'^(\d{4}(?:\.\d+)?)\s+', r'\1 · ', clean_cat)
                if "SURPLUS" in clean_cat.upper():
                    clean_cat = "Assigned Surplus"
                cat_sub_map = subcategories.setdefault(clean_cat, {})
                for s_lbl, s_val in sub_items:
                    if clean_cat == "Assigned Surplus":
                        clean_sub = "Surplus"
                    else:
                        clean_sub = re.sub(r'^\d+-', '', str(s_lbl).strip())
                        clean_sub = re.sub(r'^(\d{4}(?:\.\d+)?)\s+', r'\1 · ', clean_sub)
                    cat_sub_map[clean_sub] = cat_sub_map.get(clean_sub, 0.0) + (float(s_val) * scale_factor)

    final_subcats = {
        cat: [[s_lbl, s_val] for s_lbl, s_val in sub_map.items() if round(s_val, 2) != 0]
        for cat, sub_map in subcategories.items()
    }
    annual_inc = int(round(avail_inc_sum * scale_factor))
    annual_exp = int(round(avail_exp_sum * scale_factor))

    status_note = None
    if n_avail < 12:
        missing_count = 12 - n_avail
        month_span = f"{active_months[0]}–{active_months[-1]}" if n_avail > 1 else active_months[0]
        if has_variation:
            status_note = (
                f"Budget data was available for {n_avail} months ({month_span}) with varying monthly amounts.\n\n"
                f"The remaining {missing_count} missing month(s) were filled using the per-category monthly average "
                f"of those {n_avail} months to project a full 12-month annual budget."
            )
        else:
            status_note = (
                f"Budget data was available for {n_avail} identical months ({month_span}).\n\n"
                f"Those exact monthly budget figures were carried forward across the remaining {missing_count} "
                f"missing month(s) to construct the full 12-month annual budget."
            )

    return final_subcats, annual_inc, annual_exp, status_note


def import_excel_budget(app):
    """Opens a unified Budget Import wizard: choose source mode (Annual vs. Financials),
    browse for the Excel file, pick the worksheet tab/column, and populate the dashboard.
    """
    desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
    default_dir = desktop_dir if os.path.exists(desktop_dir) else os.getcwd()

    try:
        selector = tk.Toplevel(app.root)
        selector.title("Import Spreadsheet Budget")
        selector.configure(bg=MODAL_BG, highlightbackground=NEON_CYAN, highlightthickness=1)
        selector.geometry("580x375")
        selector.transient(app.root)
        selector.grab_set()

        mx = app.root.winfo_x() + (app.root.winfo_width() // 2) - 290
        my = app.root.winfo_y() + (app.root.winfo_height() // 2) - 187
        selector.geometry(f"+{max(20, mx)}+{max(20, my)}")

        tk.Label(selector, text="IMPORT SPREADSHEET BUDGET", bg=MODAL_BG, fg=NEON_CYAN,
                 font=('Arial', 10, 'bold')).pack(pady=(14, 8))

        # 1. Source Layout Mode Selector (Annual Single Column vs. Financials Monthly Columns)
        source_mode_var = tk.StringVar(value="annual")
        mode_frame = tk.Frame(selector, bg=RECESSED_BG, highlightbackground=BORDER_GRAY, highlightthickness=1)
        mode_frame.pack(fill="x", padx=25, pady=(2, 10))

        tk.Radiobutton(
            mode_frame, text="Annual Budget Sheet (Single Column)",
            variable=source_mode_var, value="annual",
            bg=RECESSED_BG, fg='white', selectcolor=AXIS_GRAY,
            activebackground=RECESSED_BG, activeforeground=NEON_CYAN,
            font=('Arial', 9, 'bold'), cursor="hand2"
        ).pack(anchor="w", padx=10, pady=(6, 2))

        tk.Radiobutton(
            mode_frame, text="Financials Sheet (Monthly Budget Columns)",
            variable=source_mode_var, value="monthly_bva",
            bg=RECESSED_BG, fg='white', selectcolor=AXIS_GRAY,
            activebackground=RECESSED_BG, activeforeground=NEON_CYAN,
            font=('Arial', 9, 'bold'), cursor="hand2"
        ).pack(anchor="w", padx=10, pady=(2, 6))

        # 2. Excel File Browser Row
        frm_file = tk.Frame(selector, bg=MODAL_BG)
        frm_file.pack(fill="x", padx=25, pady=6)
        tk.Label(frm_file, text="Excel File:", bg=MODAL_BG, fg='white',
                 font=('Arial', 9, 'bold'), width=15, anchor="w").pack(side="left")

        file_display_var = tk.StringVar(value="No file selected")
        lbl_file = tk.Label(frm_file, textvariable=file_display_var, bg=RECESSED_BG, fg=SOFT_GRAY,
                            font=('Arial', 8), anchor="w", padx=8, pady=4,
                            highlightbackground=BORDER_GRAY, highlightthickness=1)
        lbl_file.pack(side="left", fill="x", expand=True, padx=(0, 8))

        wb = None
        selected_tab_var = tk.StringVar(value="Select file first...")
        selected_col_var = tk.StringVar(value="Col L (Default)")
        col_lookup = {"Col L (Default)": 11}

        def browse_excel_file():
            nonlocal wb
            initial_dir = getattr(app, 'last_import_dir', default_dir) or default_dir
            picked_path = filedialog.askopenfilename(
                parent=selector,
                title="Select Excel Budget or Financials Spreadsheet",
                initialdir=initial_dir,
                filetypes=[("Excel Files", "*.xlsx *.xlsm"), ("All Files", "*.*")]
            )
            if not picked_path:
                return
            app.last_import_dir = os.path.dirname(picked_path)
            try:
                wb = run_with_busy_banner(
                    selector,
                    f"Reading '{os.path.basename(picked_path)}'...\nPlease wait",
                    lambda: load_workbook(picked_path, data_only=True)
                )
                file_display_var.set(os.path.basename(picked_path))
                lbl_file.config(fg=NEON_CYAN)
                tab_choices = ["Select tab"] + list(wb.sheetnames)
                cb_sheet.config(values=tab_choices, state="readonly")
                selected_tab_var.set("Select tab")
                sync_mode_ui()
            except Exception as load_err:
                wb = None
                messagebox.showerror("Workbook Error", f"Could not read Excel file:\n{load_err}", parent=selector)

        tk.Button(frm_file, text="Browse...", command=browse_excel_file,
                  bg=BUTTON_BG, fg=NEON_CYAN, font=('Arial', 8, 'bold'),
                  padx=10, pady=4, bd=1, relief="solid", cursor="hand2").pack(side="right")
        # 3. Worksheet Tab & Budget Column Selectors
        frm_tab = tk.Frame(selector, bg=MODAL_BG)
        frm_tab.pack(fill="x", padx=25, pady=6)
        tk.Label(frm_tab, text="Worksheet Tab:", bg=MODAL_BG, fg='white',
                 font=('Arial', 9, 'bold'), width=15, anchor="w").pack(side="left")

        cb_sheet = ttk.Combobox(frm_tab, textvariable=selected_tab_var, values=["Select file first..."],
                                state="disabled", width=32)
        cb_sheet.pack(side="right", fill="x", expand=True)

        frm_col = tk.Frame(selector, bg=MODAL_BG)
        frm_col.pack(fill="x", padx=25, pady=6)
        lbl_col = tk.Label(frm_col, text="Budget Column:", bg=MODAL_BG, fg='white',
                           font=('Arial', 9, 'bold'), width=15, anchor="w")
        lbl_col.pack(side="left")

        cb_col = ttk.Combobox(frm_col, textvariable=selected_col_var, values=["Col L (Default)"],
                              state="disabled", width=32)
        cb_col.pack(side="right", fill="x", expand=True)

        def sync_mode_ui(*args):
            if source_mode_var.get() == "monthly_bva":
                lbl_col.config(fg=DIVIDER_GRAY)
                cb_col.config(state="disabled")
                selected_col_var.set("Auto-Sum Monthly 'Budget' Columns")
            else:
                lbl_col.config(fg='white')
                if wb is not None and selected_tab_var.get() in wb.sheetnames:
                    cb_col.config(state="readonly")
                    on_tab_selected()
                else:
                    cb_col.config(state="disabled")
                    selected_col_var.set("Col L (Default)")

        source_mode_var.trace_add("write", sync_mode_ui)

        def on_tab_selected(event=None):
            if wb is None or source_mode_var.get() == "monthly_bva":
                return
            t_name = selected_tab_var.get()
            if t_name not in wb.sheetnames:
                return
            cb_col.config(state="readonly")
            col_opts = _discover_sheet_columns(wb[t_name])
            col_lookup.clear()
            display_list = []
            default_choice = None
            for c_idx, c_lbl in col_opts:
                col_lookup[c_lbl] = c_idx
                display_list.append(c_lbl)
                if c_idx == 11 and default_choice is None:
                    default_choice = c_lbl
                elif "BUDGET" in c_lbl.upper() and default_choice is None:
                    default_choice = c_lbl
            cb_col.config(values=display_list)
            selected_col_var.set(default_choice or (display_list[0] if display_list else "Col L (Default)"))

        cb_sheet.bind("<<ComboboxSelected>>", on_tab_selected)

        BUDGET_HELP_TEXT = (
            "HOW BUDGET IMPORT MODES WORK:\n\n"
            "1. Choose Source Mode First:\n"
            "  • Annual Budget Sheet (Single Column): Select a dedicated budget tab and pick the single column holding annual figures (e.g., 'Col L — 2025 Budget').\n"
            "  • Financials Sheet (Monthly Budget Columns): Select a QuickBooks 'Budget vs. Actuals' tab. All monthly 'Budget' sub-columns (Jan–Dec) are summed automatically using exact QuickBooks account numbers.\n\n"
            "2. Missing / $0 Future Months (Monthly Mode):\n"
            "  • If fewer than 12 months contain budget data (such as a YTD September report), missing months are automatically filled using the per-category monthly average, and you will be notified.\n\n"
            "3. Annual Sheet Requirements (Single-Column Mode):\n"
            "  • Parent Categories sit in Column D; line items sit in Column E or F.\n"
            "  • Requires 'EXPENSES', 'TOTAL RESOURCES' (or 'TOTAL INCOME'), and 'TOTAL OPERATING EXPENSES' rows."
        )

        chosen_sheet_name = None
        chosen_mode = "annual"
        target_col_idx = 11

        def confirm_selection():
            nonlocal chosen_sheet_name, chosen_mode, target_col_idx
            if wb is None:
                messagebox.showwarning("File Required", "Please click 'Browse...' to select an Excel workbook first.", parent=selector)
                return
            picked = selected_tab_var.get()
            if picked in ("Select tab", "Select file first..."):
                messagebox.showwarning("Tab Required", "Please choose a worksheet tab from the dropdown.", parent=selector)
                return
            chosen_sheet_name = picked
            chosen_mode = source_mode_var.get()
            target_col_idx = col_lookup.get(selected_col_var.get(), 11)
            selector.grab_release()
            selector.destroy()

        def cancel_selection():
            selector.grab_release()
            selector.destroy()

        btn_row = tk.Frame(selector, bg=MODAL_BG)
        btn_row.pack(side="bottom", pady=16)
        tk.Button(btn_row, text="? Info",
                  command=lambda: show_import_help(selector, "Budget Import Guide", BUDGET_HELP_TEXT),
                  bg=BUTTON_BG, fg=NEON_CYAN, font=('Arial', 9, 'bold'),
                  padx=12, pady=5, bd=1, relief="solid", cursor="hand2").pack(side="left", padx=(0, 10))
        tk.Button(btn_row, text="Cancel", command=cancel_selection, bg=BUTTON_BG, fg='white',
                  font=('Arial', 9, 'bold'), padx=14, pady=5, bd=0, cursor="hand2").pack(side="left", padx=8)
        tk.Button(btn_row, text="Import Selected Tab", command=confirm_selection, bg=NEON_CYAN, fg='black',
                  font=('Arial', 9, 'bold'), padx=14, pady=5, bd=0, cursor="hand2").pack(side="left", padx=8)

        selector.bind("<Escape>", lambda e: cancel_selection())
        app.root.wait_window(selector)
        if not chosen_sheet_name or wb is None:
            return


        # Extract 4-digit year from the selected Budget Column header, tab name, or top rows
        chosen_col_label = selected_col_var.get()
        year_match = (re.search(r'\b(20\d{2})\b', chosen_col_label) or
                      re.search(r'\b(20\d{2})\b', chosen_sheet_name))
        if not year_match:
            ws_check = wb[chosen_sheet_name]
            for r in ws_check.iter_rows(max_row=8, values_only=True):
                row_str = " ".join(str(c) for c in r if c is not None)
                year_match = re.search(r'\b(20\d{2})\b', row_str)
                if year_match:
                    break

        if year_match:
            yr = year_match.group(1)
            cur_inc = re.sub(r'^20\d{2}\s+', '', app.income_title_var.get().strip())
            cur_exp = re.sub(r'^20\d{2}\s+', '', app.expense_title_var.get().strip())
            app.income_title_var.set(f"{yr} {cur_inc}")
            app.expense_title_var.set(f"{yr} {cur_exp}")

        # Reset tracking lists from application memory
        app.subcategories.clear()
        app.income_inputs.clear()
        app.expense_inputs.clear()

        # Safely loop over and destroy custom rows, protecting system titles and total frames
        for frame, assigned_title in [(app.inc_frame, app.inc_title_row), (app.exp_frame, app.exp_title_row)]:
            for widget in frame.winfo_children():
                if isinstance(widget, tk.Frame) and widget != assigned_title:
                    is_total_row = any("Total" in c.get() for c in widget.winfo_children() if
                                       isinstance(c, tk.Entry) and hasattr(c, 'get'))
                    if not is_total_row:
                        widget.destroy()

        sheet = wb[chosen_sheet_name]
        other_res_total = 0
        sheet_total_income = None
        sheet_total_expenses = None
        extrapolation_note = None

        if chosen_mode == "monthly_bva":
            extracted_subs, sheet_total_income, sheet_total_expenses, extrapolation_note = _extract_annual_from_monthly_bva(
                sheet)
            app.subcategories.update(extracted_subs)
        else:
            current_section = "Income"
            current_category = "Other Resources"

            for row_cells in sheet.iter_rows(values_only=True):
                if len(row_cells) <= target_col_idx:
                    continue

                val_c = str(row_cells[2]).strip() if row_cells[2] is not None else ""
                val_d = str(row_cells[3]).strip() if row_cells[3] is not None else ""
                val_e = str(row_cells[4]).strip() if row_cells[4] is not None else ""
                val_f = str(row_cells[5]).strip() if row_cells[5] is not None else ""
                val_target = row_cells[target_col_idx]

                if not val_d:
                    if val_e and val_f:
                        val_e = val_f if val_e.upper() == "NEW" else f"{val_e} - {val_f}"
                    elif val_f and not val_e:
                        val_e = val_f

                if "EXPENSES" in val_c.upper() or "EXPENSES" in val_d.upper():
                    if "TOTAL" in val_c.upper() or "TOTAL" in val_d.upper():
                        if val_target is not None:
                            try:
                                sheet_total_expenses = int(round(float(val_target)))
                            except (ValueError, TypeError):
                                pass
                    else:
                        current_section = "Expense"
                        current_category = "Unnamed Category"
                    continue

                if ("TOTAL RESOURCES" in val_c.upper() or "TOTAL RESOURCES" in val_d.upper() or
                        "TOTAL INCOME" in val_c.upper() or "TOTAL INCOME" in val_d.upper()):
                    if val_target is not None:
                        try:
                            sheet_total_income = int(round(float(val_target)))
                        except (ValueError, TypeError):
                            pass
                    continue

                if "SURPLUS ASSIGNED" in val_c.upper() or "SURPLUS ASSIGNED" in val_d.upper():
                    if val_target is not None:
                        try:
                            val = float(val_target)
                            if round(val, 2) != 0:
                                app.subcategories.setdefault("Assigned Surplus", []).append(["Surplus", val])
                        except (ValueError, TypeError):
                            pass
                    continue

                if "TOTAL OTHER RESOURCES" in val_c.upper() or "TOTAL OTHER RESOURCES" in val_d.upper():
                    if val_target is not None:
                        try:
                            other_res_total = int(round(float(val_target)))
                            if "Other Resources" not in app.subcategories:
                                app.subcategories["Other Resources"] = []
                        except (ValueError, TypeError):
                            pass
                    continue

                if "BENEVOLENCES" in val_d.upper() and "TOTAL" in val_d.upper():
                    if val_target is not None:
                        try:
                            val = float(val_target)
                            if round(val, 2) != 0:
                                app.subcategories.setdefault("6050 · BENEVOLENCES", []).append(["ELCA Oregon Synod", val])
                        except (ValueError, TypeError):
                            pass
                    continue

                if "TOTAL" in val_c.upper() or "TOTAL" in val_d.upper():
                    if "CONGREGATIONAL SUPPORT" in val_c.upper() or "CONGREGATIONAL SUPPORT" in val_d.upper():
                        current_category = "Other Resources"
                    continue

                if val_d and not val_e:
                    current_category = val_d
                    continue

                if val_e and val_target is not None:
                    if "TOTAL" in val_e.upper() or "SUM" in val_e.upper():
                        continue
                    try:
                        val = float(val_target)
                        if round(val, 2) == 0:
                            continue
                        if current_category == "Unnamed Category" and current_section == "Income":
                            current_category = "Other Resources"
                        app.subcategories.setdefault(current_category, []).append([val_e, val])
                    except (ValueError, TypeError):
                        pass
        # Compile and calculate ALL parent aggregates safely into a master orderable tracker list
        compiled_categories = []
        surplus_amount_found = 0.0
        total_income_found = 0.0
        total_expense_found = 0.0

        for cat_name, sub_items in app.subcategories.items():
            if cat_name == "Other Resources" and other_res_total > 0:
                cat_sum = float(other_res_total)
            else:
                cat_sum = sum(v for _, v in sub_items)

            if cat_name == "Assigned Surplus":
                surplus_amount_found = cat_sum

            # Classify Income vs. Expense using 4000-series account codes or standard Income keywords
            acct_m = re.match(r'^(\d{4})\b', cat_name.strip())
            if acct_m and acct_m.group(1).startswith("4"):
                is_income = True
            elif acct_m and int(acct_m.group(1)) >= 5000:
                is_income = False
            else:
                is_income = (
                    "SUPPORT" in cat_name.upper() or "RESOURCES" in cat_name.upper() or
                    "SURPLUS" in cat_name.upper() or "MISC INCOME" in cat_name.upper() or
                    cat_name in ["Assigned Surplus", "Other Resources"]
                )

            if any(tok in cat_name.upper() for tok in ["BENEVOLENCES", "SALARY", "BUILDING", "ADMIN", "WORSHIP", "FAITH", "COMMUNITY"]):
                is_income = False

            if is_income:
                total_income_found += cat_sum
            else:
                total_expense_found += cat_sum

            compiled_categories.append((cat_name, cat_sum, is_income))

        compiled_categories.sort(key=lambda x: x, reverse=True)

        try:
            if sheet_total_income is not None:
                if surplus_amount_found > 0 and abs((sheet_total_income + surplus_amount_found) - total_income_found) <= 2:
                    final_inc_limit = sheet_total_income + surplus_amount_found
                else:
                    final_inc_limit = sheet_total_income
            else:
                final_inc_limit = total_income_found

            final_exp_limit = sheet_total_expenses if sheet_total_expenses is not None else total_expense_found

            app.inc_total_val.set(str(int(round(final_inc_limit))))
            if hasattr(app, 'exp_total_val'):
                app.exp_total_val.set(str(int(round(final_exp_limit))))
        except (ValueError, TypeError, AttributeError):
            pass

        for cat_name, cat_sum, is_income in compiled_categories:
            if is_income:
                lbl_var, val_var = app.add_input_row(app.inc_frame, cat_name, int(round(cat_sum)))
                app.income_inputs.append((lbl_var, val_var))
            else:
                lbl_var, val_var = app.add_input_row(app.exp_frame, cat_name, int(round(cat_sum)))
                app.expense_inputs.append((lbl_var, val_var))

        tk.Button(app.inc_frame, text="+ Add Income Item", command=lambda: app.add_blank_row("Income"),
                  bg=DARK_BG, fg=NEON_CYAN, font=('Arial', 8, 'bold'), bd=0, cursor="hand2").pack(anchor="w", padx=7, pady=5)

        tk.Button(app.exp_frame, text="+ Add Expense Item", command=lambda: app.add_blank_row("Expense"),
                  bg=DARK_BG, fg=NEON_PINK, font=('Arial', 8, 'bold'), bd=0, cursor="hand2").pack(anchor="w", padx=7, pady=5)

        layout_maps = [
            (app.inc_frame, app.inc_title_row, app.inc_other_lbl),
            (app.exp_frame, app.exp_title_row, app.exp_other_lbl)
        ]

        for frame, assigned_title_row, other_lbl in layout_maps:
            widgets = frame.winfo_children()
            for w in widgets:
                w.pack_forget()

            section_header = None
            total_row = None
            item_rows = []
            add_button = None

            for w in widgets:
                if isinstance(w, tk.Label) and w != other_lbl and (
                        "CONFIG" in w.cget("text") or "TOTAL" in w.cget("text")):
                    section_header = w
                elif isinstance(w, tk.Frame) and w != assigned_title_row and any(
                        "Total" in c.get() for c in w.winfo_children() if
                        isinstance(c, tk.Entry) and hasattr(c, 'get')):
                    total_row = w
                elif isinstance(w, tk.Button) and "+" in w.cget("text"):
                    add_button = w
                elif isinstance(w, tk.Frame) and w != assigned_title_row:
                    entries = [c for c in w.winfo_children() if isinstance(c, tk.Entry)]
                    try:
                        val = float(entries[1].get() or 0.0) if len(entries) > 1 else 0.0
                    except (IndexError, ValueError):
                        val = 0.0
                    item_rows.append((w, val))

            item_rows.sort(key=lambda x: x[1], reverse=True)

            if section_header:
                section_header.pack(anchor="w", pady=(10, 4), padx=5)
            if assigned_title_row:
                assigned_title_row.pack(fill="x", pady=2, padx=5)
            if total_row:
                total_row.pack(fill="x", pady=4, padx=5)

            for row_frame, _ in item_rows:
                row_frame.pack(fill="x", pady=4, padx=5)

            if other_lbl:
                other_lbl.pack(anchor="w", padx=7, pady=2)
            if add_button:
                add_button.pack(anchor="w", padx=7, pady=5)

        if hasattr(app, 'exp_frame') and app.exp_frame:
            for widget in app.exp_frame.winfo_children():
                if isinstance(widget, tk.Frame) and widget != app.exp_title_row:
                    if any("Total" in c.get() for c in widget.winfo_children() if
                           isinstance(c, tk.Entry) and hasattr(c, 'get')):
                        for child in widget.winfo_children():
                            if isinstance(child, tk.Entry):
                                child.config(disabledforeground=NEON_PINK, fg=NEON_PINK)

        app.process_inputs()
        if hasattr(app, 'data_source_var'):
            app.data_source_var.set(f"Source: {file_display_var.get()}")

        # Reset Monthly Financials to default Forecast whenever a new Budget is imported
        if hasattr(app, 'monthly_view') and app.monthly_view:
            mv = app.monthly_view
            mv.force_forecast_reset = True
            mv._last_render_sig = None
            if hasattr(mv, 'data_source_var'):
                mv.data_source_var.set("Source: Budget Forecast")
            if getattr(mv, 'initialized', False):
                yr_m = re.search(r'\b(20\d{2})\b', app.income_title_var.get())
                if yr_m:
                    mv.title_var.set(f"{yr_m.group(1)} Monthly Financial Results")
                mv.seed_from_active_budget()
                mv.rebuild_left_table()
                mv.redraw_chart()

        if extrapolation_note:
            messagebox.showinfo(
                "Annual Budget Projected from Partial Year",
                f"Budget tab '{chosen_sheet_name}' imported.\n\n{extrapolation_note}"
            )
        else:
            messagebox.showinfo("Success", f"Budget tab '{chosen_sheet_name}' successfully ingested!")

    except Exception as e:
        messagebox.showerror("Error", f"Failed to ingest Excel workbook data:\n{str(e)}")
