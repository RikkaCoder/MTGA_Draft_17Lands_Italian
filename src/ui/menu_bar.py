"""
src/ui/menu_bar.py
Handles the generation of the native OS Menu bar (File, Tools, Theme)
and encapsulates the associated file dialogs and export logic.
"""

import tkinter
import os
from tkinter import filedialog, messagebox
from src import constants
from src.ui.styles import Theme
from src.configuration import write_configuration
from src.ui.windows.practice_dialog import PracticeDialog
from src.i18n import configure_card_names, tr


class AppMenuBar:
    def __init__(self, root, app_context):
        self.root = root
        self.app_context = app_context
        self.config = app_context.configuration
        self._setup_menu()

    def _setup_menu(self):
        m = tkinter.Menu(self.root)
        self.root.config(menu=m)

        # --- FILE MENU ---
        file_m = tkinter.Menu(m, tearoff=0)
        m.add_cascade(label=tr("common.file"), menu=file_m)
        file_m.add_command(
            label=tr("menu.preferences"), command=self.app_context._open_settings
        )
        file_m.add_separator()
        file_m.add_command(label=tr("menu.read_draft_log"), command=self._read_draft_log)
        file_m.add_command(label=tr("menu.read_player_log"), command=self._read_player_log)
        file_m.add_command(
            label=tr("menu.locate_data"), command=self._locate_mtga_data
        )
        file_m.add_separator()
        file_m.add_command(label=tr("menu.export_csv"), command=self._export_csv)
        file_m.add_command(label=tr("menu.export_json"), command=self._export_json)
        file_m.add_separator()
        file_m.add_command(label=tr("menu.exit"), command=self.app_context._on_close)

        # --- TOOLS MENU ---
        tools_m = tkinter.Menu(m, tearoff=0)
        m.add_cascade(label=tr("common.tools"), menu=tools_m)
        tools_m.add_command(
            label=tr("menu.practice_random"),
            command=lambda: PracticeDialog(
                self.root, self.app_context, is_import=False
            ),
        )
        tools_m.add_command(
            label=tr("menu.practice_import"),
            command=lambda: PracticeDialog(self.root, self.app_context, is_import=True),
        )

        # --- THEME MENU ---
        theme_m = tkinter.Menu(m, tearoff=0)
        m.add_cascade(label=tr("menu.theme"), menu=theme_m)
        theme_m.add_command(
            label=tr("menu.system_theme"),
            command=lambda: self._update_theme(new_palette="System"),
        )
        theme_m.add_separator()

        for name in Theme.THEME_MAPPING.keys():
            if name == "System":
                continue
            theme_m.add_command(
                label=tr("menu.mana_flair", name=name),
                command=lambda n=name: self._update_theme(new_palette=n),
            )

        custom_m = tkinter.Menu(theme_m, tearoff=0)
        theme_m.add_cascade(label=tr("menu.custom_themes"), menu=custom_m)
        custom_m.add_command(
            label=tr("menu.browse_theme"), command=self._browse_custom_tcl
        )

        for name, path in Theme.discover_custom_themes().items():
            custom_m.add_command(
                label=name, command=lambda p=path: self._update_theme(new_custom=p)
            )

    def _update_theme(self, new_engine=None, new_palette=None, new_custom=None):
        s = self.config.settings
        if new_engine:
            s.theme_base = new_engine
        if new_palette:
            s.theme = new_palette
        if new_custom:
            s.theme_custom_path = new_custom
        else:
            s.theme_custom_path = ""

        write_configuration(self.config)
        current_scale = constants.UI_SIZE_DICT.get(s.ui_size, 1.0)
        Theme.apply(
            self.root,
            palette=s.theme,
            engine=getattr(s, "theme_base", "clam"),
            custom_path=s.theme_custom_path,
            scale=current_scale,
        )

    def _browse_custom_tcl(self):
        f = filedialog.askopenfilename(
            filetypes=(("Tcl files", "*.tcl"), ("All", "*.*"))
        )
        if f:
            self._update_theme(new_custom=f)

    def _read_draft_log(self):
        f = filedialog.askopenfilename(filetypes=(("Log", "*.log"), ("All", "*.*")))
        if f:
            if hasattr(self.app_context, "loading_overlay"):
                self.app_context.loading_overlay.show(tr("loading.draft_log"))
                self.app_context.loading_overlay.update_status(tr("loading.queuing"))
            self.app_context.orchestrator.set_file_and_scan(f)

    def _read_player_log(self):
        f = filedialog.askopenfilename(filetypes=(("Log", "*.log"), ("All", "*.*")))
        if f:
            if hasattr(self.app_context, "loading_overlay"):
                self.app_context.loading_overlay.show(tr("loading.player_log"))
                self.app_context.loading_overlay.update_status(tr("loading.queuing"))
            self.app_context.orchestrator.set_file_and_scan(f)

    def _locate_mtga_data(self):
        folder = filedialog.askdirectory(title=tr("menu.select_data_folder"))
        if folder:
            if not folder.endswith("MTGA_Data"):
                if os.path.exists(os.path.join(folder, "MTGA_Data")):
                    folder = os.path.join(folder, "MTGA_Data")

            if os.path.exists(os.path.join(folder, "Downloads", "Raw")):
                self.config.settings.database_location = folder
                write_configuration(self.config)
                configure_card_names(folder)

                if (
                    hasattr(self.app_context, "orchestrator")
                    and self.app_context.orchestrator.scanner
                    and self.app_context.orchestrator.scanner.set_data
                ):
                    self.app_context.orchestrator.scanner.set_data.db_path = folder
                    self.app_context.orchestrator.scanner.set_data.unknown_id_cache.clear()
                    self.app_context.orchestrator.request_math_update()
                    self.app_context._refresh_ui_data()

                messagebox.showinfo(
                    tr("common.success"),
                    tr("data_folder.success", folder=folder),
                )
            else:
                messagebox.showerror(
                    tr("common.error"),
                    tr("data_folder.invalid"),
                )

    def _export_csv(self):
        h = self.app_context.orchestrator.scanner.retrieve_draft_history()
        if not h:
            return
        from src.card_logic import export_draft_to_csv

        data = export_draft_to_csv(
            h,
            self.app_context.orchestrator.scanner.set_data,
            self.app_context.orchestrator.scanner.picked_cards,
        )
        f = filedialog.asksaveasfile(mode="w", defaultextension=".csv")
        if f:
            with f:
                f.write(data)
            messagebox.showinfo(tr("common.success"), tr("menu.export_complete"))

    def _export_json(self):
        h = self.app_context.orchestrator.scanner.retrieve_draft_history()
        if not h:
            return
        from src.card_logic import export_draft_to_json

        data = export_draft_to_json(
            h,
            self.app_context.orchestrator.scanner.set_data,
            self.app_context.orchestrator.scanner.picked_cards,
        )
        f = filedialog.asksaveasfile(mode="w", defaultextension=".json")
        if f:
            with f:
                f.write(data)
            messagebox.showinfo(tr("common.success"), tr("menu.export_complete"))
