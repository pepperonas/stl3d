#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
STL-Fixer: Ein Tool zum Reparieren von STL-Dateien für 3D-Druck
Unterstützt sowohl Kommandozeilen- als auch GUI-Modus
"""

import argparse
import os
import sys
import numpy as np
import trimesh
from stl import mesh
import tkinter as tk
from tkinter import filedialog, ttk, scrolledtext
import threading
import time

# Farbschema (Material Design mit #2C2E3B als Hauptfarbe)
COLORS = {
    "primary": "#2C2E3B",
    "primary_light": "#565969",
    "primary_dark": "#060714",
    "accent": "#5C6BC0",  # etwas dunkler für besseren Kontrast mit weißem Text
    "text": "#FFFFFF",
    "text_secondary": "#B0BEC5",
    "bg": "#303030",
    "success": "#4CAF50",
    "warning": "#FFC107",
    "error": "#F44336",
    "button_text": "#FFFFFF",  # separater Textwert für Buttons
    "button_bg": "#3F51B5",  # hellerer Button-Hintergrund
}


def clean_model(mesh_data, verbose=False):
    """
    Säubert das Modell von Artefakten wie Rändern, Rahmen und isolierten Teilen.

    Args:
        mesh_data: Das zu säubernde Trimesh-Objekt
        verbose: Wenn True, werden Fortschrittsinformationen ausgegeben

    Returns:
        Das gesäuberte Trimesh-Objekt
    """
    if verbose:
        print("Entferne Artefakte und Rahmenelemente...")

    # Original-Statistiken speichern
    original_vertices = len(mesh_data.vertices)
    original_faces = len(mesh_data.faces)

    # 1. Entferne doppelte Vertices und Flächen
    mesh_data.merge_vertices()
    mesh_data.update_faces(mesh_data.unique_faces())

    # 2. Identifiziere zusammenhängende Komponenten
    components = mesh_data.split(only_watertight=False)

    if len(components) > 1:
        if verbose:
            print(f"Modell besteht aus {len(components)} separaten Komponenten")

        # Berechne Volumen/Größe jeder Komponente
        component_sizes = []
        for i, comp in enumerate(components):
            # Verwende Anzahl der Flächen als Maß für die Größe
            size = len(comp.faces)
            # Versuche Volumen zu berechnen, wenn möglich
            volume = 0
            try:
                if comp.is_watertight:
                    volume = comp.volume
            except:
                pass

            component_sizes.append((i, size, volume))

            if verbose:
                print(f"  Komponente {i + 1}: {size} Flächen, Volumen: {volume:.2f}")

        # Sortiere nach Größe (Anzahl der Flächen)
        component_sizes.sort(key=lambda x: x[1], reverse=True)

        # Identifiziere Hauptkomponente(n) und Rahmen/Artefakte
        main_components = []
        artifacts = []

        # Hauptkomponente ist die größte
        main_size = component_sizes[0][1]

        # Komponenten, die mindestens 20% der Größe der Hauptkomponente haben, werden behalten
        threshold = main_size * 0.2

        for i, size, volume in component_sizes:
            if size >= threshold:
                main_components.append(i)
            else:
                artifacts.append(i)

        if verbose:
            print(f"Identifizierte {len(main_components)} Hauptkomponente(n) und {len(artifacts)} Artefakte/Rahmen")

        # Behalte nur die Hauptkomponenten
        if len(main_components) < len(components):
            # Erstelle ein neues Mesh aus den Hauptkomponenten
            kept_components = [components[i] for i in main_components]

            if len(kept_components) == 1:
                # Nur eine Hauptkomponente
                mesh_data = kept_components[0]
            else:
                # Mehrere Hauptkomponenten - vereinige sie
                mesh_data = trimesh.util.concatenate(kept_components)

            if verbose:
                print(f"Artefakte/Rahmen entfernt. Neue Mesh-Größe: {len(mesh_data.faces)} Flächen")

    # 3. Entferne degeneriete Dreiecke (Dreiecke mit Null-Fläche)
    if len(mesh_data.faces) > 0:
        # Identifiziere degenerierte Dreiecke (mit Null-Fläche)
        areas = trimesh.triangles.area(mesh_data.triangles)
        valid_faces = areas > 1e-8  # Toleranz für Flächenberechnung

        if not np.all(valid_faces):
            if verbose:
                invalid_count = np.sum(~valid_faces)
                print(f"Entferne {invalid_count} degenerierte Dreiecke")

            # Aktualisiere Faces, behalte nur gültige
            mesh_data.update_faces(mesh_data.faces[valid_faces])

    # Statistiken ausgeben
    if verbose:
        vertices_removed = original_vertices - len(mesh_data.vertices)
        faces_removed = original_faces - len(mesh_data.faces)
        print(f"Säuberung abgeschlossen: {vertices_removed} Vertices und {faces_removed} Flächen entfernt")

    return mesh_data


def make_watertight(mesh_data, max_hole_size=None, timeout=30):
    """
    Aggressive Funktion zum Wasserdichtmachen eines Meshes

    Args:
        mesh_data: Das zu reparierende Trimesh-Objekt
        max_hole_size: Maximale Größe der zu füllenden Löcher (None = alle Größen)
        timeout: Maximale Zeit in Sekunden für rechenintensive Operationen

    Returns:
        Das reparierte Trimesh-Objekt
    """
    import time
    start_time = time.time()

    # 1. Entferne doppelte Vertices und Flächen
    mesh_data.merge_vertices()
    mesh_data.update_faces(mesh_data.unique_faces())

    # 2. Versuche zunächst, Löcher mit Trimesh zu füllen
    mesh_data.fill_holes()

    # Prüfe, ob das Mesh bereits wasserdicht ist
    if mesh_data.is_watertight:
        print("Mesh ist nach dem Löcher-Füllen bereits wasserdicht!")
        return mesh_data

    # 3. Versuche vereinfachte Reparatur, wenn das Mesh noch nicht wasserdicht ist
    if not mesh_data.is_watertight:
        print("Versuche vereinfachte Reparatur...")

        # Entferne ungenutzte Vertices und isolierte Komponenten
        mesh_data.remove_unreferenced_vertices()

        # Extrahiere die größte zusammenhängende Komponente
        components = mesh_data.split(only_watertight=False)
        if len(components) > 1:
            print(f"Mesh besteht aus {len(components)} getrennten Komponenten")
            # Wähle die größte Komponente
            largest_component = sorted(components, key=lambda m: len(m.faces), reverse=True)[0]
            mesh_data = largest_component
            print(f"Größte Komponente ausgewählt: {len(mesh_data.faces)} Flächen")

        # Normalen korrigieren
        mesh_data.fix_normals()

        # Prüfe erneut, ob das Mesh wasserdicht ist
        if mesh_data.is_watertight:
            print("Mesh ist nach vereinfachter Reparatur wasserdicht!")
            return mesh_data

    # 4. Versuche eine Konvexhülle, wenn die Zeit es erlaubt
    # Dies ist schneller als Voxelisierung und funktioniert in den meisten Fällen
    if not mesh_data.is_watertight and (time.time() - start_time) < timeout:
        try:
            print("Erstelle Konvexhülle...")
            hull_mesh = mesh_data.convex_hull
            if hull_mesh is not None and len(hull_mesh.faces) > 0:
                print("Konvexhülle erfolgreich erstellt")
                return hull_mesh
        except Exception as e:
            print(f"Convex-Hull-Erstellung fehlgeschlagen: {str(e)}")

    # 5. Wenn die Zeit es erlaubt und die Konvexhülle fehlgeschlagen ist,
    # versuche als letzte Option eine Voxelisierung
    if not mesh_data.is_watertight and (time.time() - start_time) < timeout:
        try:
            print("Erstelle Voxel-Darstellung (kann einige Sekunden dauern)...")
            # Verwende eine gröbere Voxel-Auflösung für schnellere Verarbeitung
            # Berechne eine vernünftige Voxelgröße basierend auf der Modellgröße
            voxel_size = max(mesh_data.bounding_box.extents) / 50.0
            print(f"Verwende Voxelgröße: {voxel_size}")

            voxel = mesh_data.voxelized(pitch=voxel_size)

            print("Erzeuge Mesh aus Voxel-Darstellung...")
            watertight_mesh = voxel.marching_cubes

            if watertight_mesh is not None and len(watertight_mesh.faces) > 0:
                print("Voxel-Reparatur erfolgreich")
                return watertight_mesh
        except Exception as e:
            print(f"Voxel-Reparatur fehlgeschlagen: {str(e)}")

    # 6. Wenn alle Versuche fehlschlagen oder das Timeout erreicht wird,
    # gib das bestmögliche Mesh zurück und warne den Benutzer
    if time.time() - start_time >= timeout:
        print(f"Zeitlimit von {timeout} Sekunden erreicht. Breche aggressive Reparatur ab.")

    print("Konnte keine vollständig wasserdichte Version erstellen. Gebe bestmögliches Mesh zurück.")
    return mesh_data


def fix_stl(input_file, output_file, verbose=False, aggressive=True, clean=True, max_iterations=2, timeout=30):
    """
    Lädt eine STL-Datei, repariert sie und speichert die reparierte Version.

    Args:
        input_file (str): Pfad zur Eingabe-STL-Datei
        output_file (str): Pfad zur Ausgabe-STL-Datei
        verbose (bool): Wenn True, werden detaillierte Informationen ausgegeben
        aggressive (bool): Wenn True, werden aggressive Reparaturmethoden angewendet
        clean (bool): Wenn True, werden Rahmen und Artefakte entfernt
        max_iterations (int): Maximale Anzahl von Reparaturversuchen
        timeout (int): Maximale Zeit in Sekunden für rechenintensive Operationen

    Returns:
        bool: True bei Erfolg, False bei Fehler
    """
    if verbose:
        print(f"Lade STL-Datei: {input_file}")

    try:
        # Lade die Datei mit trimesh für erweiterte Reparaturoptionen
        mesh_data = trimesh.load_mesh(input_file)

        if verbose:
            print("Original-Mesh geladen.")
            print(f"Vertices: {len(mesh_data.vertices)}")
            print(f"Faces: {len(mesh_data.faces)}")

            # Prüfe auf Probleme
            if not mesh_data.is_watertight:
                print("PROBLEM: Mesh ist nicht wasserdicht (hat Löcher)")

            if not mesh_data.is_winding_consistent:
                print("PROBLEM: Inkonsistente Flächenorientierung")

            if mesh_data.is_empty:
                print("PROBLEM: Mesh ist leer")

            duplicate_faces = len(mesh_data.faces) - len(np.unique(mesh_data.faces, axis=0))
            if duplicate_faces > 0:
                print(f"PROBLEM: {duplicate_faces} doppelte Flächen gefunden")

        # Säubere das Modell von Artefakten wie Rändern und Rahmenelementen
        if clean:
            if verbose:
                print("Säubere das Modell von Artefakten...")
            mesh_data = clean_model(mesh_data, verbose)

        # Repariere das Mesh
        if verbose:
            print("Repariere Mesh...")

        # Iterativer Reparaturprozess
        iteration = 0
        repaired_mesh = mesh_data

        while (
                not repaired_mesh.is_watertight or not repaired_mesh.is_winding_consistent) and iteration < max_iterations:
            iteration += 1
            if verbose:
                print(f"Reparaturdurchlauf {iteration}/{max_iterations}...")

            # Grundlegende Reparatur
            # 1. Entferne doppelte Vertices
            repaired_mesh.merge_vertices()

            # 2. Entferne doppelte Flächen
            repaired_mesh.update_faces(repaired_mesh.unique_faces())

            # 3. Fülle Löcher
            repaired_mesh.fill_holes()

            # 4. Korrigiere Flächenorientierungen
            repaired_mesh.fix_normals()

            # 5. Führe zusätzliche Reparaturen durch
            repaired_mesh = repaired_mesh.process(validate=True)

            # Prüfe, ob das Mesh bereits wasserdicht ist
            if repaired_mesh.is_watertight:
                if verbose:
                    print("Mesh ist bereits nach Standard-Reparatur wasserdicht!")
                break

        # Aggressive Reparatur, wenn gewünscht und noch nicht wasserdicht
        if aggressive and not repaired_mesh.is_watertight:
            if verbose:
                print("Starte aggressive Reparatur zum Erzwingen der Wasserdichtigkeit...")
            repaired_mesh = make_watertight(repaired_mesh, timeout=timeout)

        if verbose:
            print("Reparatur abgeschlossen.")
            print(f"Neue Vertices: {len(repaired_mesh.vertices)}")
            print(f"Neue Faces: {len(repaired_mesh.faces)}")

            if repaired_mesh.is_watertight:
                print("SUCCESS: Mesh ist jetzt wasserdicht")
            else:
                print("WARNUNG: Mesh ist immer noch nicht vollständig wasserdicht")
                if not aggressive:
                    print("TIPP: Versuche es mit der Option für aggressive Reparatur")

            if repaired_mesh.is_winding_consistent:
                print("SUCCESS: Flächenorientierung ist jetzt konsistent")
            else:
                print("WARNUNG: Flächenorientierung ist immer noch inkonsistent")

        # Exportiere das reparierte Mesh
        repaired_mesh.export(output_file)

        if verbose:
            print(f"Repariertes Mesh gespeichert als: {output_file}")

        return True

    except Exception as e:
        print(f"Fehler beim Verarbeiten der STL-Datei: {str(e)}")
        return False


def validate_stl(file_path):
    """
    Überprüft, ob die STL-Datei für den 3D-Druck geeignet ist

    Args:
        file_path (str): Pfad zur STL-Datei

    Returns:
        tuple: (bool, dict) - True wenn gültig, sowie ein Dictionary mit Statistiken
    """
    try:
        mesh_data = trimesh.load_mesh(file_path)

        stats = {
            "vertices": len(mesh_data.vertices),
            "faces": len(mesh_data.faces),
            "is_watertight": mesh_data.is_watertight,
            "is_winding_consistent": mesh_data.is_winding_consistent,
            "is_empty": mesh_data.is_empty,
            "volume": mesh_data.volume if mesh_data.is_watertight else "N/A",
            "euler_number": mesh_data.euler_number,
        }

        is_valid = (mesh_data.is_watertight and
                    mesh_data.is_winding_consistent and
                    not mesh_data.is_empty)

        return is_valid, stats

    except Exception as e:
        print(f"Fehler beim Validieren der STL-Datei: {str(e)}")
        return False, {}


class RedirectText:
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.buffer = ""

    def write(self, string):
        self.buffer += string
        self.text_widget.configure(state="normal")
        self.text_widget.insert(tk.END, string)
        self.text_widget.see(tk.END)
        self.text_widget.configure(state="disabled")

    def flush(self):
        pass


class STLFixerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("STL-Fixer")
        self.root.geometry("800x600")
        self.root.minsize(600, 400)
        self.root.configure(bg=COLORS["bg"])

        self.input_file = ""
        self.output_file = ""

        self.create_widgets()
        self.apply_styles()

    def create_widgets(self):
        # Hauptframe
        self.main_frame = tk.Frame(self.root, bg=COLORS["bg"])
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Dateieingabe-Frame
        file_frame = tk.Frame(self.main_frame, bg=COLORS["bg"])
        file_frame.pack(fill=tk.X, pady=10)

        # Input-Datei
        input_label = tk.Label(file_frame, text="Eingabe STL-Datei:", bg=COLORS["bg"], fg=COLORS["text"])
        input_label.grid(row=0, column=0, sticky=tk.W, pady=5)

        self.input_entry = tk.Entry(file_frame, width=50, bg=COLORS["primary_light"], fg=COLORS["text"],
                                    insertbackground=COLORS["text"])
        self.input_entry.grid(row=0, column=1, sticky=tk.EW, padx=5)

        browse_btn = tk.Button(file_frame, text="Durchsuchen", command=self.browse_input, bg=COLORS["primary"],
                               fg=COLORS["text"], activebackground=COLORS["primary_dark"])
        browse_btn.grid(row=0, column=2, padx=5)

        # Output-Datei
        output_label = tk.Label(file_frame, text="Ausgabe STL-Datei:", bg=COLORS["bg"], fg=COLORS["text"])
        output_label.grid(row=1, column=0, sticky=tk.W, pady=5)

        self.output_entry = tk.Entry(file_frame, width=50, bg=COLORS["primary_light"], fg=COLORS["text"],
                                     insertbackground=COLORS["text"])
        self.output_entry.grid(row=1, column=1, sticky=tk.EW, padx=5)

        browse_out_btn = tk.Button(file_frame, text="Durchsuchen", command=self.browse_output, bg=COLORS["primary"],
                                   fg=COLORS["text"], activebackground=COLORS["primary_dark"])
        browse_out_btn.grid(row=1, column=2, padx=5)

        file_frame.columnconfigure(1, weight=1)

        # Optionen-Frame
        options_frame = tk.Frame(self.main_frame, bg=COLORS["bg"])
        options_frame.pack(fill=tk.X, pady=10)

        self.verbose_var = tk.BooleanVar(value=True)
        verbose_check = tk.Checkbutton(options_frame, text="Ausführliche Ausgabe", variable=self.verbose_var,
                                       bg=COLORS["bg"], fg=COLORS["text"], selectcolor=COLORS["primary"],
                                       activebackground=COLORS["bg"], activeforeground=COLORS["text"],
                                       font=('Arial', 10))
        verbose_check.pack(side=tk.LEFT)

        self.aggressive_var = tk.BooleanVar(value=True)
        aggressive_check = tk.Checkbutton(options_frame, text="Aggressive Reparatur",
                                          variable=self.aggressive_var,
                                          bg=COLORS["bg"], fg=COLORS["text"], selectcolor=COLORS["primary"],
                                          activebackground=COLORS["bg"], activeforeground=COLORS["text"],
                                          font=('Arial', 10))
        aggressive_check.pack(side=tk.LEFT, padx=20)

        self.clean_var = tk.BooleanVar(value=True)
        clean_check = tk.Checkbutton(options_frame, text="Rahmen/Artefakte entfernen",
                                     variable=self.clean_var,
                                     bg=COLORS["bg"], fg=COLORS["text"], selectcolor=COLORS["primary"],
                                     activebackground=COLORS["bg"], activeforeground=COLORS["text"],
                                     font=('Arial', 10))
        clean_check.pack(side=tk.LEFT, padx=20)

        # Timeout-Option
        timeout_frame = tk.Frame(options_frame, bg=COLORS["bg"])
        timeout_frame.pack(side=tk.RIGHT, padx=20)

        timeout_label = tk.Label(timeout_frame, text="Timeout (Sek.):", bg=COLORS["bg"], fg=COLORS["text"],
                                 font=('Arial', 10))
        timeout_label.pack(side=tk.LEFT)

        self.timeout_var = tk.StringVar(value="30")
        timeout_entry = tk.Entry(timeout_frame, textvariable=self.timeout_var, width=4,
                                 bg=COLORS["primary_light"], fg=COLORS["text"], insertbackground=COLORS["text"])
        timeout_entry.pack(side=tk.LEFT, padx=5)

        # Button-Frame
        button_frame = tk.Frame(self.main_frame, bg=COLORS["bg"])
        button_frame.pack(fill=tk.X, pady=10)

        validate_btn = tk.Button(button_frame, text="Nur validieren", command=self.validate_stl,
                                 bg=COLORS["button_bg"], fg=COLORS["button_text"],
                                 activebackground=COLORS["primary_dark"],
                                 font=('Arial', 10, 'bold'), padx=10, pady=5)
        validate_btn.pack(side=tk.LEFT, padx=5)

        fix_btn = tk.Button(button_frame, text="Reparieren", command=self.fix_stl,
                            bg=COLORS["accent"], fg=COLORS["button_text"], activebackground=COLORS["primary_dark"],
                            font=('Arial', 10, 'bold'), padx=10, pady=5)
        fix_btn.pack(side=tk.LEFT, padx=5)

        # Log-Ausgabe
        log_frame = tk.Frame(self.main_frame, bg=COLORS["bg"])
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        log_label = tk.Label(log_frame, text="Log:", bg=COLORS["bg"], fg=COLORS["text"])
        log_label.pack(anchor=tk.W)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, bg=COLORS["primary_light"], fg=COLORS["text"])
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.configure(state="disabled")

        # Status-Leiste
        self.status_var = tk.StringVar()
        self.status_var.set("Bereit")
        status_bar = tk.Label(self.root, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W,
                              bg=COLORS["primary"], fg=COLORS["text"])
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # Umleiten der Konsolen-Ausgabe zur Text-Widget
        self.stdout_redirect = RedirectText(self.log_text)
        sys.stdout = self.stdout_redirect

    def apply_styles(self):
        style = ttk.Style()
        style.configure("TButton", background=COLORS["primary"], foreground=COLORS["text"])
        style.map("TButton", background=[("active", COLORS["primary_dark"])])

    def browse_input(self):
        filename = filedialog.askopenfilename(filetypes=[("STL-Dateien", "*.stl"), ("Alle Dateien", "*.*")])
        if filename:
            self.input_file = filename
            self.input_entry.delete(0, tk.END)
            self.input_entry.insert(0, filename)

            # Schlage Ausgabedatei vor
            if not self.output_entry.get():
                base_name = os.path.splitext(filename)[0]
                output_file = f"{base_name}_fixed.stl"
                self.output_file = output_file
                self.output_entry.delete(0, tk.END)
                self.output_entry.insert(0, output_file)

    def browse_output(self):
        filename = filedialog.asksaveasfilename(defaultextension=".stl",
                                                filetypes=[("STL-Dateien", "*.stl"), ("Alle Dateien", "*.*")])
        if filename:
            self.output_file = filename
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, filename)

    def validate_stl(self):
        input_file = self.input_entry.get()
        if not input_file:
            self.show_message("Bitte wähle eine Eingabedatei aus.")
            return

        self.status_var.set("Validiere...")
        self.log_text.configure(state="normal")
        self.log_text.delete(1.0, tk.END)
        self.log_text.configure(state="disabled")

        thread = threading.Thread(target=self._validate_thread, args=(input_file,))
        thread.daemon = True
        thread.start()

    def _validate_thread(self, input_file):
        print(f"Validiere STL-Datei: {input_file}")
        is_valid, stats = validate_stl(input_file)

        print("\nSTL-Validierungsergebnisse:")
        print(f"Datei: {input_file}")
        for key, value in stats.items():
            print(f"{key}: {value}")

        if is_valid:
            print("\nDie STL-Datei ist für den 3D-Druck geeignet.")
            self.status_var.set("Validierung abgeschlossen: Datei ist gültig")
        else:
            print("\nDie STL-Datei hat Probleme, die den 3D-Druck beeinträchtigen könnten.")
            print("Klicke auf 'Reparieren', um die Datei zu reparieren.")
            self.status_var.set("Validierung abgeschlossen: Probleme gefunden")

    def fix_stl(self):
        input_file = self.input_entry.get()
        output_file = self.output_entry.get()

        if not input_file:
            self.show_message("Bitte wähle eine Eingabedatei aus.")
            return

        if not output_file:
            base_name = os.path.splitext(input_file)[0]
            output_file = f"{base_name}_fixed.stl"
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, output_file)

        self.status_var.set("Repariere...")
        self.log_text.configure(state="normal")
        self.log_text.delete(1.0, tk.END)
        self.log_text.configure(state="disabled")

        thread = threading.Thread(target=self._fix_thread, args=(input_file, output_file))
        thread.daemon = True
        thread.start()

    def _fix_thread(self, input_file, output_file):
        verbose = self.verbose_var.get()
        aggressive = self.aggressive_var.get()
        clean = self.clean_var.get()
        timeout = int(self.timeout_var.get())

        # Aktualisiere Status
        self.status_var.set("Repariere...")
        print(f"Repariere STL-Datei: {input_file}")
        print(f"Optionen: Aggressive Reparatur: {'Aktiviert' if aggressive else 'Deaktiviert'}")
        print(f"         Rahmenentfernung: {'Aktiviert' if clean else 'Deaktiviert'}")
        print(f"         Timeout: {timeout} Sekunden")

        try:
            success = fix_stl(input_file, output_file, verbose, aggressive, clean, timeout=timeout)

            if success:
                print(f"STL-Datei erfolgreich repariert. Ausgabedatei: {output_file}")
                self.status_var.set("Reparatur erfolgreich abgeschlossen")

                # Validiere das Ergebnis
                is_valid, stats = validate_stl(output_file)
                if verbose:
                    print("\nValidierung der reparierten Datei:")
                    if stats.get('is_watertight', False):
                        print("SUCCESS: Mesh ist wasserdicht")
                    else:
                        print("WARNUNG: Mesh ist nicht wasserdicht")

                    if not aggressive:
                        print("TIPP: Aktiviere 'Aggressive Reparatur' für wasserdichte Meshes")
            else:
                print("Reparatur fehlgeschlagen.")
                self.status_var.set("Reparatur fehlgeschlagen")

        except Exception as e:
            print(f"Fehler beim Verarbeiten der STL-Datei: {str(e)}")
            self.status_var.set("Reparatur fehlgeschlagen")

    def show_message(self, message):
        print(message)
        self.status_var.set(message)


def command_line_interface():
    parser = argparse.ArgumentParser(description="STL-Fixer: Repariert STL-Dateien für 3D-Druck")
    parser.add_argument("input_file", nargs="?", help="Pfad zur Eingabe-STL-Datei")
    parser.add_argument("-o", "--output", help="Pfad zur Ausgabe-STL-Datei (Standard: input_file_fixed.stl)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Ausführliche Ausgabe")
    parser.add_argument("--validate", action="store_true", help="Nur validieren, keine Reparatur")
    parser.add_argument("--gui", action="store_true", help="Startet die grafische Benutzeroberfläche")
    parser.add_argument("--aggressive", action="store_true", help="Aggressive Reparatur für wasserdichte Meshes")
    parser.add_argument("--clean", action="store_true", help="Entfernt Rahmen und Artefakte")
    parser.add_argument("--timeout", type=int, default=30,
                        help="Zeitlimit für rechenintensive Operationen (Sekunden, Standard: 30)")
    parser.add_argument("--iterations", type=int, default=2,
                        help="Maximale Anzahl von Reparaturversuchen (Standard: 2)")

    args = parser.parse_args()

    # GUI-Modus starten, wenn --gui angegeben oder keine Argumente vorhanden sind
    if args.gui or (len(sys.argv) == 1):
        root = tk.Tk()
        app = STLFixerGUI(root)
        root.mainloop()
        return 0

    # Kommandozeilen-Modus
    if not args.input_file:
        parser.print_help()
        return 1

    # Überprüfe, ob die Eingabedatei existiert
    if not os.path.isfile(args.input_file):
        print(f"Fehler: Die Datei '{args.input_file}' existiert nicht.")
        return 1

    # Überprüfe, ob die Datei eine STL-Datei ist
    if not args.input_file.lower().endswith('.stl'):
        print(f"Warnung: Die Datei '{args.input_file}' scheint keine STL-Datei zu sein.")

    # Bestimme den Ausgabepfad
    if args.output:
        output_file = args.output
    else:
        base_name = os.path.splitext(args.input_file)[0]
        output_file = f"{base_name}_fixed.stl"

    if args.validate:
        print(f"Validiere STL-Datei: {args.input_file}")
        is_valid, stats = validate_stl(args.input_file)

        print("\nSTL-Validierungsergebnisse:")
        print(f"Datei: {args.input_file}")
        for key, value in stats.items():
            print(f"{key}: {value}")

        if is_valid:
            print("\nDie STL-Datei ist für den 3D-Druck geeignet.")
            return 0
        else:
            print("\nDie STL-Datei hat Probleme, die den 3D-Druck beeinträchtigen könnten.")
            print("Führe das Tool ohne --validate aus, um die Datei zu reparieren.")
            return 1
    else:
        print(f"Repariere STL-Datei: {args.input_file}")
        print(f"Optionen: Aggressive Reparatur: {'Aktiviert' if args.aggressive else 'Deaktiviert'}")
        print(f"         Rahmenentfernung: {'Aktiviert' if args.clean else 'Deaktiviert'}")
        print(f"         Timeout: {args.timeout} Sekunden")

        success = fix_stl(args.input_file, output_file, args.verbose, args.aggressive,
                          args.clean, max_iterations=args.iterations, timeout=args.timeout)

        if success:
            print(f"STL-Datei erfolgreich repariert. Ausgabedatei: {output_file}")

            # Validiere das Ergebnis, wenn ausführliche Ausgabe aktiviert ist
            if args.verbose:
                is_valid, stats = validate_stl(output_file)
                print("\nValidierung der reparierten Datei:")
                if stats.get('is_watertight', False):
                    print("SUCCESS: Mesh ist wasserdicht")
                else:
                    print("WARNUNG: Mesh ist nicht wasserdicht")
                    if not args.aggressive:
                        print("TIPP: Nutze --aggressive für wasserdichte Meshes")

            return 0
        else:
            print("Reparatur fehlgeschlagen.")
            return 1


if __name__ == "__main__":
    sys.exit(command_line_interface())