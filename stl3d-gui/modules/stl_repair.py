"""
Modul zur Reparatur von STL-Dateien für den 3D-Druck
"""

import os
import datetime
import numpy as np
import trimesh
from utils.file_utils import ensure_directory_exists

def create_output_dir(script_name="stl-repair"):
    """
    Erstellt das Ausgabeverzeichnis basierend auf dem Skriptnamen.
    
    Args:
        script_name: Name des Skripts/Moduls
        
    Returns:
        Pfad zum Ausgabeverzeichnis
    """
    output_dir = os.path.join("output", script_name)
    ensure_directory_exists(output_dir)
    return output_dir

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

    # 3. Entferne degenerierte Dreiecke (Dreiecke mit Null-Fläche)
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

def make_watertight(mesh_data, max_hole_size=None, timeout=30, verbose=False):
    """
    Aggressive Funktion zum Wasserdichtmachen eines Meshes
    
    Args:
        mesh_data: Das zu reparierende Trimesh-Objekt
        max_hole_size: Maximale Größe der zu füllenden Löcher (None = alle Größen)
        timeout: Maximale Zeit in Sekunden für rechenintensive Operationen
        verbose: Wenn True, werden Fortschrittsinformationen ausgegeben
        
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
        if verbose:
            print("Mesh ist nach dem Löcher-Füllen bereits wasserdicht!")
        return mesh_data

    # 3. Versuche vereinfachte Reparatur, wenn das Mesh noch nicht wasserdicht ist
    if not mesh_data.is_watertight:
        if verbose:
            print("Versuche vereinfachte Reparatur...")

        # Entferne ungenutzte Vertices und isolierte Komponenten
        mesh_data.remove_unreferenced_vertices()

        # Extrahiere die größte zusammenhängende Komponente
        components = mesh_data.split(only_watertight=False)
        if len(components) > 1:
            if verbose:
                print(f"Mesh besteht aus {len(components)} getrennten Komponenten")
            # Wähle die größte Komponente
            largest_component = sorted(components, key=lambda m: len(m.faces), reverse=True)[0]
            mesh_data = largest_component
            if verbose:
                print(f"Größte Komponente ausgewählt: {len(mesh_data.faces)} Flächen")

        # Normalen korrigieren
        mesh_data.fix_normals()

        # Prüfe erneut, ob das Mesh wasserdicht ist
        if mesh_data.is_watertight:
            if verbose:
                print("Mesh ist nach vereinfachter Reparatur wasserdicht!")
            return mesh_data

    # 4. Versuche eine Konvexhülle, wenn die Zeit es erlaubt
    # Dies ist schneller als Voxelisierung und funktioniert in den meisten Fällen
    if not mesh_data.is_watertight and (time.time() - start_time) < timeout:
        try:
            if verbose:
                print("Erstelle Konvexhülle...")
            hull_mesh = mesh_data.convex_hull
            if hull_mesh is not None and len(hull_mesh.faces) > 0:
                if verbose:
                    print("Konvexhülle erfolgreich erstellt")
                return hull_mesh
        except Exception as e:
            if verbose:
                print(f"Convex-Hull-Erstellung fehlgeschlagen: {str(e)}")

    # 5. Wenn die Zeit es erlaubt und die Konvexhülle fehlgeschlagen ist,
    # versuche als letzte Option eine Voxelisierung
    if not mesh_data.is_watertight and (time.time() - start_time) < timeout:
        try:
            if verbose:
                print("Erstelle Voxel-Darstellung (kann einige Sekunden dauern)...")
            # Verwende eine gröbere Voxel-Auflösung für schnellere Verarbeitung
            # Berechne eine vernünftige Voxelgröße basierend auf der Modellgröße
            voxel_size = max(mesh_data.bounding_box.extents) / 50.0
            if verbose:
                print(f"Verwende Voxelgröße: {voxel_size}")

            voxel = mesh_data.voxelized(pitch=voxel_size)

            if verbose:
                print("Erzeuge Mesh aus Voxel-Darstellung...")
            watertight_mesh = voxel.marching_cubes

            if watertight_mesh is not None and len(watertight_mesh.faces) > 0:
                if verbose:
                    print("Voxel-Reparatur erfolgreich")
                return watertight_mesh
        except Exception as e:
            if verbose:
                print(f"Voxel-Reparatur fehlgeschlagen: {str(e)}")

    # 6. Wenn alle Versuche fehlschlagen oder das Timeout erreicht wird,
    # gib das bestmögliche Mesh zurück und warne den Benutzer
    if time.time() - start_time >= timeout:
        if verbose:
            print(f"Zeitlimit von {timeout} Sekunden erreicht. Breche aggressive Reparatur ab.")

    if verbose:
        print("Konnte keine vollständig wasserdichte Version erstellen. Gebe bestmögliches Mesh zurück.")
    return mesh_data

def fix_stl(input_file, output_path=None, verbose=False, aggressive=True, clean_model_flag=True, 
           max_iterations=2, timeout=30, use_timestamp=False):
    """
    Lädt eine STL-Datei, repariert sie und speichert die reparierte Version.
    
    Args:
        input_file: Pfad zur Eingabe-STL-Datei
        output_path: Pfad zur Ausgabe-STL-Datei (None für automatische Benennung)
        verbose: Wenn True, werden detaillierte Informationen ausgegeben
        aggressive: Wenn True, werden aggressive Reparaturmethoden angewendet
        clean_model_flag: Wenn True, werden Rahmen und Artefakte entfernt
        max_iterations: Maximale Anzahl von Reparaturversuchen
        timeout: Maximale Zeit in Sekunden für rechenintensive Operationen
        use_timestamp: Wenn True, wird der Ausgabedatei ein Zeitstempel hinzugefügt
        
    Returns:
        Der vollständige Pfad zur reparierten STL-Datei
    """
    # Ausgabeverzeichnis erstellen
    output_dir = create_output_dir()
    
    # Wenn kein Ausgabepfad angegeben ist, erstelle einen Standard-Ausgabepfad
    if output_path is None:
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        output_path = os.path.join(output_dir, f"{base_name}_repaired.stl")
    else:
        output_path = os.path.join(output_dir, os.path.basename(output_path))

    # Zeitstempel einfügen, falls gewünscht
    if use_timestamp:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        base_name, ext = os.path.splitext(output_path)
        output_path = f"{base_name}_{timestamp}{ext}"

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
        if clean_model_flag:
            if verbose:
                print("Säubere das Modell von Artefakten...")
            mesh_data = clean_model(mesh_data, verbose)

        # Repariere das Mesh
        if verbose:
            print("Repariere Mesh...")

        # Iterativer Reparaturprozess
        iteration = 0
        repaired_mesh = mesh_data

        while (not repaired_mesh.is_watertight or not repaired_mesh.is_winding_consistent) and iteration < max_iterations:
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
            repaired_mesh = make_watertight(repaired_mesh, timeout=timeout, verbose=verbose)

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
        repaired_mesh.export(output_path)

        if verbose:
            print(f"Repariertes Mesh gespeichert als: {output_path}")

        return output_path

    except Exception as e:
        print(f"Fehler beim Verarbeiten der STL-Datei: {str(e)}")
        raise

def validate_stl(file_path, verbose=False):
    """
    Überprüft, ob die STL-Datei für den 3D-Druck geeignet ist
    
    Args:
        file_path: Pfad zur STL-Datei
        verbose: Wenn True, werden detaillierte Informationen ausgegeben
        
    Returns:
        Tupel (bool, dict) - True wenn gültig, sowie ein Dictionary mit Statistiken
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

        if verbose:
            print(f"STL-Validierung für {file_path}:")
            print(f"Vertices: {stats['vertices']}")
            print(f"Faces: {stats['faces']}")
            print(f"Ist wasserdicht: {stats['is_watertight']}")
            print(f"Hat konsistente Winding-Reihenfolge: {stats['is_winding_consistent']}")
            print(f"Ist leer: {stats['is_empty']}")
            print(f"Volumen: {stats['volume']}")
            print(f"Euler-Zahl: {stats['euler_number']}")
            print(f"Gesamturteil: {'Gültig' if is_valid else 'Ungültig'} für 3D-Druck")

        return is_valid, stats

    except Exception as e:
        print(f"Fehler beim Validieren der STL-Datei: {str(e)}")
        return False, {}
