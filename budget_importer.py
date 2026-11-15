import os
from tkinter import filedialog
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from utility_methods import *  # Imports cleanly from your support module
import re


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


def import_excel_budget(app):
    """Opens a file dialog, reads workbook tabs, prompts user with Tab and Budget Column dropdowns,
    and cleanly reconstructs category allocations directly into the dashboard application.
    """
    desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
    default_dir = desktop_dir if os.path.exists(desktop_dir) else os.getcwd()
    initial_dir = getattr(app, 'last_import_dir', default_dir) or default_dir

    file_selected = filedialog.askopenfilename(
        title="Select Excel Budget Spreadsheet",
        initialdir=initial_dir,
        filetypes=[("Excel Files", "*.xlsx *.xlsm"), ("All Files", "*.*")]
    )
    if not file_selected:
        return

    # CAPTURE ACTIVE IMPORT DIRECTORY SOURCE LOCATION
    app.last_import_dir = os.path.dirname(file_selected)

    try:
        wb = load_workbook(file_selected, data_only=True)
        sheets = wb.sheetnames

        selector = tk.Toplevel(app.root)
        selector.title("Select Budget Worksheet & Column")
        selector.configure(bg='#1c1c1c', highlightbackground='#00F0FF', highlightthickness=1)
        selector.geometry("460x255")
        selector.transient(app.root)
        selector.grab_set()

        mx = app.root.winfo_x() + (app.root.winfo_width() // 2) - 230
        my = app.root.winfo_y() + (app.root.winfo_height() // 2) - 127
        selector.geometry(f"+{mx}+{my}")

        tk.Label(selector, text="SELECT BUDGET WORKBOOK TAB & COLUMN", bg='#1c1c1c', fg='#00F0FF',
                 font=('Arial', 10, 'bold')).pack(pady=(16, 10))

        frm_tab = tk.Frame(selector, bg='#1c1c1c')
        frm_tab.pack(fill="x", padx=25, pady=6)
        tk.Label(frm_tab, text="Budget Tab:", bg='#1c1c1c', fg='white',
                 font=('Arial', 9, 'bold'), width=15, anchor="w").pack(side="left")

        tab_choices = ["Select tab"] + list(sheets)
        selected_tab_var = tk.StringVar(value="Select tab")
        cb_sheet = ttk.Combobox(frm_tab, textvariable=selected_tab_var, values=tab_choices, state="readonly", width=30)
        cb_sheet.pack(side="right", fill="x", expand=True)

        frm_col = tk.Frame(selector, bg='#1c1c1c')
        frm_col.pack(fill="x", padx=25, pady=6)
        tk.Label(frm_col, text="Budget Column:", bg='#1c1c1c', fg='white',
                 font=('Arial', 9, 'bold'), width=15, anchor="w").pack(side="left")

        selected_col_var = tk.StringVar(value="Col L (Default)")
        cb_col = ttk.Combobox(frm_col, textvariable=selected_col_var, values=["Col L (Default)"], state="readonly", width=30)
        cb_col.pack(side="right", fill="x", expand=True)

        col_lookup = {"Col L (Default)": 11}

        def on_tab_selected(event=None):
            t_name = selected_tab_var.get()
            if t_name == "Select tab" or t_name not in wb.sheetnames:
                return
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

        chosen_sheet_name = None
        target_col_idx = 11

        def confirm_selection():
            nonlocal chosen_sheet_name, target_col_idx
            picked = selected_tab_var.get()
            if picked == "Select tab":
                messagebox.showwarning("Selection Required", "Please choose a worksheet tab from the dropdown.", parent=selector)
                return
            chosen_sheet_name = picked
            target_col_idx = col_lookup.get(selected_col_var.get(), 11)
            selector.grab_release()
            selector.destroy()

        def cancel_selection():
            selector.grab_release()
            selector.destroy()

        btn_row = tk.Frame(selector, bg='#1c1c1c')
        btn_row.pack(side="bottom", pady=18)
        tk.Button(btn_row, text="Cancel", command=cancel_selection, bg='#2a2a2a', fg='white',
                  font=('Arial', 9, 'bold'), padx=14, pady=5, bd=0, cursor="hand2").pack(side="left", padx=10)
        tk.Button(btn_row, text="Import Selected Tab", command=confirm_selection, bg='#00F0FF', fg='black',
                  font=('Arial', 9, 'bold'), padx=14, pady=5, bd=0, cursor="hand2").pack(side="left", padx=10)

        BUDGET_HELP_TEXT = (
            "WHAT THIS IMPORTER LOOKS FOR:\n\n"
            "1. Budget Tab & Column:\n"
            "   • Select the worksheet tab containing the annual budget (e.g., '2026 Budget' or '2026 Workplan').\n"
            "   • Pick the column holding the annual budget figures you want to load (e.g., 'Col L — 2025 Budget').\n"
            "   • The 4-digit year in your selected column header (or tab name) is automatically added to the chart titles.\n\n"
            "2. Table Header Row (Top 15 Rows):\n"
            "   • Include a header row containing 'Budget Line' or 'YTD' so column names populate automatically.\n\n"
            "3. Category & Line-Item Hierarchy:\n"
            "   • Parent Categories (e.g., '6300 · BUILDING & PROPERTY') sit in Column D with Column E blank.\n"
            "   • Line Items sit indented in Column E or Column F (account number prefixes are optional), with dollar amounts in your selected Budget Column.\n\n"
            "4. Required Section & Total Labels (Columns C or D):\n"
            "   • 'EXPENSES' marks the switch from Income to Expense categories.\n"
            "   • 'SURPLUS ASSIGNED' captures prior-year carryover funds.\n"
            "   • 'TOTAL RESOURCES' (or 'TOTAL INCOME') and 'TOTAL OPERATING EXPENSES' set the target totals."
        )

        tk.Button(btn_row, text="? Info",
                  command=lambda: show_import_help(selector, "Budget Import Guide", BUDGET_HELP_TEXT),
                  bg='#2a2a2a', fg='#00F0FF', font=('Arial', 9, 'bold'),
                  padx=12, pady=5, bd=1, relief="solid", cursor="hand2").pack(side="left", padx=(0, 10))

        selector.bind("<Escape>", lambda e: cancel_selection())
        app.root.wait_window(selector)
        if not chosen_sheet_name:
            return

        # Prefer the 4-digit year from the selected Budget Column header (e.g., "Col L — 2025 Budget"),
        # falling back to the tab name or top rows if needed.
        chosen_col_label = selected_col_var.get()
        year_match = re.search(r'\b(20\d{2})\b', chosen_col_label) or re.search(r'\b(20\d{2})\b', chosen_sheet_name)

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
        current_section = "Income"
        current_category = "Other Resources"
        other_res_total = 0
        sheet_total_income = None
        sheet_total_expenses = None

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

            # Detect section transitions from resources to expenditures
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

            # Capture "TOTAL OTHER RESOURCES" to force the official total value
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

            # Identify Parent Category blocks (Column D populated, Column E empty)
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
        surplus_amount_found = 0
        total_income_found = 0
        total_expense_found = 0

        for cat_name, sub_items in app.subcategories.items():
            if cat_name == "Other Resources":
                cat_sum = other_res_total if other_res_total > 0 else sum(v for _, v in sub_items)
            else:
                cat_sum = sum(v for _, v in sub_items)

            if cat_name == "Assigned Surplus":
                surplus_amount_found = cat_sum

            # Explicit context map checks to isolate income sectors securely
            is_income = any(
                "SUPPORT" in cat_name.upper() or "RESOURCES" in cat_name.upper() or "SURPLUS" in cat_name.upper()
                for sub_lbl, _ in sub_items
            ) or cat_name in ["Assigned Surplus", "Other Resources"]

            if "BENEVOLENCES" in cat_name.upper() or "SALARY" in cat_name.upper() or "BUILDING" in cat_name.upper() or "ADMIN" in cat_name.upper():
                is_income = False

            if is_income:
                total_income_found += cat_sum
            else:
                total_expense_found += cat_sum

            compiled_categories.append((cat_name, cat_sum, is_income))

        # Enforce ordering sorting key targeting numeric index values safely
        compiled_categories.sort(key=lambda x: x[1], reverse=True)

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

        # Generate the sorted row widgets sequentially down the frame panel
        for cat_name, cat_sum, is_income in compiled_categories:
            if is_income:
                lbl_var, val_var = app.add_input_row(app.inc_frame, cat_name, int(round(cat_sum)))
                app.income_inputs.append((lbl_var, val_var))
            else:
                lbl_var, val_var = app.add_input_row(app.exp_frame, cat_name, int(round(cat_sum)))
                app.expense_inputs.append((lbl_var, val_var))

        # Re-instantiate operational addition buttons right beneath sorted data list elements
        tk.Button(app.inc_frame, text="+ Add Income Item", command=lambda: app.add_blank_row("Income"),
                  bg='#111111', fg='#00F0FF', font=('Arial', 8, 'bold'), bd=0, cursor="hand2").pack(anchor="w", padx=7, pady=5)

        tk.Button(app.exp_frame, text="+ Add Expense Item", command=lambda: app.add_blank_row("Expense"),
                  bg='#111111', fg='#FF007F', font=('Arial', 8, 'bold'), bd=0, cursor="hand2").pack(anchor="w", padx=7, pady=5)

        # Explicit Layout Sorting Manager to arrange visual tree elements flawlessly on screen
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
                                child.config(disabledforeground='#FF007F', fg='#FF007F')

        app.process_inputs()
        messagebox.showinfo("Success", f"Budget tab '{chosen_sheet_name}' successfully ingested!")

    except Exception as e:
        messagebox.showerror("Error", f"Failed to ingest Excel workbook data:\n{str(e)}")
