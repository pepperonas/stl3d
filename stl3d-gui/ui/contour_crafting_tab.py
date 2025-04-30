"""
UI-Komponente für den Contour-Crafting Tab
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog
from resources.styles import COLORS
from utils.gui_utils import create_button, create_labeled_entry, create_log_area
from modules.contour_crafting import contour_crafting_process

class ContourCraftingTab:
    """Tab für die Erstellung von 3D-Modellen aus Bildern mittels Höhenlinien"""
    
    def __init__(self, parent, status_var, log_redirect):
        """
        Initialisiert den Tab für das Contour Crafting.
        
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
        self.num_contours_var = tk.IntVar(value=10)
        self.extrusion_height_var = tk.DoubleVar(value=1.0)
        self.base_height_var = tk.DoubleVar(value=0.5)
        self.smoothing_var = tk.DoubleVar(value=1.0)
        self.invert_var = tk.BooleanVar(value=False)
        self.photo_mode_var = tk.BooleanVar(value=False)
        self.timestamp_var = tk.BooleanVar(value=True)
        
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
        
        # Zeile 1: Anzahl Konturen, Extrusionshöhe
        num_contours_frame = create_labeled_entry(general_frame, "Anzahl Konturen:", 
                                                 self.num_contours_var, width=8)
        num_contours_frame.grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        
        extrusion_height_frame = create_labeled_entry(general_frame, "Extrusionshöhe (mm):", 
                                                     self.extrusion_height_var, width=8)
        extrusion_height_frame.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        # Zeile 2: Basishöhe, Glättung
        base_height_frame = create_labeled_entry(general_frame, "Basis-Höhe (mm):", 
                                               self.base_height_var, width=8)
        base_height_frame.grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        
        smoothing_frame = create_labeled_entry(general_frame, "Glättung:", 
                                              self.smoothing_var, width=8)
        smoothing_frame.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        
        # Checkboxen
        checkbox_frame = ttk.Frame(param_frame)
        checkbox_frame.pack(fill=tk.X, padx=10, pady=5)
        
        invert_check = ttk.Checkbutton(checkbox_frame, text="Bild invertieren", 
                                      variable=self.invert_var)
        invert_check.pack(side=tk.LEFT, padx=5)
        
        photo_mode_check = ttk.Checkbutton(checkbox_frame, text="Foto-Modus (für realistische Fotos)", 
                                          variable=self.photo_mode_var)
        photo_mode_check.pack(side=tk.LEFT, padx=5)
        
        timestamp_check = ttk.Checkbutton(checkbox_frame, text="Zeitstempel hinzufügen", 
                                         variable=self.timestamp_var)
        timestamp_check.pack(side=tk.LEFT, padx=5)
        
        # Button-Frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        convert_btn = create_button(button_frame, text="Höhenlinien-Modell erstellen", 
                                   command=self.create_contour_model)
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
                output_file = f"{base_name}_contour.stl"
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
    
    def create_contour_model(self):
        """Erstellt ein 3D-Modell aus Höhenlinien des Bildes"""
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
            num_contours = self.num_contours_var.get()
            extrusion_height = self.extrusion_height_var.get()
            base_height = self.base_height_var.get()
            smoothing = self.smoothing_var.get()
            invert = self.invert_var.get()
            photo_mode = self.photo_mode_var.get()
            use_timestamp = self.timestamp_var.get()
            
            # Status aktualisieren
            self.status_var.set("Erstelle 3D-Modell aus Höhenlinien...")
            
            # Log-Bereich leeren
            self.log_text.configure(state="normal")
            self.log_text.delete(1.0, tk.END)
            self.log_text.configure(state="disabled")
            
            # Alle Parameter in ein Dictionary packen
            params = {
                'input_file': input_file,
                'output_file': output_file,
                'num_contours': num_contours,
                'extrusion_height': extrusion_height,
                'base_height': base_height,
                'smoothing': smoothing,
                'invert': invert,
                'photo_mode': photo_mode,
                'use_timestamp': use_timestamp
            }

            # Verarbeitung in einem separaten Thread starten - DIREKT IMPLEMENTIERT
            import threading
            thread = threading.Thread(target=self._run_contour_crafting_wrapper, args=(params,))
            thread.daemon = True
            thread.start()

        except Exception as e:
            import traceback
            error_msg = f"Fehler bei der Eingabevalidierung: {str(e)}"
            self.status_var.set(error_msg)
            self.log_text.configure(state="normal")
            self.log_text.insert(tk.END, f"{error_msg}\n{traceback.format_exc()}")
            self.log_text.configure(state="disabled")

    def _run_contour_crafting_wrapper(self, params):
        """
        Wrapper für _run_contour_crafting, der die Parameter aus einem Dictionary nimmt.
        """
        try:
            # Parameter aus dem Dictionary extrahieren
            self._run_contour_crafting(
                params['input_file'],
                params['output_file'],
                params['num_contours'],
                params['extrusion_height'],
                params['base_height'],
                params['smoothing'],
                params['invert'],
                params['photo_mode'],
                params['use_timestamp']
            )
        except Exception as e:
            import traceback
            error_msg = f"Fehler bei der Höhenlinien-Verarbeitung: {str(e)}"
            print(error_msg)
            print(traceback.format_exc())

    def _run_contour_crafting(self, input_file, output_file, num_contours, extrusion_height,
                            base_height, smoothing, invert, photo_mode, use_timestamp):
        """
        Führt das Contour Crafting in einem separaten Thread aus.

        Args:
            Alle Parameter werden von create_contour_model() übergeben
        """
        try:
            # Verarbeitung durchführen
            print(f"Verarbeite {input_file} mit Contour Crafting...")
            print(f"Parameter: num_contours={num_contours}, extrusion_height={extrusion_height}")
            print(f"base_height={base_height}, smoothing={smoothing}")
            print(f"invert={invert}, photo_mode={photo_mode}")

            result_path = contour_crafting_process(
                input_file, output_file, num_contours, extrusion_height,
                base_height, smoothing, invert, photo_mode, use_timestamp
            )

            # Status aktualisieren
            self.status_var.set(f"Contour Crafting abgeschlossen: {result_path}")

        except Exception as e:
            print(f"Fehler beim Contour Crafting: {str(e)}")
            self.status_var.set("Fehler beim Contour Crafting")