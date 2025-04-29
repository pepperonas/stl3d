#!/usr/bin/env python3
# Einfaches STL Repair Tool - Repariert non-manifold Kanten in 3D Modellen
# Abhängigkeiten: pip install trimesh numpy pyglet

import argparse
import os
import sys
import numpy as np
import trimesh
import datetime


def repair_basic(mesh, verbose=False):
    """Grundlegende Reparatur ohne fortgeschrittene Funktionen"""
    if verbose:
        print("Führe grundlegende Reparaturen durch...")

    try:
        # Entferne doppelte Flächen
        mesh.process()
        if verbose:
            print("- Doppelte Flächen entfernt")

        # Repariere Oberflächennormalen
        mesh.fix_normals()
        if verbose:
            print("- Normalen repariert")

        # Fülle Löcher
        mesh.fill_holes()
        if verbose:
            print("- Löcher gefüllt")

        return mesh
    except Exception as e:
        if verbose:
            print(f"Fehler bei grundlegender Reparatur: {str(e)}")
        return mesh


def repair_advanced(mesh, verbose=False):
    """Fortgeschrittene Reparatur mit zusätzlichen Schritten"""
    if verbose:
        print("Führe fortgeschrittene Reparaturen durch...")

    try:
        # Behalte nur die größten Komponenten
        if hasattr(mesh, 'split'):
            components = mesh.split()
            if len(components) > 1:
                if verbose:
                    print(f"- Gefundene Komponenten: {len(components)}")

                areas = np.array([c.area for c in components])
                mesh = components[areas.argmax()]
                if verbose:
                    print(f"- Größte Komponente mit {len(mesh.faces)} Flächen beibehalten")
        else:
            if verbose:
                print("- Split-Funktion nicht verfügbar, überspringe Komponententrennung")

        return mesh
    except Exception as e:
        if verbose:
            print(f"Fehler bei fortgeschrittener Reparatur: {str(e)}")
        return mesh


def create_output_dir(script_name="stl-repair-tool"):
    """Erstellt das Ausgabeverzeichnis basierend auf dem Skriptnamen."""
    output_dir = os.path.join("output", script_name)
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


def repair_mesh(input_file, output_file, verbose=False, export_intermediate=False, use_timestamp=False):
    """Repariert ein Mesh mit schrittweiser Fehlerbehandlung"""
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
            print(f"Lade Mesh aus: {input_file}")
            print(f"Ausgabe wird in {output_file} gespeichert")

        # Mesh laden
        mesh = trimesh.load(input_file)

        if verbose:
            print(f"Ursprüngliches Mesh: {len(mesh.faces)} Flächen, {len(mesh.vertices)} Vertices")

        # Zähle non-manifold Kanten vor der Reparatur
        edges_unique = mesh.edges_unique
        edges_by_count = trimesh.grouping.group_rows(mesh.edges_sorted, require_count=1)
        non_manifold_edges_before = len(edges_by_count)

        if verbose:
            print(f"Non-manifold Kanten gefunden: {non_manifold_edges_before}")
            print(f"Ist wasserdicht: {mesh.is_watertight}")

        # Speichere Original-Mesh, falls gewünscht
        if export_intermediate:
            intermediate_base, ext = os.path.splitext(os.path.basename(output_file))
            intermediate_path = os.path.join(output_dir, f"{intermediate_base}_original{ext}")
            mesh.export(intermediate_path)
            if verbose:
                print(f"Original-Mesh gespeichert in: {intermediate_path}")

        # Schritt 1: Grundlegende Reparaturen
        repaired_mesh = repair_basic(mesh, verbose)

        # Prüfe Ergebnis nach grundlegender Reparatur
        if export_intermediate:
            intermediate_base, ext = os.path.splitext(os.path.basename(output_file))
            intermediate_path = os.path.join(output_dir, f"{intermediate_base}_basic{ext}")
            repaired_mesh.export(intermediate_path)
            if verbose:
                print(f"Mesh nach grundlegender Reparatur gespeichert in: {intermediate_path}")

        # Zähle non-manifold Kanten nach grundlegender Reparatur
        edges_by_count = trimesh.grouping.group_rows(repaired_mesh.edges_sorted, require_count=1)
        non_manifold_edges_intermediate = len(edges_by_count)

        if verbose:
            print(f"Non-manifold Kanten nach grundlegender Reparatur: {non_manifold_edges_intermediate}")
            print(f"Ist wasserdicht nach grundlegender Reparatur: {repaired_mesh.is_watertight}")

        # Schritt 2: Fortgeschrittene Reparaturen
        repaired_mesh = repair_advanced(repaired_mesh, verbose)

        # Zähle non-manifold Kanten nach fortgeschrittener Reparatur
        edges_by_count = trimesh.grouping.group_rows(repaired_mesh.edges_sorted, require_count=1)
        non_manifold_edges_after = len(edges_by_count)

        if verbose:
            print(f"Non-manifold Kanten nach fortgeschrittener Reparatur: {non_manifold_edges_after}")
            print(f"Ist wasserdicht nach fortgeschrittener Reparatur: {repaired_mesh.is_watertight}")

        # Mesh speichern
        repaired_mesh.export(output_file)
        if verbose:
            print(f"Repariertes Mesh gespeichert in: {output_file}")

        return True, non_manifold_edges_before, non_manifold_edges_after

    except Exception as e:
        print(f"Fehler beim Reparieren des Mesh: {str(e)}")
        print(f"Stack-Trace: {sys.exc_info()}")
        return False, 0, 0


def main():
    parser = argparse.ArgumentParser(description='Repariert non-manifold Kanten in STL-Dateien')
    parser.add_argument('input', help='Pfad zur Eingabe-STL-Datei')
    parser.add_argument('-o', '--output', help='Pfad zur Ausgabe-STL-Datei')
    parser.add_argument('-v', '--verbose', action='store_true', help='Ausführliche Ausgabe')
    parser.add_argument('-i', '--intermediate', action='store_true',
                        help='Speichert Zwischenschritte der Reparatur')
    parser.add_argument('-t', '--timestamp', action='store_true',
                        help='Zeitstempel (yyyy-MM-dd-HH-mm-ss) an Ausgabedatei anfügen')

    args = parser.parse_args()

    # Überprüfe, ob die Eingabedatei existiert
    if not os.path.exists(args.input):
        print(f"Fehler: Datei '{args.input}' nicht gefunden!")
        sys.exit(1)

    # Wenn keine Ausgabedatei angegeben wurde, generiere einen Namen
    if args.output is None:
        base, ext = os.path.splitext(args.input)
        args.output = f"{os.path.basename(base)}_repaired{ext}"

    print(f"STL Repair Tool - Repariere non-manifold Kanten")
    print(f"Eingabedatei: {args.input}")
    print(f"Ausgabedatei: {args.output}")

    # Starte Reparatur
    success, before_count, after_count = repair_mesh(
        args.input, args.output, args.verbose, args.intermediate, args.timestamp
    )

    if success:
        print(f"\nReparatur abgeschlossen!")
        print(f"Non-manifold Kanten vorher: {before_count}")
        print(f"Non-manifold Kanten nachher: {after_count}")

        if after_count == 0:
            print("\nDas Modell wurde erfolgreich repariert und sollte jetzt in Bambu Studio importiert werden können.")
        elif after_count < before_count:
            print("\nDas Modell wurde teilweise repariert, enthält aber noch einige non-manifold Kanten.")
            print("Es könnte in Bambu Studio funktionieren oder weitere Reparaturen benötigen.")
        else:
            print("\nDie Reparatur konnte die non-manifold Kanten nicht reduzieren.")
    else:
        print("\nReparatur fehlgeschlagen. Details wurden oben ausgegeben.")
        print("Versuche, das Modell mit einem Drittanbieter-Tool zu reparieren.")


if __name__ == "__main__":
    main()