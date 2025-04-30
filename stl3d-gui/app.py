"""
Hauptklasse der STL3D-Anwendung
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from resources.styles import COLORS
from utils.gui_utils import RedirectText, create_button
from utils.file_utils import setup_drag_drop
from ui.image_to_stl_tab import ImageToSTLTab
from ui.contour_crafting_tab import ContourCraftingTab
from ui.topographic_tab import TopographicTab
from ui.stl_repair_tab import STLRepairTab

# Plattformspezifische Importe
if sys.platform == 'darwin':  # macOS
    from utils.mac_compatibility import setup_mac_drag_drop, setup_mac_menu


class STL3DApp:
    """Hauptklasse für die 3D-Modellierungsanwendung"""

    def __init__(self):
        """Initialisiert die Anwendung"""
        self.root = tk.Tk()
        self.root.title("3D-Modellierung aus Bildern")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)

        # Überprüfe, ob die Ausgabeverzeichnisse existieren
        self.check_output_dirs()

        # Status-Variable
        self.status_var = tk.StringVar()
        self.status_var.set("Bereit")

        # Themenstil anwenden
        self.apply_theme()

        # UI-Elemente erstellen
        self.create_menu()
        self.create_widgets()

        # Drag & Drop aktivieren
        self.setup_drag_drop()

        # macOS-spezifische Konfiguration
        if sys.platform == 'darwin':
            setup_mac_drag_drop(self.root)
            setup_mac_menu(self.root)

    def check_output_dirs(self):
        """Erstellt die benötigten Ausgabeverzeichnisse, falls sie nicht existieren"""
        output_base = "output"
        if not os.path.exists(output_base):
            os.makedirs(output_base, exist_ok=True)

        # Verzeichnisse für jedes Modul
        module_dirs = [
            "image-to-stl",
            "contour-crafting",
            "topographic-layering",
            "stl-repair"
        ]

        for module_dir in module_dirs:
            dir_path = os.path.join(output_base, module_dir)
            if not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)

    def apply_theme(self):
        """Wendet das Material Design-Thema auf die Anwendung an"""
        # Konfiguriere einen ttk-Stil
        style = ttk.Style()

        # Fallback: Wenn verfügbar, verwende clam als Basis (funktioniert gut für dunkle Themen)
        if 'clam' in style.theme_names():
            style.theme_use('clam')

        # Konfiguriere allgemeine Stile
        style.configure('TFrame', background=COLORS["bg"])
        style.configure('TLabel', background=COLORS["bg"], foreground=COLORS["text"])
        style.configure('TButton', background=COLORS["button_bg"], foreground=COLORS["button_text"])
        style.configure('TNotebook', background=COLORS["bg"], tabmargins=[2, 5, 2, 0])
        style.configure('TNotebook.Tab', background=COLORS["primary"], foreground=COLORS["text"],
                        padding=[10, 2], font=('Arial', 10, 'bold'))
        style.map('TNotebook.Tab', background=[('selected', COLORS["accent"])],
                  foreground=[('selected', COLORS["text"])])
        style.configure('TCheckbutton', background=COLORS["bg"], foreground=COLORS["text"])
        style.configure('TRadiobutton', background=COLORS["bg"], foreground=COLORS["text"])
        style.configure('TLabelframe', background=COLORS["bg"], foreground=COLORS["text"])
        style.configure('TLabelframe.Label', background=COLORS["bg"], foreground=COLORS["text"])

        # Konfiguriere die Farben für die Anwendung
        self.root.configure(background=COLORS["bg"])

    def create_menu(self):
        """Erstellt die Menüleiste"""
        menu_bar = tk.Menu(self.root)

        # Datei-Menü
        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="Öffnen...", command=self.open_file)
        file_menu.add_separator()
        file_menu.add_command(label="Ausgabeverzeichnis öffnen", command=self.open_output_dir)
        file_menu.add_separator()
        file_menu.add_command(label="Beenden", command=self.root.quit)

        # Hilfe-Menü
        help_menu = tk.Menu(menu_bar, tearoff=0)
        help_menu.add_command(label="Über", command=self.show_about)

        # Menüs zur Menüleiste hinzufügen
        menu_bar.add_cascade(label="Datei", menu=file_menu)
        menu_bar.add_cascade(label="Hilfe", menu=help_menu)

        # Menüleiste anzeigen
        self.root.config(menu=menu_bar)

    def create_widgets(self):
        """Erstellt die UI-Elemente"""
        # Hauptframe
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Notebook für Tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Log-Umleitung konfigurieren
        self.log_redirect = None

        # Tabs erstellen
        self.create_tabs()

        # Status-Leiste
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W,
                               background=COLORS["primary"], foreground=COLORS["text"])
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def create_tabs(self):
        """Erstellt die Tabs für die verschiedenen Module"""
        # Image to STL Tab
        image_to_stl_tab = ttk.Frame(self.notebook)
        self.notebook.add(image_to_stl_tab, text="Bild zu STL")

        # Contour Crafting Tab
        contour_tab = ttk.Frame(self.notebook)
        self.notebook.add(contour_tab, text="Höhenlinien")

        # Topographic Layering Tab
        topo_tab = ttk.Frame(self.notebook)
        self.notebook.add(topo_tab, text="Topografisch")

        # STL Repair Tab
        repair_tab = ttk.Frame(self.notebook)
        self.notebook.add(repair_tab, text="STL-Reparatur")

        # Log-Umleitung für alle Tabs
        log_widget = None

        # Initialisiere die Tab-Module
        self.image_to_stl = ImageToSTLTab(image_to_stl_tab, self.status_var, self.log_redirect)
        self.contour_crafting = ContourCraftingTab(contour_tab, self.status_var, self.log_redirect)
        self.topographic = TopographicTab(topo_tab, self.status_var, self.log_redirect)
        self.stl_repair = STLRepairTab(repair_tab, self.status_var, self.log_redirect)

        # Verwende das erste Log-Widget für Umleitung
        log_widget = self.image_to_stl.log_text
        self.log_redirect = RedirectText(log_widget)
        sys.stdout = self.log_redirect

        # Tab-Wechsel-Handler, um das Log-Widget zu aktualisieren
        def on_tab_change(event):
            tab_idx = self.notebook.index("current")
            if tab_idx == 0:  # Image to STL
                sys.stdout = RedirectText(self.image_to_stl.log_text)
            elif tab_idx == 1:  # Contour Crafting
                sys.stdout = RedirectText(self.contour_crafting.log_text)
            elif tab_idx == 2:  # Topographic
                sys.stdout = RedirectText(self.topographic.log_text)
            elif tab_idx == 3:  # STL Repair
                sys.stdout = RedirectText(self.stl_repair.log_text)

        self.notebook.bind("<<NotebookTabChanged>>", on_tab_change)

    def setup_drag_drop(self):
        """Richtet Drag & Drop für die Anwendung ein"""

        def handle_drop(files):
            if not files:
                return

            # Erster gedropter Dateiname
            file_path = files[0]

            # Bestimme Dateityp und wähle entsprechenden Tab
            filename, extension = os.path.splitext(file_path.lower())

            if extension in ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff']:
                # Bild
                tab_idx = 0  # Image to STL
                self.notebook.select(tab_idx)

                # Aktualisiere Eingabefeld
                self.image_to_stl.input_entry.delete(0, tk.END)
                self.image_to_stl.input_entry.insert(0, file_path)

                # Schlage Ausgabedatei vor
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                output_file = f"{base_name}.stl"
                self.image_to_stl.output_entry.delete(0, tk.END)
                self.image_to_stl.output_entry.insert(0, output_file)

            elif extension == '.stl':
                # STL-Datei
                tab_idx = 3  # STL Repair
                self.notebook.select(tab_idx)

                # Aktualisiere Eingabefeld
                self.stl_repair.input_entry.delete(0, tk.END)
                self.stl_repair.input_entry.insert(0, file_path)

                # Schlage Ausgabedatei vor
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                output_file = f"{base_name}_repaired.stl"
                self.stl_repair.output_entry.delete(0, tk.END)
                self.stl_repair.output_entry.insert(0, output_file)

            self.status_var.set(f"Datei geladen: {file_path}")

        # Drag & Drop für das Hauptfenster einrichten
        setup_drag_drop(self.root, handle_drop)

        # Für macOS: Behandlung der AppleEvents
        if sys.platform == 'darwin':
            def handle_mac_file_dropped(event):
                if hasattr(event, 'data'):
                    files = event.data.split("\n")
                    handle_drop(files)

            self.root.bind('<<MacFileDropped>>', handle_mac_file_dropped)

    def open_file(self):
        """Öffnet eine Datei über einen Dateiauswahldialog"""
        filetypes = [
            ("Unterstützte Dateien", "*.jpg *.jpeg *.png *.bmp *.gif *.tiff *.stl"),
            ("Bilddateien", "*.jpg *.jpeg *.png *.bmp *.gif *.tiff"),
            ("STL-Dateien", "*.stl"),
            ("Alle Dateien", "*.*")
        ]
        filename = filedialog.askopenfilename(filetypes=filetypes)
        if filename:
            # Datei wurde ausgewählt, fingieren eines Drag & Drop-Events
            self.status_var.set("Datei wird geladen...")
            # Verarbeite die Datei wie ein Drop-Event
            filename_ext = os.path.splitext(filename.lower())[1]
            if filename_ext in ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.stl']:
                self.setup_drag_drop()  # Stelle sicher, dass Drag & Drop eingerichtet ist
                # Fingiere ein Drag & Drop mit dem ausgewählten Dateinamen
                filename, extension = os.path.splitext(filename.lower())

                if extension in ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff']:
                    # Bild
                    tab_idx = 0  # Image to STL
                    self.notebook.select(tab_idx)

                    # Aktualisiere Eingabefeld
                    self.image_to_stl.input_entry.delete(0, tk.END)
                    self.image_to_stl.input_entry.insert(0, filename + extension)

                    # Schlage Ausgabedatei vor
                    base_name = os.path.splitext(os.path.basename(filename + extension))[0]
                    output_file = f"{base_name}.stl"
                    self.image_to_stl.output_entry.delete(0, tk.END)
                    self.image_to_stl.output_entry.insert(0, output_file)

                elif extension == '.stl':
                    # STL-Datei
                    tab_idx = 3  # STL Repair
                    self.notebook.select(tab_idx)

                    # Aktualisiere Eingabefeld
                    self.stl_repair.input_entry.delete(0, tk.END)
                    self.stl_repair.input_entry.insert(0, filename + extension)

                    # Schlage Ausgabedatei vor
                    base_name = os.path.splitext(os.path.basename(filename + extension))[0]
                    output_file = f"{base_name}_repaired.stl"
                    self.stl_repair.output_entry.delete(0, tk.END)
                    self.stl_repair.output_entry.insert(0, output_file)

                self.status_var.set(f"Datei geladen: {filename + extension}")

    def open_output_dir(self):
        """Öffnet das Ausgabeverzeichnis im Dateimanager"""
        output_dir = os.path.abspath("output")

        try:
            # Plattformunabhängig den Dateimanager öffnen
            if sys.platform == 'darwin':  # macOS
                os.system(f'open "{output_dir}"')
            elif sys.platform == 'win32':  # Windows
                os.system(f'explorer "{output_dir}"')
            else:  # Linux und andere
                try:
                    os.system(f'xdg-open "{output_dir}"')
                except:
                    # Fallback für Linux-Systeme ohne xdg-open
                    try:
                        os.system(f'nautilus "{output_dir}"')  # GNOME
                    except:
                        os.system(f'thunar "{output_dir}"')  # XFCE

            self.status_var.set(f"Ausgabeverzeichnis geöffnet: {output_dir}")
        except Exception as e:
            self.status_var.set(f"Fehler beim Öffnen des Ausgabeverzeichnisses: {str(e)}")
            print(f"Hinweis: Das Ausgabeverzeichnis befindet sich unter: {output_dir}")

    def show_about(self):
        """Zeigt Informationen über die Anwendung an"""
        about_text = """3D-Modellierung aus Bildern

Eine Sammlung von Python-Werkzeugen zur Umwandlung von Bildern
in 3D-Modelle für den 3D-Druck.

Entwickelt von: Martin Pfeffer

Version: 1.0
Lizenz: MIT License
"""
        messagebox.showinfo("Über 3D-Modellierung aus Bildern", about_text)

    def run(self):
        """Startet die Anwendung"""
        self.root.mainloop()