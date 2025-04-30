#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STL-Reducer: Ein Tool zum Verkleinern von STL-Dateien für 3D-Druck
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
import datetime

# Farbschema (Material Design mit #2C2E3B als Hauptfarbe)
COLORS = {
    "primary": "#2C2E3B",
    "primary_light": "#565969",
    "primary_dark": "#060714",
    "accent": "#5C6BC0",
    "text": "#FFFFFF",
    "text_secondary": "#B0BEC5",
    "bg": "#303030",
    "success": "#4CAF50",
    "warning": "#FFC107",
    "error": "#F44336",
    "button_text": "#FFFFFF",
    "button_bg": "#3F51B5",
}


def create_output_dir(script_name="stl-reducer"):
    """Erstellt das Ausgabeverzeichnis basierend auf dem Skriptnamen."""
    output_dir = os.path.join("output", script_name)
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


def reduce_mesh_size(input_file, output_file, reduction_factor=0.5,
                     preserve_boundary=True, smooth_iterations=0,
                     verbose=False, use_timestamp=False, method='basic'):
    """
    Reduziert die Größe einer STL-Datei durch Mesh-Dezimierung.

    Args:
        input_file: Pfad zur Eingabe-STL-Datei
        output_file: Pfad zur Ausgabe-STL-Datei
        reduction_factor: Zielwert für Reduktion (0.1 = auf 10% reduzieren, 0.5 = auf 50% reduzieren)
        preserve_boundary: Rand-Geometrie erhalten
        smooth_iterations: Anzahl der Glättungsdurchgänge nach Reduzierung
        verbose: Detaillierte Ausgabe anzeigen
        use_timestamp: Zeitstempel zum Ausgabedateinamen hinzufügen
        method: Dezimierungsmethode ('basic', 'quadric' oder 'voxel')

    Returns:
        dict: Statistiken über die Verkleinerung
    """
    try:
        # Ausgabeverzeichnis erstellen
        script_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
        output_dir = create_output_dir(script_name)

        # Zeitstempel einfügen, falls gewünscht
        if use_timestamp:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
            base_name, ext = os.path.splitext(os.path.basename(output_file))
            output_file = f"{base_name}_{timestamp}{ext}"

        # Ausgabepfad anpassen
        if os.path.isabs(output_file):
            # Wenn absoluter Pfad angegeben wurde, behalte den Dateinamen bei
            output_filename = os.path.basename(output_file)
            output_file = os.path.join(output_dir, output_filename)
        else:
            # Wenn relativer Pfad angegeben wurde
            output_file = os.path.join(output_dir, os.path.basename(output_file))

        if verbose:
            print(f"Lade STL-Datei: {input_file}")

        # Mesh laden mit trimesh
        mesh_data = trimesh.load_mesh(input_file)

        # Originalgröße speichern
        original_vertices = len(mesh_data.vertices)
        original_faces = len(mesh_data.faces)
        original_file_size = os.path.getsize(input_file)

        if verbose:
            print(f"Original-Mesh: {original_vertices} Vertices, {original_faces} Faces")
            print(f"Originaldateigröße: {original_file_size / 1024:.2f} KB")

        # 1. Doppelte Vertices und Flächen entfernen
        mesh_data.merge_vertices()
        mesh_data.process()

        if verbose:
            print(f"Nach Duplikatentfernung: {len(mesh_data.vertices)} Vertices, {len(mesh_data.faces)} Faces")

        # 2. Mesh-Dezimierung durchführen
        # Berechne Zielanzahl von Faces
        target_faces = int(original_faces * reduction_factor)

        if verbose:
            print(f"Zielanzahl Flächen: {target_faces}")
            print(f"Verwende Dezimierungsmethode: {method}")

        # Verschiedene Dezimierungsmethoden zur Auswahl
        decimated_mesh = None

        # Versuche PyMeshLab zu verwenden falls verfügbar
        if method in ['quadric', 'basic']:
            try:
                import pymeshlab
                if verbose:
                    print("PyMeshLab gefunden, verwende es für die Mesh-Dezimierung...")

                # Erzeuge ein neues MeshSet
                ms = pymeshlab.MeshSet()

                # Füge das aktuelle Mesh hinzu (zuerst in temporäre Datei speichern)
                temp_file = os.path.join(output_dir, "temp_mesh.stl")
                mesh_data.export(temp_file)
                ms.load_new_mesh(temp_file)

                if method == 'quadric':
                    # Quadric Edge Collapse Decimation
                    if verbose:
                        print("Verwende Quadric Edge Collapse Decimation...")
                    ms.meshing_decimation_quadric_edge_collapse(
                        targetfacenum=target_faces,
                        preserveboundary=preserve_boundary
                    )
                else:
                    # Clustered Decimation (einfacher)
                    if verbose:
                        print("Verwende Clustered Decimation...")
                    ms.meshing_decimation_clustering(
                        targetfacenum=target_faces
                    )

                # Speichere das resultierende Mesh in eine temporäre Datei
                decimated_file = os.path.join(output_dir, "decimated_mesh.stl")
                ms.save_current_mesh(decimated_file)

                # Lade das reduzierte Mesh zurück
                decimated_mesh = trimesh.load_mesh(decimated_file)

                # Lösche temporäre Dateien
                try:
                    os.remove(temp_file)
                    os.remove(decimated_file)
                except:
                    pass

            except ImportError:
                if verbose:
                    print("PyMeshLab nicht verfügbar, verwende alternative Methoden...")
                method = 'voxel' if method == 'quadric' else 'basic'

        # Quadric Decimation mit Trimesh
        if method == 'quadric' and decimated_mesh is None:
            try:
                if verbose:
                    print("Versuche Quadric Error Metrics Dezimierung...")
                decimated_mesh = mesh_data.simplify_quadric_decimation(target_faces)
            except (ImportError, AttributeError) as e:
                if verbose:
                    print(f"Quadric Dezimierung nicht verfügbar: {str(e)}")
                    print("Wechsle zu Voxel-basierter Vereinfachung...")
                method = 'voxel'

        # Voxel-basierte Vereinfachung
        if method == 'voxel' and decimated_mesh is None:
            try:
                if verbose:
                    print("Führe Voxel-basierte Vereinfachung durch...")

                # Berechne eine vernünftige Voxelgröße basierend auf dem Reduktionsfaktor und der Modellgröße
                # Je größer die Voxelgröße, desto stärker die Reduktion
                extents = mesh_data.bounding_box.extents
                max_extent = max(extents)

                # Skaliere die Voxelgröße basierend auf dem Reduktionsfaktor
                # Kleinerer Reduktionsfaktor = größere Voxel = mehr Reduktion
                scale_factor = 1.0 / (reduction_factor ** 0.5)  # Nicht-lineare Skalierung
                voxel_size = max_extent / (100.0 * scale_factor)

                if verbose:
                    print(f"Verwende Voxelgröße: {voxel_size}")

                # Voxelisiere das Mesh
                voxelized = mesh_data.voxelized(pitch=voxel_size)
                # Erzeuge ein neues Mesh aus den Voxeln
                decimated_mesh = voxelized.marching_cubes
            except Exception as e:
                if verbose:
                    print(f"Voxel-basierte Vereinfachung fehlgeschlagen: {str(e)}")
                    print("Wechsle zu grundlegender Vereinfachung...")
                method = 'basic'

        # Basis-Vereinfachung: Manuelle Vertex-Reduktion
        if decimated_mesh is None:
            if verbose:
                print("Führe einfache Vertex-Reduktion durch...")

            try:
                # Eigene Implementierung einer einfachen Dezimierung durch Vertex-Reduktion
                # Wir wählen nur einen Teil der Vertices und rekonstruieren die Faces

                # 1. Wähle einen Teil der Vertices basierend auf dem Reduktionsfaktor
                vertices = mesh_data.vertices
                n_vertices = len(vertices)
                n_target = int(n_vertices * reduction_factor)

                if n_target < 3:
                    n_target = 3  # Mindestens 3 Vertices benötigt

                # Wähle Vertices gleichmäßig aus
                selected_indices = np.linspace(0, n_vertices - 1, n_target, dtype=int)
                selected_vertices = vertices[selected_indices]

                # 2. Erstelle ein neues vereinfachtes Mesh aus diesen Vertices
                # Verwende ConvexHull, um ein gültiges Mesh zu erzeugen
                from scipy.spatial import ConvexHull
                hull = ConvexHull(selected_vertices)

                # Erstelle ein neues Mesh aus der konvexen Hülle
                hull_vertices = selected_vertices[hull.vertices]
                hull_faces = hull.simplices

                # Erstelle ein trimesh aus den Hull-Daten
                decimated_mesh = trimesh.Trimesh(vertices=hull_vertices, faces=hull_faces)

                if verbose:
                    print(f"Konvexe Hülle erstellt mit {len(hull_vertices)} Vertices und {len(hull_faces)} Faces")

            except Exception as e:
                if verbose:
                    print(f"Einfache Vertex-Reduktion fehlgeschlagen: {str(e)}")
                    print("Verwende das Mesh nach Duplikatentfernung...")

                # Fallback: Verwende das Mesh nach der Duplikatentfernung
                decimated_mesh = mesh_data

        if verbose:
            print(f"Nach Dezimierung: {len(decimated_mesh.vertices)} Vertices, {len(decimated_mesh.faces)} Faces")

        # 3. Optional: Glätten
        if smooth_iterations > 0:
            if verbose:
                print(f"Führe {smooth_iterations} Glättungsdurchläufe durch...")
            # Laplacian-Glättung anwenden
            decimated_mesh = decimated_mesh.smoothed(method='laplacian', iterations=smooth_iterations)

        # 4. Sicherstellen, dass alle Flächen gültig sind
        # Entferne degenerierte Dreiecke (Dreiecke mit Null-Fläche)
        if len(decimated_mesh.faces) > 0:
            # Identifiziere degenerierte Dreiecke (mit Null-Fläche)
            areas = trimesh.triangles.area(decimated_mesh.triangles)
            valid_faces = areas > 1e-8  # Toleranz für Flächenberechnung

            if not np.all(valid_faces):
                if verbose:
                    invalid_count = np.sum(~valid_faces)
                    print(f"Entferne {invalid_count} degenerierte Dreiecke")

                # Aktualisiere Faces, behalte nur gültige
                decimated_mesh.update_faces(decimated_mesh.faces[valid_faces])

        # 5. Ergebnis speichern
        decimated_mesh.export(output_file)

        # Statistiken sammeln
        reduced_vertices = len(decimated_mesh.vertices)
        reduced_faces = len(decimated_mesh.faces)
        reduced_file_size = os.path.getsize(output_file)

        vertex_reduction = (1 - reduced_vertices / original_vertices) * 100
        face_reduction = (1 - reduced_faces / original_faces) * 100
        size_reduction = (1 - reduced_file_size / original_file_size) * 100

        if verbose:
            print(f"Reduziertes Mesh: {reduced_vertices} Vertices, {reduced_faces} Faces")
            print(f"Reduzierte Dateigröße: {reduced_file_size / 1024:.2f} KB")
            print(
                f"Reduktion: Vertices {vertex_reduction:.1f}%, Faces {face_reduction:.1f}%, Größe {size_reduction:.1f}%")
            print(f"Reduziertes Mesh gespeichert als: {output_file}")

        # Statistiken zurückgeben
        return {
            "original_vertices": original_vertices,
            "original_faces": original_faces,
            "original_file_size": original_file_size,
            "reduced_vertices": reduced_vertices,
            "reduced_faces": reduced_faces,
            "reduced_file_size": reduced_file_size,
            "vertex_reduction_percent": vertex_reduction,
            "face_reduction_percent": face_reduction,
            "size_reduction_percent": size_reduction
        }

    except Exception as e:
        print(f"Fehler bei der Mesh-Reduzierung: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


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


class STLReducerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("STL-Reducer")
        self.root.geometry("800x600")
        self.root.minsize(600, 400)
        self.root.configure(bg=COLORS["bg"])

        self.input_file = ""
        self.output_file = ""
        self.method = "basic"  # Standardmethode

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

        # Reduktions-Faktor
        reduction_label = tk.Label(options_frame, text="Reduktionsfaktor:", bg=COLORS["bg"], fg=COLORS["text"])
        reduction_label.grid(row=0, column=0, sticky=tk.W, pady=5)

        self.reduction_var = tk.StringVar(value="0.5")
        reduction_entry = tk.Entry(options_frame, textvariable=self.reduction_var, width=5,
                                   bg=COLORS["primary_light"], fg=COLORS["text"])
        reduction_entry.grid(row=0, column=1, sticky=tk.W, padx=5)

        # Reduktions-Beschreibung
        reduction_desc = tk.Label(options_frame,
                                  text="(0.1 = auf 10% reduzieren, 1.0 = keine Reduktion)",
                                  bg=COLORS["bg"], fg=COLORS["text_secondary"], font=("Arial", 8))
        reduction_desc.grid(row=0, column=2, sticky=tk.W, padx=5)

        # Smoothing-Iterationen
        smooth_label = tk.Label(options_frame, text="Glättungs-Iterationen:", bg=COLORS["bg"], fg=COLORS["text"])
        smooth_label.grid(row=1, column=0, sticky=tk.W, pady=5)

        self.smooth_var = tk.StringVar(value="0")
        smooth_entry = tk.Entry(options_frame, textvariable=self.smooth_var, width=5,
                                bg=COLORS["primary_light"], fg=COLORS["text"])
        smooth_entry.grid(row=1, column=1, sticky=tk.W, padx=5)

        # Smoothing-Beschreibung
        smooth_desc = tk.Label(options_frame,
                               text="(0 = keine Glättung, höhere Werte = mehr Glättung)",
                               bg=COLORS["bg"], fg=COLORS["text_secondary"], font=("Arial", 8))
        smooth_desc.grid(row=1, column=2, sticky=tk.W, padx=5)

        # Dezimierungsmethode
        method_frame = tk.Frame(options_frame, bg=COLORS["bg"])
        method_frame.grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=10)

        method_label = tk.Label(method_frame, text="Dezimierungsmethode:", bg=COLORS["bg"], fg=COLORS["text"])
        method_label.pack(side=tk.LEFT, padx=(0, 10))

        self.method_var = tk.StringVar(value="basic")

        # Radio-Buttons für Methoden
        method_basic = tk.Radiobutton(method_frame, text="Basic", variable=self.method_var, value="basic",
                                      bg=COLORS["bg"], fg=COLORS["text"], selectcolor=COLORS["primary"],
                                      activebackground=COLORS["bg"], activeforeground=COLORS["text"])
        method_basic.pack(side=tk.LEFT, padx=(0, 10))

        method_quadric = tk.Radiobutton(method_frame, text="Quadric", variable=self.method_var, value="quadric",
                                        bg=COLORS["bg"], fg=COLORS["text"], selectcolor=COLORS["primary"],
                                        activebackground=COLORS["bg"], activeforeground=COLORS["text"])
        method_quadric.pack(side=tk.LEFT, padx=(0, 10))

        method_voxel = tk.Radiobutton(method_frame, text="Voxel", variable=self.method_var, value="voxel",
                                      bg=COLORS["bg"], fg=COLORS["text"], selectcolor=COLORS["primary"],
                                      activebackground=COLORS["bg"], activeforeground=COLORS["text"])
        method_voxel.pack(side=tk.LEFT)

        # Checkbox-Optionen
        checkbox_frame = tk.Frame(options_frame, bg=COLORS["bg"])
        checkbox_frame.grid(row=3, column=0, columnspan=3, sticky=tk.W, pady=10)

        self.preserve_boundary_var = tk.BooleanVar(value=True)
        preserve_check = tk.Checkbutton(checkbox_frame, text="Randgeometrie erhalten",
                                        variable=self.preserve_boundary_var,
                                        bg=COLORS["bg"], fg=COLORS["text"], selectcolor=COLORS["primary"],
                                        activebackground=COLORS["bg"], activeforeground=COLORS["text"])
        preserve_check.pack(side=tk.LEFT, padx=(0, 20))

        self.verbose_var = tk.BooleanVar(value=True)
        verbose_check = tk.Checkbutton(checkbox_frame, text="Ausführliche Ausgabe",
                                       variable=self.verbose_var,
                                       bg=COLORS["bg"], fg=COLORS["text"], selectcolor=COLORS["primary"],
                                       activebackground=COLORS["bg"], activeforeground=COLORS["text"])
        verbose_check.pack(side=tk.LEFT, padx=(0, 20))

        self.timestamp_var = tk.BooleanVar(value=False)
        timestamp_check = tk.Checkbutton(checkbox_frame, text="Zeitstempel hinzufügen",
                                         variable=self.timestamp_var,
                                         bg=COLORS["bg"], fg=COLORS["text"], selectcolor=COLORS["primary"],
                                         activebackground=COLORS["bg"], activeforeground=COLORS["text"])
        timestamp_check.pack(side=tk.LEFT)

        options_frame.columnconfigure(2, weight=1)

        # Button-Frame
        button_frame = tk.Frame(self.main_frame, bg=COLORS["bg"])
        button_frame.pack(fill=tk.X, pady=10)

        reduce_btn = tk.Button(button_frame, text="STL reduzieren", command=self.reduce_stl,
                               bg=COLORS["accent"], fg=COLORS["button_text"], activebackground=COLORS["primary_dark"],
                               font=('Arial', 10, 'bold'), padx=10, pady=5)
        reduce_btn.pack(side=tk.LEFT, padx=5)

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
                output_file = f"{base_name}_reduced.stl"
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

    def reduce_stl(self):
        input_file = self.input_entry.get()
        output_file = self.output_entry.get()

        if not input_file:
            self.show_message("Bitte wähle eine Eingabedatei aus.")
            return

        if not output_file:
            base_name = os.path.splitext(input_file)[0]
            output_file = f"{base_name}_reduced.stl"
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, output_file)

        try:
            reduction_factor = float(self.reduction_var.get())
            if reduction_factor <= 0 or reduction_factor > 1.0:
                self.show_message("Der Reduktionsfaktor muss zwischen 0.01 und 1.0 liegen.")
                return
        except ValueError:
            self.show_message("Bitte gib einen gültigen Reduktionsfaktor ein.")
            return

        try:
            smooth_iterations = int(self.smooth_var.get())
            if smooth_iterations < 0:
                self.show_message("Die Anzahl der Glättungs-Iterationen muss mindestens 0 sein.")
                return
        except ValueError:
            self.show_message("Bitte gib eine gültige Anzahl von Glättungs-Iterationen ein.")
            return

        self.status_var.set("Reduziere STL...")
        self.log_text.configure(state="normal")
        self.log_text.delete(1.0, tk.END)
        self.log_text.configure(state="disabled")

        thread = threading.Thread(target=self._reduce_thread,
                                  args=(input_file, output_file, reduction_factor, smooth_iterations))
        thread.daemon = True
        thread.start()

    def _reduce_thread(self, input_file, output_file, reduction_factor, smooth_iterations):
        verbose = self.verbose_var.get()
        preserve_boundary = self.preserve_boundary_var.get()
        use_timestamp = self.timestamp_var.get()
        method = self.method_var.get()

        # Aktualisiere Status
        self.status_var.set("Reduziere STL...")
        print(f"Reduziere STL-Datei: {input_file}")
        print(f"Reduktionsfaktor: {reduction_factor}")
        print(f"Glättungs-Iterationen: {smooth_iterations}")
        print(f"Dezimierungsmethode: {method}")
        print(f"Optionen: Randgeometrie erhalten: {'Ja' if preserve_boundary else 'Nein'}")
        print(f"         Zeitstempel: {'Ja' if use_timestamp else 'Nein'}")

        try:
            stats = reduce_mesh_size(
                input_file,
                output_file,
                reduction_factor=reduction_factor,
                preserve_boundary=preserve_boundary,
                smooth_iterations=smooth_iterations,
                verbose=verbose,
                use_timestamp=use_timestamp,
                method=method
            )

            if stats:
                print("\nSTL-Reduktion abgeschlossen:")
                print(f"Originalgröße: {stats['original_file_size'] / 1024:.2f} KB")
                print(f"Neue Größe: {stats['reduced_file_size'] / 1024:.2f} KB")
                print(f"Reduktion: {stats['size_reduction_percent']:.1f}%")
                print(f"Ausgabedatei: {output_file}")
                self.status_var.set(f"Reduktion abgeschlossen: {stats['size_reduction_percent']:.1f}% kleiner")
            else:
                print("Reduktion fehlgeschlagen.")
                self.status_var.set("Reduktion fehlgeschlagen")

        except Exception as e:
            print(f"Fehler bei der STL-Reduktion: {str(e)}")
            self.status_var.set("Reduktion fehlgeschlagen")

    def show_message(self, message):
        print(message)
        self.status_var.set(message)


def command_line_interface():
    parser = argparse.ArgumentParser(description="STL-Reducer: Reduziert die Größe von STL-Dateien für 3D-Druck")
    parser.add_argument("input_file", nargs="?", help="Pfad zur Eingabe-STL-Datei")
    parser.add_argument("-o", "--output", help="Pfad zur Ausgabe-STL-Datei (Standard: input_file_reduced.stl)")
    parser.add_argument("-r", "--reduction", type=float, default=0.5,
                        help="Reduktionsfaktor (0.1 = auf 10%% reduzieren, 1.0 = keine Reduktion)")
    parser.add_argument("-s", "--smooth", type=int, default=0,
                        help="Anzahl der Glättungs-Iterationen (0 = keine Glättung)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Ausführliche Ausgabe")
    parser.add_argument("--preserve-boundary", action="store_true", help="Randgeometrie erhalten")
    parser.add_argument("--gui", action="store_true", help="Startet die grafische Benutzeroberfläche")
    parser.add_argument("-t", "--timestamp", action="store_true",
                        help="Zeitstempel (yyyy-MM-dd-HH-mm-ss) an Ausgabedatei anfügen")
    parser.add_argument("-m", "--method", choices=["basic", "quadric", "voxel"], default="basic",
                        help="Dezimierungsmethode: basic (Standard), quadric (benötigt pymeshlab), oder voxel")

    args = parser.parse_args()

    # GUI-Modus starten, wenn --gui angegeben oder keine Argumente vorhanden sind
    if args.gui or (len(sys.argv) == 1):
        root = tk.Tk()
        app = STLReducerGUI(root)
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
        output_file = f"{base_name}_reduced.stl"

    print(f"Reduziere STL-Datei: {args.input_file}")
    print(f"Reduktionsfaktor: {args.reduction}")
    print(f"Glättungs-Iterationen: {args.smooth}")

    stats = reduce_mesh_size(
        args.input_file,
        output_file,
        reduction_factor=args.reduction,
        preserve_boundary=args.preserve_boundary,
        smooth_iterations=args.smooth,
        verbose=args.verbose,
        use_timestamp=args.timestamp,
        method=args.method
    )

    if stats:
        print("\nSTL-Reduktion abgeschlossen:")
        print(f"Originalgröße: {stats['original_file_size'] / 1024:.2f} KB")
        print(f"Neue Größe: {stats['reduced_file_size'] / 1024:.2f} KB")
        print(f"Reduktion: {stats['size_reduction_percent']:.1f}%")
        print(f"Ausgabedatei: {output_file}")
        return 0
    else:
        print("Reduktion fehlgeschlagen.")
        return 1


if __name__ == "__main__":
    sys.exit(command_line_interface())