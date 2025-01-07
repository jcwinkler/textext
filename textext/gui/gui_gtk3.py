"""
This file is part of TexText, an extension for the vector
illustration program Inkscape.

Copyright (c) 2006-2024 TexText developers.

TexText is released under the 3-Clause BSD license. See
file LICENSE.txt or go to https://github.com/textext/textext
for full license details.
"""
from abc import ABCMeta, abstractmethod
import shutil
from typing import Dict, List, Union
import os
from textext.elements import TexTextEleMetaData
from textext.settings import SettingsTexText, Align
from textext.utils.environment import Cmds
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, Gio  # noqa


class DlgExePaths:
    def __init__(self, exe_paths: Dict[str, str]):
        self.exe_paths = exe_paths
        self.builder: Gtk.Builder = Gtk.Builder()
        self.builder.add_from_file("gui/executable_dlg.ui")
        self.builder.connect_signals(self)
        self.dialog = self.builder.get_object("dlg_exe_paths")

        for command, exe_path in exe_paths.items():
            try:
                self.builder.get_object(f"ed_{command}").set_text(exe_path)
            except AttributeError as err:
                # ToDo -> Log message!
                print(f"Failed to set exe path for command {command}")

    def show(self):
        self.dialog.run()

    def on_dlg_exe_paths_delete_event(self, dialog: Gtk.Dialog, event: Gdk.Event):
        self.dialog.hide()

    def on_btn_ok_clicked(self, button: Gtk.Button):
        for command in self.exe_paths.keys():
            self.exe_paths[command] = self.builder.get_object(f"ed_{command}").get_text()
        self.dialog.hide()

    def on_btn_cancel_clicked(self, button: Gtk.Button):
        self.on_dlg_exe_paths_delete_event(self.dialog, Gdk.EventType.DELETE)

    def on_btn_pdflatex_select_clicked(self, button: Gtk.Button):
        self.select_executable(Cmds.PDFLATEX, [""])

    def on_btn_xelatex_select_clicked(self, button: Gtk.Button):
        self.select_executable(Cmds.XELATEX, [""])

    def on_btn_lualatex_select_clicked(self, button: Gtk.Button):
        self.select_executable(Cmds.LUALATEX, [""])

    def on_btn_typst_select_clicked(self, button: Gtk.Button):
        self.select_executable(Cmds.TYPST, [""])

    def on_btn_inkscape_select_clicked(self, button: Gtk.Button):
        self.select_executable(Cmds.INKSCAPE, [""])

    def on_btn_dvisvgm_select_clicked(self, button: Gtk.Button):
        self.select_executable(Cmds.DVISVGM, [""])

    def on_btn_pdf2svg_select_clicked(self, button: Gtk.Button):
        self.select_executable(Cmds.PDF2SVG, [""])

    def on_rb_pdf2svg_inkscape_toggled(self, button: Gtk.RadioButton):
        pass

    def on_rb_pdf2svg_dvisvgm_toggled(self, button: Gtk.RadioButton):
        pass

    def on_rb_pdf2svg_pdf2svg_toggled(self, button: Gtk.RadioButton):
        pass

    def select_executable(self, command: str, check_strings: List[str]):
        entry: Gtk.Entry = self.builder.get_object(f"ed_{command}")
        exe_path = self.select_file(entry.get_text())

        if shutil.which(exe_path):
            entry.set_text(exe_path)
        else:
            dlg = Gtk.MessageDialog(transient_for=self.dialog,
                                    flags=0,
                                    message_type=Gtk.MessageType.WARNING,
                                    buttons=Gtk.ButtonsType.YES_NOL,
                                    text=f"The specified executable '{exe_path}' for the command '{command}' "
                                         f"is not a valid executable! Continue anyway?"
                                    )
            res = dlg.run()
            if res == Gtk.ResponseType.YES:
                entry.set_text(exe_path)

    def select_file(self, file_path: str) -> str:

        dlg = Gtk.FileChooserDialog(title="Select executable...",
                                    transient_for=self.dialog,
                                    action=Gtk.FileChooserAction.OPEN)
        dlg.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        if os.path.isfile(file_path):
            dlg.set_file(Gio.File.new_for_path(file_path))
        else:
            dlg.set_file(Gio.File.new_for_path("/"))

        # ToDo: Implement correct filtering for applications
        # exe_filter = Gtk.FileFilter()
        # exe_filter.set_name("Executables")
        # exe_filter.add_mime_type("application/x-binary")
        # exe_filter.add_pattern("*")
        # dlg.set_filter(exe_filter)

        response = dlg.run()
        new_filepath = file_path
        if response == Gtk.ResponseType.OK:
            new_filepath = dlg.get_filename()

        dlg.destroy()

        return new_filepath


class TexTextGuiBase:
    __metaclass__ = ABCMeta

    def __init__(self, version_str: str,  node_meta_data: TexTextEleMetaData, config: SettingsTexText,
                 svg_build_func, png_build_func):
        """

        :param (str) version_str: TexText version
        :param (TexTextEleMetaData) node_meta_data: The metadata of the node being processed
        :param (Settings) config: TexText configuration
        """
        self.textext_version = version_str
        self.meta_data = node_meta_data
        self.global_scale_factor = config.scale_factor
        self.global_pdf_font_size = config.font_size_pt
        self.config = config

        if node_meta_data.tex_command not in Cmds.ALL_TEX:
            node_meta_data.tex_command = Cmds.PDFLATEX

        self.svg_build_func = svg_build_func
        self.png_build_func = png_build_func

        self.window = None
        self.buffer_code = None
        self.buffer_preamble = None

    @abstractmethod
    def show(self):
        """
        Present the GUI for entering LaTeX code and setting some options
        """

    @abstractmethod
    def show_error_dialog(self, dlg_title: str, message_text: str, exception: Exception = None):
        """ Displays a dialog with information about the occurred error
        :param dlg_title: The text shown in the title
        :param message_text: The user defined message text shown in the dialog
        :param exception: The exception which caused the error. The string representation of the
                          exception will be displayed additionally to message_text. If the exception
                          has stdout and/or stderr attributes these should be additionally
                          displayed in the dialog
        """


class TexTextGuiGTK3(TexTextGuiBase):

    def __init__(self, version_str,  node_meta_data, config, svg_build_func, png_build_func=None):
        super().__init__(version_str,  node_meta_data, config, svg_build_func, png_build_func)
        self.builder: Gtk.Builder = Gtk.Builder()
        self.builder.add_from_file("gui/textext_gui.ui")
        self.builder.connect_signals(self)

        self.window: Gtk.Window = self.builder.get_object("textext_gui")
        self.buffer_code: Gtk.TextBuffer = self.builder.get_object("tbf_texcode")
        self.textview_code: Gtk.TextView = self.builder.get_object("tev_texcode")
        self.buffer_preamble: Gtk.TextBuffer = self.builder.get_object("tbf_preamble")
        self.textview_preamble: Gtk.TextView = self.builder.get_object("tev_preamble")

    def show(self):

        # Command box
        widget = self.builder.get_object("cmb_cmd")
        widget.remove_all()
        for cmd in Cmds.ALL_TEX:
            widget.append_text(cmd)
        widget.set_active(Cmds.ALL_TEX.index(self.meta_data.tex_command))

        # Alignment box
        widget = self.builder.get_object("cmb_align")
        widget.set_active(Align.LABELS.index(self.meta_data.alignment))

        # Sizing box
        if self.meta_data.use_font_size:
            self.builder.get_object("rb_scale").set_active(True)
            self.builder.get_object("adj_scale").set_value(self.meta_data.scale_factor)

            self.builder.get_object("sbn_scale").set_sensitive(True)
            self.builder.get_object("btn_scale_reset").set_sensitive(True)
            self.builder.get_object("btn_scale_previous").set_sensitive(True)

            self.builder.get_object("sbn_fontsize").set_sensitive(False)
            self.builder.get_object("btn_fontsize_reset").set_sensitive(False)
            self.builder.get_object("btn_fontsize_previous").set_sensitive(False)
        else:
            self.builder.get_object("rb_fontsize").set_active(True)
            self.builder.get_object("adj_fontsize").set_value(self.meta_data.font_size_pt)

            self.builder.get_object("sbn_fontsize").set_sensitive(True)
            self.builder.get_object("btn_fontsize_reset").set_sensitive(True)
            self.builder.get_object("btn_fontsize_previous").set_sensitive(True)

            self.builder.get_object("sbn_scale").set_sensitive(False)
            self.builder.get_object("btn_scale_reset").set_sensitive(False)
            self.builder.get_object("btn_scale_previous").set_sensitive(False)

        # Code window & Preamble file
        self.buffer_code.set_text(self.meta_data.text)
        self.load_preamble_file(self.meta_data.preamble)
        self.set_monospace_font(self.config.gui_font_size)

        # View menu
        self.builder.get_object("mit_wordwrap").set_active(self.config.gui_word_wrap)
        self.builder.get_object("mit_line_numbers").set_active(self.config.gui_line_numbers)
        self.builder.get_object("mit_spaces").set_active(self.config.gui_insert_spaces)
        self.builder.get_object("mit_autoindent").set_active(self.config.gui_auto_indent)
        self.builder.get_object("mit_white_preview_bg").set_active(self.config.gui_preview_white_bg)
        widget = self.builder.get_object(f"mit_{self.config.gui_font_size}pt")
        if widget:
            widget.set_active(True)

        widget = self.builder.get_object(f"mit_tabw{self.config.gui_tab_width}")
        if widget:
            widget.set_active(True)

        # Settings menus
        widget = self.builder.get_object(f"mit_new_node_{self.config.gui_new_node_content}")
        if widget:
            widget.set_active(True)

        self.builder.get_object(f"mit_confirm_close").set_active(self.config.gui_confirm_close)

        widget = self.builder.get_object(f"mit_close_shortcut_{self.config.gui_close_shortcut}")
        if widget:
            widget.set_active(True)

        self.window.show()
        Gtk.main()

    def show_error_dialog(self, dlg_title: str, message_text: str, exception: Exception = None):

        def add_section(dlg: Gtk.Dialog, header: Union[str, None], text: str):
            """ Adds a section consisting of a header and a textview to a dialog

            :param dlg: The dialog to which the section is added
            :param header: The text written above the textview
            :param text: The text put into the textview
            :return:
            """

            text_view = Gtk.TextView()
            text_view.set_editable(False)
            text_view.set_left_margin(5)
            text_view.set_right_margin(5)
            text_view.set_wrap_mode(Gtk.WrapMode.WORD)
            text_view.get_buffer().set_text(text)
            text_view.show()

            scroll_window = Gtk.ScrolledWindow()
            scroll_window.set_policy(hscrollbar_policy=Gtk.PolicyType.NEVER,
                                     vscrollbar_policy=Gtk.PolicyType.ALWAYS)
            scroll_window.set_shadow_type(Gtk.ShadowType.IN)
            scroll_window.set_min_content_height(150)
            scroll_window.add(text_view)
            scroll_window.show()

            if header is None:
                dlg.vbox.pack_start(scroll_window, expand=True, fill=True, padding=5)
                return

            expander = Gtk.Expander()

            # noinspection PyUnusedLocal
            def expand_or_collapse(_):
                if expander.get_expanded():
                    desired_height = 20
                else:
                    desired_height = 150
                expander.set_size_request(width=-1, height=desired_height)

            expander.connect('activate', expand_or_collapse)
            expander.add(scroll_window)
            expander.show()

            expander.set_label(header)
            expander.set_use_markup(True)

            expander.set_size_request(width=20, height=-1)
            scroll_window.hide()

            dlg.vbox.pack_start(expander, expand=True, fill=True, padding=5)

        dialog = Gtk.Dialog(title=dlg_title, transient_for=self.window)
        dialog.set_default_size(width=450, height=-1)
        button = dialog.add_button(button_text=Gtk.STOCK_OK, response_id=Gtk.ResponseType.CLOSE)
        button.connect("clicked", lambda w, d=None: dialog.destroy())
        message_label = Gtk.Label()
        message_label.set_markup(f"<b>{message_text}</b>")
        message_label.set_justify(Gtk.Justification.LEFT)

        raw_output_box = Gtk.VBox()

        dialog.vbox.pack_start(message_label, expand=False, fill=True, padding=5)

        if exception:
            add_section(dlg=dialog, header="Detailed error information", text=str(exception))
            dialog.vbox.pack_start(raw_output_box, expand=False, fill=True, padding=5)

            if hasattr(exception, "stdout") and exception.stdout:
                add_section(dlg=dialog, header="Stdout: <small><i>(click to expand)</i></small>",
                            text=exception.stdout)
            if hasattr(exception, "stderr") and exception.stderr:
                add_section(dlg=dialog, header="Stderr: <small><i>(click to expand)</i></small>",
                            text=exception.stderr)

        dialog.show_all()
        dialog.run()

    def set_monospace_font(self, font_size: int):
        """ Sets the font of the text views to monospace

        What an effort to simply set the font size. Gtk is sometimes ridiculous.

        :param font_size: The desired  font size in the text views
        """

        # I do not want to rely on hard coded widget names taken from glade here
        # It is enough error-prone to hard code the ids...
        code_view_name = self.builder.get_object("tev_texcode").get_name()
        preamble_view_name = self.builder.get_object("tev_preamble_file").get_name()

        css_style = f"""
            #{code_view_name} {{
                font: {font_size}pt "Monospace";
            }}
            #{preamble_view_name} {{
                font: {font_size}pt "Monospace";
            }}
        """

        css_provider: Gtk.CssProvider = Gtk.CssProvider()
        css_provider.load_from_data(css_style.encode())
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(),
                                                 css_provider,
                                                 Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def load_preamble_file(self, filepath: str):
        """
        Loads the content of the preamble file into the corresponding text buffer. Also
        sets the path to the preamble file in the edit field.

        :param filepath: The path to the preamble file
        """
        try:
            with open(filepath, mode="r", errors="ignore") as fh:
                content = fh.read()
            self.buffer_preamble.set_text(content)
            self.builder.get_object("ed_preamble_filepath").set_text(filepath)
        except OSError as err:
            self.show_error_dialog("Preamble file not found",
                                   f"Cannot load the specified preamble file '{filepath}'\n\n "
                                   f"Please select or create a preamble file in the Preamble-File tab!",
                                   err)

    @staticmethod
    def on_win_main_destroy(widget):
        Gtk.main_quit()

    def on_btn_execute_clicked(self, btn_execute: Gtk.Button):
        pass

    def on_btn_preview_clicked(self, btn_preview: Gtk.Button):
        pass

    def on_btn_cancel_clicked(self, btn_cancel: Gtk.Button):
        self.on_win_main_destroy(btn_cancel)

    def on_btn_scale_reset_clicked(self, btn_scale_reset: Gtk.Button):
        pass

    def on_btn_scale_previous_clicked(self, btn_scale_previous: Gtk.Button):
        pass

    def on_btn_fontsize_reset_clicked(self, btn_fontsize_reset: Gtk.Button):
        pass

    def on_btn_fontsize_previous_clicked(self, btn_fontsize_previous: Gtk.Button):
        pass

    def on_btn_preamble_open_clicked(self, btn_preamble_open: Gtk.Button):
        pass

    def on_btn_preamble_saveas_clicked(self, btn_preamble_saveas: Gtk.Button):
        pass

    def on_btn_preamble_save_clicked(self, btn_preamble_save: Gtk.Button):
        pass

    def on_mit_wordwrap_toggled(self, mit_wordwrap: Gtk.CheckMenuItem):
        self.config.gui_word_wrap = mit_wordwrap.get_active()
        self.textview_code.set_wrap_mode(Gtk.WrapMode.WORD if self.config.gui_word_wrap else Gtk.WrapMode.NONE)

    def on_mit_line_numbers_toggled(self, mit_line_numbers: Gtk.CheckMenuItem):
        self.config.gui_line_numbers = mit_line_numbers.get_active()
        # ToDo Insert GTKSourceView Code here for line numbering

    def on_mit_spaces_toggled(self, mit_spaces: Gtk.CheckMenuItem):
        self.config.gui_insert_spaces = mit_spaces.get_active()
        # ToDo Insert GTKSourceView Code here for spaces

    def on_mit_white_preview_bg_toggled(self, mit_white_preview_bg: Gtk.CheckMenuItem):
        self.config.gui_preview_white_bg = mit_white_preview_bg.get_active()

    def on_mit_exepaths_activate(self, widget):
        exe_paths = dict()
        for command in Cmds.ALL:
            exe_paths[command] = self.config.get_executable(command)

        dlg = DlgExePaths(exe_paths)
        dlg.show()
