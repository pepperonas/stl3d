#!/usr/bin/env python3
"""
Bild zu STL Konverter - Wandelt ein Bild in eine STL-Datei für 3D-Druck um
"""

import numpy as np
import argparse
from PIL import Image, ImageFilter
from stl import mesh
import os
import datetime


def image_to_stl(image_path, output_path, width=None, height=None,
                 max_height=5.0, base_height=1.0, invert=False,
                 smooth=1, threshold=None, border=2, max_size=170,
                 object_only=False, rotate_x=False, rotate_y=False, rotate_z=False):
    """
    Konvertiert ein Bild in eine STL-Datei

    Args:
        image_path: Pfad zum Eingabebild
        output_path: Pfad zur Ausgabe-STL-Datei
        width: Breite des 3D-Modells in mm (None = proportional zur Höhe)
        height: Höhe des 3D-Modells in mm (None = original Bildverhältnis)
        max_height: Maximale Höhe des Reliefs in mm
        base_height: Dicke der Basis in mm
        invert: Wenn True, werden helle Bereiche tiefer statt höher
        smooth: Anzahl der Glättungsdurchgänge (0 für keine Glättung)
        threshold: Schwellenwert für Hintergrunderkennung (0-255, None = keine Erkennung)
        border: Randbreite in Pixeln
        max_size: Maximale Dimension in mm
        object_only: Nur das Objekt ohne Grundplatte erstellen
        rotate_x: Wenn True, wird das Modell um 90 Grad um die X-Achse gedreht
        rotate_y: Wenn True, wird das Modell um 90 Grad um die Y-Achse gedreht
        rotate_z: Wenn True, wird das Modell um 90 Grad um die Z-Achse gedreht
    """
    # Benötigte Bibliotheken importieren
    try:
        from scipy import ndimage
        has_scipy = True
    except ImportError:
        has_scipy = False
        print("WARNUNG: SciPy nicht installiert. Einige Funktionen werden deaktiviert.")
        print("Für bessere Ergebnisse installiere SciPy: pip install scipy")

    if object_only:
        try:
            from skimage import measure
            has_skimage = True
        except ImportError:
            has_skimage = False
            print("WARNUNG: scikit-image nicht installiert. Verwende alternativen Ansatz.")
            print("Für bessere Ergebnisse installiere scikit-image: pip install scikit-image")

    # Bild laden und in Graustufen konvertieren
    img = Image.open(image_path)

    # Alpha-Kanal verarbeiten, falls vorhanden (transparent wird weiß)
    if img.mode == 'RGBA':
        # Weißen Hintergrund erstellen
        background = Image.new('RGBA', img.size, (255, 255, 255, 255))
        # Bild auf weißen Hintergrund legen
        img = Image.alpha_composite(background, img)

    # In Graustufen konvertieren
    img = img.convert('L')

    # Größe anpassen unter Berücksichtigung der maximalen Größe
    orig_width, orig_height = img.size

    # Wenn keine Dimensionen angegeben sind, verwende die Originalgröße
    # und begrenzte sie gemäß max_size
    if width is None and height is None:
        # Bestimme die längere Seite und skaliere entsprechend
        aspect_ratio = orig_width / orig_height

        if orig_width >= orig_height:
            # Breiter als hoch - Breite ist die begrenzende Dimension
            width = min(orig_width, max_size)
            height = int(width / aspect_ratio)
        else:
            # Höher als breit - Höhe ist die begrenzende Dimension
            height = min(orig_height, max_size)
            width = int(height * aspect_ratio)
    else:
        # Wenn eine Dimension angegeben ist, berechne die andere
        if width is None:
            width = int(height * orig_width / orig_height)
        if height is None:
            height = int(width * orig_height / orig_width)

        # Prüfe, ob die berechneten Dimensionen die maximale Größe überschreiten
        if width > max_size or height > max_size:
            if width >= height:
                # Breite begrenzen und Höhe anpassen
                scale_factor = max_size / width
                width = max_size
                height = int(height * scale_factor)
            else:
                # Höhe begrenzen und Breite anpassen
                scale_factor = max_size / height
                height = max_size
                width = int(width * scale_factor)

    # Bild entsprechend skalieren
    img = img.resize((width, height), Image.LANCZOS)

    # Glättung anwenden
    for _ in range(smooth):
        img = img.filter(ImageFilter.SMOOTH)

    # In NumPy-Array konvertieren
    height_map = np.array(img, dtype=np.float32)

    # Invertieren, falls gewünscht
    if invert:
        height_map = 255.0 - height_map

    # Höhendaten normalisieren
    height_map = (height_map / 255.0) * max_height + base_height

    # Hintergrund entfernen, falls Schwellenwert angegeben
    if threshold is not None:
        orig_data = np.array(img, dtype=np.float32)
        if invert:
            mask = orig_data >= threshold
        else:
            mask = orig_data <= threshold
        height_map[mask] = base_height

    # Dimensionen des Arrays
    rows, cols = height_map.shape

    # Rand hinzufügen, falls angegeben und nicht im object_only-Modus
    if border > 0 and not object_only:
        bordered_height_map = np.ones((rows + 2 * border, cols + 2 * border), dtype=np.float32) * base_height
        bordered_height_map[border:border + rows, border:border + cols] = height_map
        height_map = bordered_height_map
        rows, cols = height_map.shape

    # Mesh erstellen
    vertices = []
    faces = []

    # Im object_only-Modus, Maske erstellen für Bereiche über der Basis
    if object_only:
        # Wir brauchen ein Threshold, wenn keiner angegeben ist
        if threshold is None:
            # Standardwert: 20% über der Basis
            effective_threshold = 50 if invert else 150  # Angepasste Werte für bessere Erkennung
        else:
            effective_threshold = threshold

        # Maske für Bereiche über dem Threshold erstellen
        orig_data = np.array(img, dtype=np.float32)
        if invert:
            object_mask = orig_data < effective_threshold
        else:
            object_mask = orig_data > effective_threshold

        # Morphologische Operationen anwenden, um Lücken zu schließen
        # und kleine isolierte Bereiche zu entfernen
        from scipy import ndimage

        # AGGRESSIVE RAHMENENTFERNUNG
        # Speichere die ursprüngliche Maske für spätere Verarbeitung
        original_mask = object_mask.copy()

        # Schritt 1: Führe eine Erosion durch, um den äußeren Rand zu entfernen
        # Dieser Schritt entfernt effektiv mehrere Pixelschichten vom Rand
        border_removal_kernel = np.ones((3, 3), dtype=bool)  # Größerer Kernel für stärkere Erosion
        object_mask = ndimage.binary_erosion(object_mask, structure=border_removal_kernel, iterations=3)

        # Schritt 2: Dann führe ein Closing aus, um Löcher zu schließen
        object_mask = ndimage.binary_closing(object_mask, structure=np.ones((2, 2), dtype=bool), iterations=1)

        # Schritt 3: Fülle kleine Löcher
        object_mask = ndimage.binary_fill_holes(object_mask)

        # Schritt 4: Finde zusammenhängende Komponenten und behalte nur die größte
        labeled_array, num_features = ndimage.label(object_mask)
        if num_features > 1:
            component_sizes = np.bincount(labeled_array.ravel())[1:]
            largest_component = np.argmax(component_sizes) + 1
            object_mask = labeled_array == largest_component

        # Schritt 5: Führe eine leichte Dilatation aus, aber NICHT bis zum ursprünglichen Rand
        # Dies stellt sicher, dass wir nicht wieder bis zum problematischen Rahmen expandieren
        object_mask = ndimage.binary_dilation(object_mask, structure=np.ones((2, 2), dtype=bool), iterations=1)

        # Schritt 6: Stelle sicher, dass wir nicht über die ursprüngliche Maske hinausgehen
        object_mask = np.logical_and(object_mask, original_mask)

        # Schritt 7: Entferne explizit den Rahmen durch Maskierung des Randes
        # Erstelle eine Maske, die den Rand des Bildes repräsentiert
        padding = 3  # Größerer Abstand für bessere Ergebnisse
        border_mask = np.ones((rows, cols), dtype=bool)
        border_mask[padding:rows - padding, padding:cols - padding] = False

        # Entferne alle Objekte, die den Rand berühren
        object_mask = np.logical_and(object_mask, ~border_mask)

    # Vertices für die Oberseite erzeugen (Höhenkarte)
    for i in range(rows):
        for j in range(cols):
            # Im object_only-Modus nur Punkte für das Objekt hinzufügen
            if not object_only or (object_only and object_mask[i, j]):
                vertices.append([j, (rows - 1) - i, height_map[i, j]])

    # Wenn wir nicht im object_only-Modus sind, erstelle Unterseite
    if not object_only:
        # Vertices für die Unterseite erzeugen (flache Basis)
        for i in range(rows):
            for j in range(cols):
                vertices.append([j, (rows - 1) - i, 0])

    # Logik für die Dreiecke im object_only Modus ist komplexer
    if object_only:
        # Wir verwenden einen alternativen Ansatz: Marching Cubes-Algorithmus
        # Dieser erzeugt ein wasserdichtes Mesh aus einer volumetrischen Darstellung
        try:
            from skimage import measure

            # Erstelle ein 3D-Volume aus dem Höhenfeld
            # Füge eine Z-Dimension hinzu
            z_scale = max_height  # Skalierungsfaktor für Z-Achse
            z_size = int(max_height * 2)  # Anzahl der Z-Schichten

            # Erstelle 3D-Volume
            volume = np.zeros((rows, cols, z_size), dtype=bool)

            # Fülle das Volume basierend auf der Höhenkarte
            for i in range(rows):
                for j in range(cols):
                    # Prüfe, ob der Pixel zum Objekt gehört
                    if object_mask[i, j]:
                        # Berechne Z-Höhe für diesen Pixel
                        z_height = int((height_map[i, j] - base_height) / max_height * (z_size - 1))
                        # Fülle alle Voxel von 0 bis zur Höhe
                        volume[i, j, 0:max(1, z_height)] = True

            # Wende Marching Cubes an, um eine Oberfläche zu extrahieren
            verts, faces, normals, values = measure.marching_cubes(volume, level=0.5)

            # Skaliere die Vertices zurück, um die richtige Größe zu erhalten
            verts[:, 0] = verts[:, 0]  # X bleibt gleich
            verts[:, 1] = rows - 1 - verts[:, 1]  # Y umkehren
            verts[:, 2] = verts[:, 2] / (z_size - 1) * max_height  # Z auf richtige Höhe skalieren

            # Vertices und Faces übernehmen
            vertices = verts

            # Gesichter müssen umgekehrt werden, um korrekte Ausrichtung zu haben
            faces = faces[:, ::-1]

        except ImportError:
            print("WARNUNG: scikit-image nicht installiert. Verwende alternativen Ansatz.")
            print("Für bessere Ergebnisse installiere scikit-image: pip install scikit-image")

            # Einfacherer Ansatz: Extrusion
            # Erstelle eine obere und untere Ebene und verbinde sie mit Seitenwänden

            # Finde die Kontur des Objekts
            from scipy import ndimage

            # Erstelle ein binäres Bild für die Kontur (Grenze des Objekts)
            kernel = np.ones((2, 2), dtype=bool)
            eroded = ndimage.binary_erosion(object_mask, structure=kernel)
            contour_mask = np.logical_and(object_mask, np.logical_not(eroded))

            # Vertices für die Oberseite
            top_vertices = []
            for i in range(rows):
                for j in range(cols):
                    if object_mask[i, j]:
                        top_vertices.append([j, (rows - 1) - i, height_map[i, j]])

            # Vertices für die Unterseite (flache Basis)
            bottom_vertices = []
            for i in range(rows):
                for j in range(cols):
                    if object_mask[i, j]:
                        bottom_vertices.append([j, (rows - 1) - i, base_height])

            # Kombiniere Vertices
            vertices = top_vertices + bottom_vertices

            # Erstelle Dreiecke für die Oberseite
            top_faces = []
            vertex_map = -np.ones((rows, cols), dtype=np.int32)
            vertex_counter = 0

            # Erstelle Vertex-Map für die Oberseite
            for i in range(rows):
                for j in range(cols):
                    if object_mask[i, j]:
                        vertex_map[i, j] = vertex_counter
                        vertex_counter += 1

            # Dreiecke für die Oberseite
            for i in range(rows - 1):
                for j in range(cols - 1):
                    # Prüfe alle möglichen Dreiecke aus den 4 Punkten
                    v1 = vertex_map[i, j]
                    v2 = vertex_map[i, j + 1]
                    v3 = vertex_map[i + 1, j]
                    v4 = vertex_map[i + 1, j + 1]

                    # Oberes Dreieck, wenn alle Punkte gültig sind
                    if v1 >= 0 and v2 >= 0 and v3 >= 0:
                        top_faces.append([v1, v2, v3])

                    # Unteres Dreieck, wenn alle Punkte gültig sind
                    if v2 >= 0 and v4 >= 0 and v3 >= 0:
                        top_faces.append([v2, v4, v3])

            # Erstelle Dreiecke für die Unterseite (invertiert)
            bottom_faces = []
            for face in top_faces:
                # Unterseite benötigt umgekehrte Orientierung
                bottom_faces.append([face[0] + len(top_vertices),
                                     face[2] + len(top_vertices),
                                     face[1] + len(top_vertices)])

            # Erstelle Dreiecke für die Seitenwände
            side_faces = []

            # Finde Kanten am Rand des Objekts
            for i in range(rows):
                for j in range(cols):
                    if contour_mask[i, j]:
                        v_top = vertex_map[i, j]
                        v_bottom = v_top + len(top_vertices)

                        # Prüfe alle 4 Nachbarn
                        neighbors = []

                        # Rechts
                        if j < cols - 1 and object_mask[i, j + 1]:
                            v_top_right = vertex_map[i, j + 1]
                            v_bottom_right = v_top_right + len(top_vertices)
                            side_faces.append([v_top, v_bottom, v_top_right])
                            side_faces.append([v_bottom, v_bottom_right, v_top_right])

                        # Unten
                        if i < rows - 1 and object_mask[i + 1, j]:
                            v_top_down = vertex_map[i + 1, j]
                            v_bottom_down = v_top_down + len(top_vertices)
                            side_faces.append([v_top, v_top_down, v_bottom])
                            side_faces.append([v_bottom, v_top_down, v_bottom_down])

            # Kombiniere alle Faces
            faces = top_faces + bottom_faces + side_faces
    else:
        # Dreiecke für das Mesh erzeugen wie bisher
        # Oberseite
        for i in range(rows - 1):
            for j in range(cols - 1):
                # Oberes Dreieck
                v1 = i * cols + j
                v2 = i * cols + (j + 1)
                v3 = (i + 1) * cols + j
                faces.append([v1, v2, v3])

                # Unteres Dreieck
                v1 = (i + 1) * cols + j
                v2 = i * cols + (j + 1)
                v3 = (i + 1) * cols + (j + 1)
                faces.append([v1, v2, v3])

        # Anzahl der Vertices in der oberen Hälfte
        top_vertices = rows * cols

        # Unterseite (invertierte Dreiecke)
        for i in range(rows - 1):
            for j in range(cols - 1):
                # Oberes Dreieck (invertiert)
                v1 = top_vertices + i * cols + j
                v2 = top_vertices + (i + 1) * cols + j
                v3 = top_vertices + i * cols + (j + 1)
                faces.append([v1, v2, v3])

                # Unteres Dreieck (invertiert)
                v1 = top_vertices + i * cols + (j + 1)
                v2 = top_vertices + (i + 1) * cols + j
                v3 = top_vertices + (i + 1) * cols + (j + 1)
                faces.append([v1, v2, v3])

        # Seitenwände
        # Vordere Seite
        for j in range(cols - 1):
            v1 = j
            v2 = j + 1
            v3 = top_vertices + j
            faces.append([v1, v2, v3])

            v1 = j + 1
            v2 = top_vertices + j + 1
            v3 = top_vertices + j
            faces.append([v1, v2, v3])

        # Hintere Seite
        for j in range(cols - 1):
            v1 = (rows - 1) * cols + j
            v2 = top_vertices + (rows - 1) * cols + j
            v3 = (rows - 1) * cols + j + 1
            faces.append([v1, v2, v3])

            v1 = (rows - 1) * cols + j + 1
            v2 = top_vertices + (rows - 1) * cols + j
            v3 = top_vertices + (rows - 1) * cols + j + 1
            faces.append([v1, v2, v3])

        # Linke Seite
        for i in range(rows - 1):
            v1 = i * cols
            v2 = top_vertices + i * cols
            v3 = (i + 1) * cols
            faces.append([v1, v2, v3])

            v1 = (i + 1) * cols
            v2 = top_vertices + i * cols
            v3 = top_vertices + (i + 1) * cols
            faces.append([v1, v2, v3])

        # Rechte Seite
        for i in range(rows - 1):
            v1 = i * cols + (cols - 1)
            v2 = (i + 1) * cols + (cols - 1)
            v3 = top_vertices + i * cols + (cols - 1)
            faces.append([v1, v2, v3])

            v1 = (i + 1) * cols + (cols - 1)
            v2 = top_vertices + (i + 1) * cols + (cols - 1)
            v3 = top_vertices + i * cols + (cols - 1)
            faces.append([v1, v2, v3])

    # Vertices und Faces in NumPy-Arrays konvertieren
    vertices = np.array(vertices, dtype=np.float32)
    faces = np.array(faces, dtype=np.uint32)

    # Rotationen anwenden
    if rotate_x:
        # Rotation um die X-Achse um 90 Grad
        y_temp = vertices[:, 1].copy()
        vertices[:, 1] = vertices[:, 2]  # Y = Z
        vertices[:, 2] = -y_temp  # Z = -Y

    if rotate_y:
        # Rotation um die Y-Achse um 90 Grad
        x_temp = vertices[:, 0].copy()
        vertices[:, 0] = vertices[:, 2]  # X = Z
        vertices[:, 2] = -x_temp  # Z = -X

    if rotate_z:
        # Rotation um die Z-Achse um 90 Grad
        x_temp = vertices[:, 0].copy()
        vertices[:, 0] = vertices[:, 1]  # X = Y
        vertices[:, 1] = -x_temp  # Y = -X

    # STL-Modell erstellen
    # Anzahl der Dreiecke
    num_faces = len(faces)

    # STL-Mesh erstellen
    stl_mesh = mesh.Mesh(np.zeros(num_faces, dtype=mesh.Mesh.dtype))

    # Dreiecke zum Mesh hinzufügen
    for i, face in enumerate(faces):
        for j in range(3):
            stl_mesh.vectors[i][j] = vertices[face[j]]

    # STL-Datei speichern
    stl_mesh.save(output_path)

    print(f"STL-Datei erfolgreich erstellt: {output_path}")
    print(f"Modellgröße: {cols}x{rows}x{max_height + base_height} mm")


def main():
    parser = argparse.ArgumentParser(description="Konvertiert ein Bild in eine STL-Datei für 3D-Druck")
    parser.add_argument("input", help="Pfad zum Eingabebild")
    parser.add_argument("-o", "--output", help="Pfad zur Ausgabe-STL-Datei")
    parser.add_argument("--width", type=int, help="Breite des 3D-Modells in mm")
    parser.add_argument("--height", type=int, help="Höhe des 3D-Modells in mm")
    parser.add_argument("--max-height", type=float, default=5.0, help="Maximale Höhe des Reliefs in mm (Standard: 5.0)")
    parser.add_argument("--base-height", type=float, default=1.0, help="Dicke der Basis in mm (Standard: 1.0)")
    parser.add_argument("--invert", action="store_true", help="Invertiere Höhen (helle Bereiche tiefer)")
    parser.add_argument("--smooth", type=int, default=1,
                        help="Anzahl der Glättungsdurchgänge (Standard: 1, 0 für keine Glättung)")
    parser.add_argument("--threshold", type=int,
                        help="Schwellenwert für Hintergrunderkennung (0-255, Standard: keiner)")
    parser.add_argument("--border", type=int, default=0, help="Randbreite in Pixeln (Standard: 0)")
    parser.add_argument("--max-size", type=int, default=300, help="Maximale Dimension in mm (Standard: 300)")
    parser.add_argument("--object-only", action="store_true", help="Nur das Objekt ohne Grundplatte erstellen")
    parser.add_argument("--timestamp", action="store_true",
                        help="Zeitstempel (yyyy-MM-dd-HH-mm-ss) an Ausgabedatei anfügen")

    # Rotationsoptionen
    parser.add_argument("--rotate-x", action="store_true",
                        help="Modell um 90 Grad um die X-Achse drehen")
    parser.add_argument("--rotate-y", action="store_true",
                        help="Modell um 90 Grad um die Y-Achse drehen")
    parser.add_argument("--rotate-z", action="store_true",
                        help="Modell um 90 Grad um die Z-Achse drehen")

    args = parser.parse_args()

    # Erstelle den Ausgabeordner, falls er nicht existiert
    output_dir = "output/image-to-stl"
    os.makedirs(output_dir, exist_ok=True)

    # Standardausgabepfad, wenn keiner angegeben ist
    if args.output is None:
        base_name = os.path.splitext(os.path.basename(args.input))[0]
        # Zeitstempel anfügen wenn gewünscht
        if args.timestamp:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
            base_name = f"{base_name}_{timestamp}"
        args.output = os.path.join(output_dir, f"{base_name}.stl")
    else:
        # Wenn ein benutzerdefinierter Ausgabepfad angegeben wurde
        if args.timestamp:
            # Zeitstempel vor der Dateiendung einfügen
            base, ext = os.path.splitext(args.output)
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
            args.output = f"{base}_{timestamp}{ext}"

        # Stelle sicher, dass er im output_dir-Ordner liegt
        if not os.path.dirname(args.output):  # Wenn kein Verzeichnis angegeben ist
            args.output = os.path.join(output_dir, os.path.basename(args.output))
        elif not args.output.startswith(output_dir):  # Wenn ein anderes Verzeichnis angegeben ist
            # Extrahiere den Dateinamen und füge ihn zum output_dir hinzu
            args.output = os.path.join(output_dir, os.path.basename(args.output))

    # Installationshinweise, wenn --object-only verwendet wird
    if args.object_only:
        print("Hinweis: Für optimale Ergebnisse im object-only-Modus werden diese Bibliotheken benötigt:")
        print("  pip install numpy pillow numpy-stl scipy scikit-image")

    # Bild in STL konvertieren
    image_to_stl(
        args.input,
        args.output,
        width=args.width,
        height=args.height,
        max_height=args.max_height,
        base_height=args.base_height,
        invert=args.invert,
        smooth=args.smooth,
        threshold=args.threshold,
        border=args.border,
        max_size=args.max_size,
        object_only=args.object_only,
        rotate_x=args.rotate_x,
        rotate_y=args.rotate_y,
        rotate_z=args.rotate_z
    )


if __name__ == "__main__":
    main()