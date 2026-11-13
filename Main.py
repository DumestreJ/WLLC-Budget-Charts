import os
import tkinter as tk
from budget_view import BudgetView
from monthly_financials import MonthlyFinancialsView


class ChurchFinanceApp:
    """Lightweight top-level shell managing the shared PanedWindow and mode switcher."""

    def __init__(self, root):
        self.root = root
        self.root.title("West Linn Lutheran Church - Financial & Budget Dashboard")
        self.root.geometry("1280x760")
        self.root.minsize(920, 600)
        self.root.configure(bg='#111111')

        desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
        self.active_mode_var = tk.StringVar(value="Budget")

        self.paned_window = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, bg='#262626', sashwidth=4, bd=0)
        self.paned_window.pack(fill="both", expand=True)

        # Shared Left Panel Container with Top Mode Switcher Bar
        self.left_panel = tk.Frame(self.paned_window, bg='#111111')
        self.paned_window.add(self.left_panel, minsize=220)

        mode_bar = tk.Frame(self.left_panel, bg='#1a1a1a', pady=4, padx=6)
        mode_bar.pack(side="top", fill="x")

        self.btn_mode_budget = tk.Button(
            mode_bar, text="Budget", bg='#00F0FF', fg='black',
            font=('Arial', 9, 'bold'), bd=0, pady=4, cursor="hand2",
            command=lambda: self.switch_mode("Budget")
        )
        self.btn_mode_budget.pack(side="left", fill="x", expand=True, padx=(0, 2))

        self.btn_mode_fin = tk.Button(
            mode_bar, text="Monthly Financials", bg='#262626', fg='#aaaaaa',
            font=('Arial', 9, 'bold'), bd=0, pady=4, cursor="hand2",
            command=lambda: self.switch_mode("Financials")
        )
        self.btn_mode_fin.pack(side="left", fill="x", expand=True, padx=(2, 0))

        self.budget_left_frame = tk.Frame(self.left_panel, bg='#111111')
        self.budget_left_frame.pack(side="top", fill="both", expand=True)
        self.fin_left_frame = tk.Frame(self.left_panel, bg='#111111')

        # Shared Right Panel Container
        self.right_panel = tk.Frame(self.paned_window, bg='#111111')
        self.paned_window.add(self.right_panel, minsize=400)
        self.right_panel.rowconfigure(0, weight=1)
        self.right_panel.columnconfigure(0, weight=1)

        self.budget_right_frame = tk.Frame(self.right_panel, bg='#111111')
        self.budget_right_frame.grid(row=0, column=0, sticky="nsew")
        self.fin_right_frame = tk.Frame(self.right_panel, bg='#111111')

        # Instantiate both self-contained views
        self.budget_view = BudgetView(self, self.budget_left_frame, self.budget_right_frame)
        self.monthly_view = MonthlyFinancialsView(self, self.fin_left_frame, self.fin_right_frame)

    @property
    def last_import_dir(self):
        return getattr(self.budget_view, 'last_import_dir', os.path.join(os.path.expanduser("~"), "Desktop"))

    @last_import_dir.setter
    def last_import_dir(self, value):
        if hasattr(self, 'budget_view'):
            self.budget_view.last_import_dir = value
    @property
    def income_inputs(self): return self.budget_view.income_inputs
    @property
    def expense_inputs(self): return self.budget_view.expense_inputs
    @property
    def subcategories(self): return self.budget_view.subcategories
    def clean_label_text(self, txt): return self.budget_view.clean_label_text(txt)

    def dismiss_all_tooltips(self):
        """Destroys any active or pinned tooltip across both views when switching tabs."""
        for view in (getattr(self, 'budget_view', None), getattr(self, 'monthly_view', None)):
            if view is not None:
                view.tooltip_frozen = False
                if getattr(view, 'tooltip', None):
                    try:
                        view.tooltip.destroy()
                    except Exception:
                        pass
                    view.tooltip = None

    def switch_mode(self, mode):
        if self.active_mode_var.get() == mode:
            return
        self.dismiss_all_tooltips()
        self.active_mode_var.set(mode)

        self.tooltip_frozen = False

        if mode == "Budget":
            self.btn_mode_budget.config(bg='#00F0FF', fg='black')
            self.btn_mode_fin.config(bg='#262626', fg='#aaaaaa')
            self.fin_left_frame.pack_forget()
            self.budget_left_frame.pack(side="top", fill="both", expand=True)
            self.fin_right_frame.grid_forget()
            self.budget_right_frame.grid(row=0, column=0, sticky="nsew")
            self.budget_view.on_resize(forced=True)
        else:
            self.btn_mode_budget.config(bg='#262626', fg='#aaaaaa')
            self.btn_mode_fin.config(bg='#FF007F', fg='black')
            self.budget_left_frame.pack_forget()
            self.budget_right_frame.grid_forget()

            # 1. Cover BOTH panels with a dark busy overlay first so no half-drawn widgets flash
            self.root.config(cursor="watch")
            busy_right = tk.Frame(self.right_panel, bg='#111111')
            busy_right.grid(row=0, column=0, sticky="nsew")
            tk.Label(
                busy_right,
                text="Rendering Monthly Financials...\nPlease wait",
                bg='#161616', fg='#00F0FF',
                font=('Arial', 13, 'bold'),
                padx=30, pady=20,
                highlightbackground='#00F0FF', highlightthickness=1
            ).place(relx=0.5, rely=0.5, anchor="center")
            busy_right.lift()
            self.root.update()

            try:
                # 2. Mount both panels behind the raised overlay while data & Matplotlib build
                self.fin_left_frame.pack(side="top", fill="both", expand=True)
                self.fin_right_frame.grid(row=0, column=0, sticky="nsew")
                busy_right.lift()

                self.monthly_view.ensure_initialized()

                # 3. Force Tkinter to finish stretching the canvas & bottom controls before revealing
                self.root.update_idletasks()
                self.monthly_view.redraw_chart()
                self.root.update_idletasks()
            finally:
                busy_right.destroy()
                self.root.config(cursor="")


if __name__ == "__main__":
    root = tk.Tk()
    app = ChurchFinanceApp(root)
    root.mainloop()
