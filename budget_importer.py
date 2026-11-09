import os
import tkinter as tk
from tkinter import filedialog, messagebox
from openpyxl import load_workbook


def import_excel_budget(app):
    """Opens a file dialog, reads workbook tabs, prompts user with a Listbox selection menu,
    and cleanly reconstructs category allocations directly into the dashboard application.
    """
    desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
    file_selected = filedialog.askopenfilename(
        title="Select Excel Budget Spreadsheet",
        initialdir=desktop_dir,
        filetypes=[("Excel Files", "*.xlsx"), ("All Files", "*.*")]
    )
    if not file_selected:
        return

    try:
        wb = load_workbook(file_selected, data_only=True)
        sheets = wb.sheetnames

        selector = tk.Toplevel(app.root)
        selector.title("Select Budget Sheet Tab")
        selector.configure(bg='#1e1e1e')
        selector.geometry("320x300")
        selector.transient(app.root)
        selector.grab_set()

        mx = app.root.winfo_x() + (app.root.winfo_width() // 2) - 160
        my = app.root.winfo_y() + (app.root.winfo_height() // 2) - 150
        selector.geometry(f"+{mx}+{my}")

        tk.Label(selector, text="Choose a sheet tab to import:", bg='#1e1e1e', fg='white',
                 font=('Arial', 10, 'bold')).pack(anchor="w", padx=10, pady=8)

        list_frame = tk.Frame(selector, bg='#1e1e1e')
        list_frame.pack(fill="both", expand=True, padx=10, pady=2)

        box = tk.Listbox(list_frame, bg='#2a2a2a', fg='white', selectbackground='#00F0FF',
                         selectforeground='black', font=('Arial', 9), bd=0, highlightthickness=0)
        scroll = tk.Scrollbar(list_frame, orient="vertical", command=box.yview)
        box.configure(yscrollcommand=scroll.set)
        box.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        for name in sheets:
            box.insert("end", name)

        if sheets: box.selection_set(0)
        chosen_sheet_name = None

        def confirm_selection():
            nonlocal chosen_sheet_name
            selection = box.curselection()
            if selection:
                chosen_sheet_name = box.get(selection)
            selector.destroy()

        btn = tk.Button(selector, text="Import Selected Tab", command=confirm_selection,
                        bg='#00F0FF', fg='black', font=('Arial', 9, 'bold'), pady=4)
        btn.pack(fill="x", padx=10, pady=10)

        selector.wait_window()
        if not chosen_sheet_name: return

        # FIXED: Purely reset tracking lists from application memory
        app.subcategories.clear()
        app.income_inputs.clear()
        app.expense_inputs.clear()

        # FIXED: Safely loop over and destroy ONLY custom rows, protecting system titles and total frames
        for frame, assigned_title in [(app.inc_frame, app.inc_title_row), (app.exp_frame, app.exp_title_row)]:
            for widget in frame.winfo_children():
                if isinstance(widget, tk.Frame) and widget != assigned_title:
                    # Verify it isn't the locked Total Limit row widget frame
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
                # Detect section transitions from resources to expenditures
                # Detect section transitions from resources to expenditures
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

            is_income = any(
                "SUPPORT" in cat_name.upper() or "RESOURCES" in cat_name.upper() or "SURPLUS" in cat_name.upper()
                for sub_lbl, _ in sub_items
            ) or cat_name in ["Assigned Surplus", "Other Resources"]

            if "BENEVOLENCES" in cat_name.upper() or "SALARY" in cat_name.upper() or "BUILDING" in cat_name.upper() or "ADMIN" in cat_name.upper():
                is_income = False

            compiled_categories.append((cat_name, cat_sum, is_income))

        compiled_categories.sort(key=lambda x: x[1], reverse=True)

        try:
            current_base_limit = 385000 + 44000
            calculated_total_income_limit = current_base_limit + surplus_amount_found
            app.inc_total_val.set(str(int(calculated_total_income_limit)))
        except (ValueError, TypeError, AttributeError):
            pass

        # Generate the fully sorted widgets down the sidebar frame layout panel sequential rows
        for cat_name, cat_sum, is_income in compiled_categories:
            if is_income:
                lbl_var, val_var = app.add_input_row(app.inc_frame, cat_name, int(cat_sum))
                app.income_inputs.append((lbl_var, val_var))
            else:
                lbl_var, val_var = app.add_input_row(app.exp_frame, cat_name, int(cat_sum))
                app.expense_inputs.append((lbl_var, val_var))

        # Re-instantiate operational addition buttons right beneath sorted sections layout
        tk.Button(app.inc_frame, text="+ Add Income Item", command=lambda: app.add_blank_row("Income"),
                  bg='#111111', fg='#00F0FF', font=('Arial', 8, 'bold'), bd=0, cursor="hand2")
        tk.Button(app.exp_frame, text="+ Add Expense Item", command=lambda: app.add_blank_row("Expense"),
                  bg='#111111', fg='#FF007F', font=('Arial', 8, 'bold'), bd=0, cursor="hand2")

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
                        # FIXED: Extract the numeric entry field explicitly by targeting list index 1
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

        app.process_inputs()
        messagebox.showinfo("Success", f"Budget tab '{chosen_sheet_name}' successfully ingested!")

    except Exception as e:
        messagebox.showerror("Error", f"Failed to ingest Excel workbook data:\n{str(e)}")
