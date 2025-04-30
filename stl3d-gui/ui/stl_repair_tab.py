"""
UI-Komponente für den STL-Repair Tab
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog
from resources.styles import COLORS
from utils.gui_utils import create_button, create_labeled_entry, create_log_area
from modules.stl_repair import fix_stl, validate_stl

class STLRepairTab:
    """Tab für die Reparatur von STL-Dateien"""
    
    def __init__(self, parent, status_var, log_redirect):
        """
        Initialisiert den Tab für die STL-Reparatur.
        
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
        self.verbose_var = tk.BooleanVar(value=True)
        self.aggressive_var = tk.BooleanVar(value=True)
        self.clean_var = tk.BooleanVar(value=True)
        self.iterations_var = tk.IntVar(value=2)
        self.timeout_var = tk.IntVar(value=30)
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
        input_label = ttk.Label(file_frame, text="Eingabe-STL:")
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
        param_frame = ttk.LabelFrame(main_frame, text="Reparatur-Optionen")
        param_frame.pack(fill=tk.X, pady=10)
        
        # Allgemeine Parameter
        general_frame = ttk.Frame(param_frame)
        general_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Zeile 1: Iterations, Timeout
        iterations_frame = create_labeled_entry(general_frame, "Max. Iterationen:", 
                                              self.iterations_var, width=5)
        iterations_frame.pack(side=tk.LEFT, padx=5, pady=5)
        
        timeout_frame = create_labeled_entry(general_frame, "Timeout (Sek.):", 
                                            self.timeout_var, width=5)
        timeout_frame.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Checkboxen
        checkbox_frame = ttk.Frame(param_frame)
        checkbox_frame.pack(fill=tk.X, padx=10, pady=5)
        
        verbose_check = ttk.Checkbutton(checkbox_frame, text="Ausführliche Ausgabe", 
                                       variable=self.verbose_var)
        verbose_check.pack(side=tk.LEFT, padx=5)
        
        aggressive_check = ttk.Checkbutton(checkbox_frame, text="Aggressive Reparatur", 
                                          variable=self.aggressive_var)
        aggressive_check.pack(side=tk.LEFT, padx=5)
        
        clean_check = ttk.Checkbutton(checkbox_frame, text="Rahmen/Artefakte entfernen", 
                                     variable=self.clean_var)
        clean_check.pack(side=tk.LEFT, padx=5)
        
        timestamp_check = ttk.Checkbutton(checkbox_frame, text="Zeitstempel hinzufügen", 
                                         variable=self.timestamp_var)
        timestamp_check.pack(side=tk.LEFT, padx=5)
        
        # Button-Frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        validate_btn = create_button(button_frame, text="Nur validieren", 
                                    command=self.validate_stl_file)
        validate_btn.pack(side=tk.LEFT, padx=5)
        
        repair_btn = create_button(button_frame, text="STL reparieren", 
                                  command=self.repair_stl)
        repair_btn.pack(side=tk.LEFT, padx=5)
        
        # Log-Bereich
        log_frame, self.log_text = create_log_area(main_frame)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)
    
    def browse_input(self):
        """Öffnet einen Dateiauswahldialog für die Eingabedatei"""
        filetypes = [
            ("STL-Dateien", "*.stl"),
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
                output_file = f"{base_name}_repaired.stl"
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
    
    def validate_stl_file(self):
        """Validiert die STL-Datei ohne sie zu reparieren"""
        input_file = self.input_entry.get()
        
        if not input_file:
            self.status_var.set("Fehler: Keine Eingabedatei ausgewählt")
            return
        
        # Status aktualisieren
        self.status_var.set("Validiere STL-Datei...")
        
        # Log-Bereich leeren
        self.log_text.configure(state="normal")
        self.log_text.delete(1.0, tk.END)
        self.log_text.configure(state="disabled")
        
        # Validierung in einem separaten Thread starten
        self.start_validation_thread(input_file)
    
    def start_validation_thread(self, input_file):
        """Startet einen Thread zur Validierung mit dem übergebenen Dateipfad"""
        import threading
        thread = threading.Thread(target=self._run_validation, args=(input_file,))
        thread.daemon = True
        thread.start()
    
    def _run_validation(self, input_file):
        """
        Führt die Validierung in einem separaten Thread aus.
        
        Args:
            input_file: Pfad zur Eingabedatei
        """
        try:
            # Validierung durchführen
            print(f"Validiere STL-Datei: {input_file}")
            
            is_valid, stats = validate_stl(input_file, verbose=True)
            
            print("\nSTL-Validierungsergebnisse:")
            print(f"Datei: {input_file}")
            for key, value in stats.items():
                print(f"{key}: {value}")
            
            if is_valid:
                print("\nDie STL-Datei ist für den 3D-Druck geeignet.")
                self.status_var.set("Validierung abgeschlossen: Datei ist gültig")
            else:
                print("\nDie STL-Datei hat Probleme, die den 3D-Druck beeinträchtigen könnten.")
                print("Klicke auf 'STL reparieren', um die Datei zu reparieren.")
                self.status_var.set("Validierung abgeschlossen: Probleme gefunden")
                
        except Exception as e:
            print(f"Fehler bei der Validierung: {str(e)}")
            self.status_var.set("Fehler bei der Validierung")
    
    def repair_stl(self):
        """Repariert die STL-Datei"""
        input_file = self.input_entry.get()
        output_file = self.output_entry.get()
        
        if not input_file:
            self.status_var.set("Fehler: Keine Eingabedatei ausgewählt")
            return
        
        if not output_file:
            base_name = os.path.splitext(os.path.basename(input_file))[0]
            output_file = f"{base_name}_repaired.stl"
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, output_file)
        
        try:
            # Parameter aus den UI-Elementen holen
            verbose = self.verbose_var.get()
            aggressive = self.aggressive_var.get()
            clean_model_flag = self.clean_var.get()
            max_iterations = self.iterations_var.get()
            timeout = self.timeout_var.get()
            use_timestamp = self.timestamp_var.get()
            
            # Status aktualisieren
            self.status_var.set("Repariere STL-Datei...")
            
            # Log-Bereich leeren
            self.log_text.configure(state="normal")
            self.log_text.delete(1.0, tk.END)
            self.log_text.configure(state="disabled")
            
            # Reparatur in einem separaten Thread starten
            self.start_repair_thread(
                input_file, output_file, verbose, aggressive, clean_model_flag,
                max_iterations, timeout, use_timestamp
            )
        
        except Exception as e:
            import traceback
            error_msg = f"Fehler bei der Eingabevalidierung: {str(e)}"
            self.status_var.set(error_msg)
            self.log_text.configure(state="normal")
            self.log_text.insert(tk.END, f"{error_msg}\n{traceback.format_exc()}")
            self.log_text.configure(state="disabled")
    
    def start_repair_thread(self, *args):
        """Startet einen Thread zur Reparatur mit den übergebenen Parametern"""
        import threading
        thread = threading.Thread(target=self._run_repair, args=args)
        thread.daemon = True
        thread.start()
    
    def _run_repair(self, input_file, output_file, verbose, aggressive, clean_model_flag,
                   max_iterations, timeout, use_timestamp):
        """
        Führt die Reparatur in einem separaten Thread aus.
        
        Args:
            Alle Parameter werden von repair_stl() übergeben
        """
        try:
            # Reparatur durchführen
            print(f"Repariere STL-Datei: {input_file}")
            print(f"Optionen: Aggressive Reparatur: {'Aktiviert' if aggressive else 'Deaktiviert'}")
            print(f"         Rahmenentfernung: {'Aktiviert' if clean_model_flag else 'Deaktiviert'}")
            print(f"         Max. Iterationen: {max_iterations}")
            print(f"         Timeout: {timeout} Sekunden")
            
            result_path = fix_stl(
                input_file, output_file, verbose, aggressive, clean_model_flag,
                max_iterations, timeout, use_timestamp
            )
            
            # Status aktualisieren
            self.status_var.set(f"Reparatur erfolgreich abgeschlossen: {result_path}")
            
            # Validiere das Ergebnis
            print("\nValidierung der reparierten Datei:")
            is_valid, stats = validate_stl(result_path, verbose=False)
            
            if stats.get('is_watertight', False):
                print("SUCCESS: Mesh ist wasserdicht")
            else:
                print("WARNUNG: Mesh ist nicht wasserdicht")
                if not aggressive:
                    print("TIPP: Aktiviere 'Aggressive Reparatur' für wasserdichte Meshes")
                
        except Exception as e:
            print(f"Fehler bei der Reparatur: {str(e)}")
            import traceback
            traceback.print_exc()
            self.status_var.set("Fehler bei der Reparatur")