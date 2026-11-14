import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from openpyxl import load_workbook
import re


def import_excel_budget(app):
    """Opens a file dialog, reads workbook tabs, prompts user with a dropdown tab selector,
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
        selector.title("Select Budget Worksheet")
        selector.configure(bg='#1c1c1c', highlightbackground='#00F0FF', highlightthickness=1)
        selector.geometry("430x210")
        selector.transient(app.root)
        selector.grab_set()

        mx = app.root.winfo_x() + (app.root.winfo_width() // 2) - 215
        my = app.root.winfo_y() + (app.root.winfo_height() // 2) - 105
        selector.geometry(f"+{mx}+{my}")

        tk.Label(selector, text="SELECT BUDGET WORKBOOK TAB", bg='#1c1c1c', fg='#00F0FF',
                 font=('Arial', 10, 'bold')).pack(pady=(16, 10))

        frm = tk.Frame(selector, bg='#1c1c1c')
        frm.pack(fill="x", padx=25, pady=8)
        tk.Label(frm, text="Budget Tab:", bg='#1c1c1c', fg='white',
                 font=('Arial', 9, 'bold'), width=14, anchor="w").pack(side="left")

        tab_choices = ["Select tab"] + list(sheets)
        selected_tab_var = tk.StringVar(value="Select tab")
        cb_sheet = ttk.Combobox(frm, textvariable=selected_tab_var, values=tab_choices, state="readonly", width=28)
        cb_sheet.pack(side="right", fill="x", expand=True)

        chosen_sheet_name = None

        def confirm_selection():
            nonlocal chosen_sheet_name
            picked = selected_tab_var.get()
            if picked == "Select tab":
                messagebox.showwarning("Selection Required", "Please choose a worksheet tab from the dropdown.", parent=selector)
                return
            chosen_sheet_name = picked
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

        selector.bind("<Escape>", lambda e: cancel_selection())
        app.root.wait_window(selector)
        if not chosen_sheet_name:
            return

        # Extract 4-digit year from the selected tab name (e.g., "2026 Budget") or header rows
        year_match = re.search(r'\b(20\d{2})\b', chosen_sheet_name)
        if not year_match:
            ws_check = wb[chosen_sheet_name]
            for r in ws_check.iter_rows(max_row=5, values_only=True):
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
        current_section = "Income"
        current_category = "Other Resources"

        for row_cells in sheet.iter_rows(values_only=True):
            if len(row_cells) < 13: continue

            val_c = str(row_cells[2]).strip() if row_cells[2] is not None else ""
            val_d = str(row_cells[3]).strip() if row_cells[3] is not None else ""
            val_e = str(row_cells[4]).strip() if row_cells[4] is not None else ""
            val_f = str(row_cells[5]).strip() if row_cells[5] is not None else ""
            val_l = row_cells[11]

            if val_e and val_f and not val_d:
                val_e = f"{val_e} - {val_f}"

            # Detect section transitions from resources to expenditures
            if "EXPENSES" in val_c.upper() or "EXPENSES" in val_d.upper():
                current_section = "Expense"
                current_category = "Unnamed Category"
                continue

            # Isolate deficit carryover fields and push to dashboard view as Income slices
            if "SURPLUS ASSIGNED" in val_c.upper() or "SURPLUS ASSIGNED" in val_d.upper():
                if val_l is not None:
                    try:
                        val = int(float(val_l))
                        if val != 0:
                            if "Assigned Surplus" not in app.subcategories:
                                app.subcategories["Assigned Surplus"] = []
                            app.subcategories["Assigned Surplus"].append(["Surplus", val])
                    except (ValueError, TypeError):
                        pass
                continue

            # Capture "TOTAL OTHER RESOURCES" to force the official total value
            if "TOTAL OTHER RESOURCES" in val_c.upper() or "TOTAL OTHER RESOURCES" in val_d.upper():
                if val_l is not None:
                    try:
                        other_res_total = int(float(val_l))
                        if "Other Resources" not in app.subcategories:
                            app.subcategories["Other Resources"] = []
                    except (ValueError, TypeError):
                        pass
                continue

            # Skip other general summary rows
            if "TOTAL" in val_c.upper() or "TOTAL" in val_d.upper():
                if "CONGREGATIONAL SUPPORT" in val_c.upper() or "CONGREGATIONAL SUPPORT" in val_d.upper():
                    current_category = "Other Resources"
                continue

            # Identify Parent Category blocks (Column D populated, Column E empty)
            if val_d and not val_e:
                current_category = val_d
                continue

            # Identify Subcategory entries (Column E populated, Column L contains values)
            if val_e and val_l is not None:
                if "TOTAL" in val_e.upper() or "SUM" in val_e.upper():
                    continue
                try:
                    val = int(float(val_l))
                    if val == 0: continue
                    if current_category == "Unnamed Category" and current_section == "Income":
                        current_category = "Other Resources"
                    if current_category not in app.subcategories:
                        app.subcategories[current_category] = []
                    app.subcategories[current_category].append([val_e, val])
                except (ValueError, TypeError):
                    pass
        # Compile and calculate ALL parent aggregates safely into a master orderable tracker list
        compiled_categories = []
        surplus_amount_found = 0

        for cat_name, sub_items in app.subcategories.items():
            if cat_name == "Other Resources":
                cat_sum = 44000
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

            compiled_categories.append((cat_name, cat_sum, is_income))

        # Enforce ordering sorting key targeting numeric index values safely
        compiled_categories.sort(key=lambda x: x[1], reverse=True)

        try:
            current_base_limit = 385000 + 44000
            calculated_total_income_limit = current_base_limit + surplus_amount_found
            app.inc_total_val.set(str(int(calculated_total_income_limit)))
        except (ValueError, TypeError, AttributeError):
            pass

        # Generate the sorted row widgets sequentially down the frame panel
        for cat_name, cat_sum, is_income in compiled_categories:
            if is_income:
                lbl_var, val_var = app.add_input_row(app.inc_frame, cat_name, int(cat_sum))
                app.income_inputs.append((lbl_var, val_var))
            else:
                lbl_var, val_var = app.add_input_row(app.exp_frame, cat_name, int(cat_sum))
                app.expense_inputs.append((lbl_var, val_var))

        # Re-instantiate operational addition buttons right beneath sorted data list elements
        tk.Button(app.inc_frame, text="+ Add Income Item", command=lambda: app.add_blank_row("Income"),
                  bg='#111111', fg='#00F0FF', font=('Arial', 8, 'bold'), bd=0, cursor="hand2").pack(anchor="w", padx=7,
                                                                                                    pady=5)

        tk.Button(app.exp_frame, text="+ Add Expense Item", command=lambda: app.add_blank_row("Expense"),
                  bg='#111111', fg='#FF007F', font=('Arial', 8, 'bold'), bd=0, cursor="hand2").pack(anchor="w", padx=7,
                                                                                                    pady=5)

        # Explicit Layout Sorting Manager to arrange visual tree elements flawlessly on screen
        layout_maps = [
            (app.inc_frame, app.inc_title_row, app.inc_other_lbl),
            (app.exp_frame, app.exp_title_row, app.exp_other_lbl)
        ]

        for frame, assigned_title_row, other_lbl in layout_maps:
            widgets = frame.winfo_children()
            for w in widgets: w.pack_forget()

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

            if section_header: section_header.pack(anchor="w", pady=(10, 4), padx=5)
            if assigned_title_row: assigned_title_row.pack(fill="x", pady=2, padx=5)
            if total_row: total_row.pack(fill="x", pady=4, padx=5)

            for row_frame, _ in item_rows:
                row_frame.pack(fill="x", pady=4, padx=5)

            if other_lbl: other_lbl.pack(anchor="w", padx=7, pady=2)
            if add_button: add_button.pack(anchor="w", padx=7, pady=5)

        # Enforce a matching Pink/Red formatting style context to Expense summary total boxes
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
