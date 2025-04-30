"""
UI-Komponente für den Image-to-STL Tab
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog
from resources.styles import COLORS
from utils.gui_utils import create_button, create_labeled_entry, create_log_area
from modules.image_to_stl import image_to_stl

class ImageToSTLTab:
    """Tab für die Konvertierung von Bildern in STL-Dateien"""

    def __init__(self, parent, status_var, log_redirect):
        """
        Initialisiert den Tab für die Bildkonvertierung.

        Args:
            parent: Das übergeordnete Widget (der Tab)
            status_var: StringVar für die Statusleiste
            log_redirect: RedirectText-Objekt für die Ausgabeumleitung
        """
        self.parent = parent
        self.status_var = status_var
        self.log_redirect = log_redirect

        self.input_file = ""
        self.output_file = ""

        # Variablen für UI-Elemente
        self.max_height_var = tk.DoubleVar(value=5.0)
        self.base_height_var = tk.DoubleVar(value=1.0)
        self.invert_var = tk.BooleanVar(value=False)
        self.smooth_var = tk.IntVar(value=1)
        self.threshold_var = tk.StringVar(value="")  # Leer = kein Schwellenwert
        self.border_var = tk.IntVar(value=2)
        self.max_size_var = tk.IntVar(value=170)
        self.object_only_var = tk.BooleanVar(value=False)
        self.timestamp_var = tk.BooleanVar(value=True)
        self.rotate_x_var = tk.BooleanVar(value=False)
        self.rotate_y_var = tk.BooleanVar(value=False)
        self.rotate_z_var = tk.BooleanVar(value=False)

        self.create_widgets()

    def create_widgets(self):
        """Erstellt die UI-Elemente"""
        # Hauptframe
        main_frame = ttk.Frame(self.parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Dateieingabe-Frame
        file_frame = ttk.Frame(main_frame)
        file_frame.pack(fill=tk.X, pady=10)

        # Input-Datei
        input_label = ttk.Label(file_frame, text="Eingabe-Bild:")
        input_label.grid(row=0, column=0, sticky=tk.W, pady=5)

        self.input_entry = ttk.Entry(file_frame, width=50)
        self.input_entry.grid(row=0, column=1, sticky=tk.EW, padx=5)

        browse_btn = create_button(file_frame, text="Durchsuchen", command=self.browse_input)
        browse_btn.grid(row=0, column=2, padx=5)

        # Output-Datei
        output_label = ttk.Label(file_frame, text="Ausgabe-STL:")
        output_label.grid(row=1, column=0, sticky=tk.W, pady=5)

        self.output_entry = ttk.Entry(file_frame, width=50)
        self.output_entry.grid(row=1, column=1, sticky=tk.EW, padx=5)

        browse_out_btn = create_button(file_frame, text="Durchsuchen", command=self.browse_output)
        browse_out_btn.grid(row=1, column=2, padx=5)

        file_frame.columnconfigure(1, weight=1)

        # Parameter-Frame
        param_frame = ttk.LabelFrame(main_frame, text="Parameter")
        param_frame.pack(fill=tk.X, pady=10)

        # Allgemeine Parameter
        general_frame = ttk.Frame(param_frame)
        general_frame.pack(fill=tk.X, padx=10, pady=5)

        # Zeile 1: Maximale Höhe, Basishöhe
        max_height_frame = create_labeled_entry(general_frame, "Max. Höhe (mm):", self.max_height_var, width=8)
        max_height_frame.grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)

        base_height_frame = create_labeled_entry(general_frame, "Basis-Höhe (mm):", self.base_height_var, width=8)
        base_height_frame.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)

        # Zeile 2: Glättung, Schwellenwert
        smooth_frame = create_labeled_entry(general_frame, "Glättung:", self.smooth_var, width=8)
        smooth_frame.grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)

        threshold_frame = create_labeled_entry(general_frame, "Schwellenwert (0-255, leer = keiner):",
                                              self.threshold_var, width=8)
        threshold_frame.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)

        # Zeile 3: Rand, Max. Größe
        border_frame = create_labeled_entry(general_frame, "Rand (Pixel):", self.border_var, width=8)
        border_frame.grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)

        max_size_frame = create_labeled_entry(general_frame, "Max. Größe (mm):", self.max_size_var, width=8)
        max_size_frame.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)

        # Checkboxen - Allgemeine Optionen
        checkbox_frame = ttk.Frame(param_frame)
        checkbox_frame.pack(fill=tk.X, padx=10, pady=5)

        invert_check = ttk.Checkbutton(checkbox_frame, text="Bild invertieren", variable=self.invert_var)
        invert_check.pack(side=tk.LEFT, padx=5)

        object_only_check = ttk.Checkbutton(checkbox_frame, text="Nur Objekt (ohne Grundplatte)",
                                           variable=self.object_only_var)
        object_only_check.pack(side=tk.LEFT, padx=5)

        timestamp_check = ttk.Checkbutton(checkbox_frame, text="Zeitstempel hinzufügen",
                                         variable=self.timestamp_var)
        timestamp_check.pack(side=tk.LEFT, padx=5)

        # Checkboxen - Rotation
        rotation_frame = ttk.LabelFrame(param_frame, text="Rotation (90°)")
        rotation_frame.pack(fill=tk.X, padx=10, pady=5)

        rotation_inner_frame = ttk.Frame(rotation_frame)
        rotation_inner_frame.pack(fill=tk.X, padx=10, pady=5)

        rotate_x_check = ttk.Checkbutton(rotation_inner_frame, text="X-Achse",
                                        variable=self.rotate_x_var)
        rotate_x_check.pack(side=tk.LEFT, padx=10)

        rotate_y_check = ttk.Checkbutton(rotation_inner_frame, text="Y-Achse",
                                        variable=self.rotate_y_var)
        rotate_y_check.pack(side=tk.LEFT, padx=10)

        rotate_z_check = ttk.Checkbutton(rotation_inner_frame, text="Z-Achse",
                                        variable=self.rotate_z_var)
        rotate_z_check.pack(side=tk.LEFT, padx=10)

        # Button-Frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)

        convert_btn = create_button(button_frame, text="Bild in STL konvertieren",
                                   command=self.convert_image)
        convert_btn.pack(side=tk.LEFT, padx=5)

        # Log-Bereich
        log_frame, self.log_text = create_log_area(main_frame)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)

    def browse_input(self):
        """Öffnet einen Dateiauswahldialog für die Eingabedatei"""
        filetypes = [
            ("Bilddateien", "*.jpg *.jpeg *.png *.bmp *.gif *.tiff"),
            ("JPEG", "*.jpg *.jpeg"),
            ("PNG", "*.png"),
            ("Alle Dateien", "*.*")
        ]
        filename = filedialog.askopenfilename(filetypes=filetypes)
        if filename:
            self.input_file = filename
            self.input_entry.delete(0, tk.END)
            self.input_entry.insert(0, filename)

            # Schlage Ausgabedatei vor
            if not self.output_entry.get():
                base_name = os.path.splitext(os.path.basename(filename))[0]
                output_file = f"{base_name}.stl"
                self.output_entry.delete(0, tk.END)
                self.output_entry.insert(0, output_file)

    def browse_output(self):
        """Öffnet einen Dateiauswahldialog für die Ausgabedatei"""
        filetypes = [
            ("STL-Dateien", "*.stl"),
            ("Alle Dateien", "*.*")
        ]
        filename = filedialog.asksaveasfilename(defaultextension=".stl", filetypes=filetypes)
        if filename:
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, filename)

    def convert_image(self):
        """Konvertiert das Bild in eine STL-Datei"""
        input_file = self.input_entry.get()
        output_file = self.output_entry.get()

        if not input_file:
            self.status_var.set("Fehler: Keine Eingabedatei ausgewählt")
            return

        if not output_file:
            self.status_var.set("Fehler: Keine Ausgabedatei angegeben")
            return

        try:
            # Parameter aus den UI-Elementen holen
            max_height = self.max_height_var.get()
            base_height = self.base_height_var.get()
            invert = self.invert_var.get()
            smooth = self.smooth_var.get()

            # Threshold kann leer sein (= None)
            threshold_str = self.threshold_var.get()
            threshold = None if not threshold_str.strip() else int(threshold_str)

            # Numerische Parameter: Validieren und Fehlermeldungen anzeigen
            try:
                border = self.border_var.get()
            except Exception:
                self.status_var.set("Fehler: Ungültiger Wert für Randbreite. Bitte geben Sie eine Zahl ein.")
                return

            try:
                max_size = self.max_size_var.get()
            except Exception:
                self.status_var.set("Fehler: Ungültiger Wert für Max. Größe. Bitte geben Sie eine Zahl ein.")
                return

            object_only = self.object_only_var.get()
            use_timestamp = self.timestamp_var.get()

            # Rotationen
            rotate_x = self.rotate_x_var.get()
            rotate_y = self.rotate_y_var.get()
            rotate_z = self.rotate_z_var.get()

            # Status aktualisieren
            self.status_var.set("Konvertiere Bild zu STL...")

            # Log-Bereich leeren
            self.log_text.configure(state="normal")
            self.log_text.delete(1.0, tk.END)
            self.log_text.configure(state="disabled")

            # Alle Parameter in ein Dictionary packen, um sie einfacher zu übergeben
            params = {
                'input_file': input_file,
                'output_file': output_file,
                'max_height': max_height,
                'base_height': base_height,
                'invert': invert,
                'smooth': smooth,
                'threshold': threshold,
                'border': border,
                'max_size': max_size,
                'object_only': object_only,
                'use_timestamp': use_timestamp,
                'rotate_x': rotate_x,
                'rotate_y': rotate_y,
                'rotate_z': rotate_z
            }

            # Konvertierung in einem separaten Thread starten - DIREKT IMPLEMENTIERT
            import threading
            thread = threading.Thread(target=self._run_conversion_wrapper, args=(params,))
            thread.daemon = True  # Daemon-Eigenschaft MUSS vor dem Start gesetzt werden
            thread.start()

        except Exception as e:
            import traceback
            error_msg = f"Fehler bei der Eingabevalidierung: {str(e)}"
            self.status_var.set(error_msg)
            self.log_text.configure(state="normal")
            self.log_text.insert(tk.END, f"{error_msg}\n{traceback.format_exc()}")
            self.log_text.configure(state="disabled")

    def _run_conversion_wrapper(self, params):
        """
        Wrapper für _run_conversion, der die Parameter aus einem Dictionary nimmt.
        Dies vereinfacht den Thread-Start und verhindert Probleme mit der Reihenfolge.
        """
        try:
            # Parameter aus dem Dictionary extrahieren
            self._run_conversion(
                params['input_file'],
                params['output_file'],
                params['max_height'],
                params['base_height'],
                params['invert'],
                params['smooth'],
                params['threshold'],
                params['border'],
                params['max_size'],
                params['object_only'],
                params['use_timestamp'],
                params['rotate_x'],
                params['rotate_y'],
                params['rotate_z']
            )
        except Exception as e:
            import traceback
            error_msg = f"Fehler bei der Konvertierung: {str(e)}"
            print(error_msg)
            print(traceback.format_exc())

    def _run_conversion(self, input_file, output_file, max_height, base_height, invert,
                       smooth, threshold, border, max_size, object_only, use_timestamp,
                       rotate_x, rotate_y, rotate_z):
        """
        Führt die Konvertierung in einem separaten Thread aus.

        Args:
            Alle Parameter werden von convert_image() übergeben
        """
        try:
            # Konvertierung durchführen
            print(f"Konvertiere {input_file} zu STL...")
            print(f"Parameter: max_height={max_height}, base_height={base_height}, invert={invert}")
            print(f"smooth={smooth}, threshold={threshold}, border={border}")
            print(f"max_size={max_size}, object_only={object_only}")
            print(f"Rotation: X={rotate_x}, Y={rotate_y}, Z={rotate_z}")

            result_path = image_to_stl(
                input_file, output_file, width=None, height=None,
                max_height=max_height, base_height=base_height, invert=invert,
                smooth=smooth, threshold=threshold, border=border, max_size=max_size,
                object_only=object_only, rotate_x=rotate_x, rotate_y=rotate_y, rotate_z=rotate_z
            )
            
            # Status aktualisieren
            self.status_var.set(f"Konvertierung abgeschlossen: {result_path}")
            
        except Exception as e:
            print(f"Fehler bei der Konvertierung: {str(e)}")
            self.status_var.set("Fehler bei der Konvertierung")