"""
Modul zur Konvertierung von Bildern in STL-Dateien
"""

import os
import datetime
import numpy as np
from PIL import Image, ImageFilter
from stl import mesh
from utils.file_utils import ensure_directory_exists

def create_output_dir(script_name="image-to-stl"):
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

def image_to_stl(image_path, output_path, width=None, height=None,
                 max_height=5.0, base_height=1.0, invert=False,
                 smooth=1, threshold=None, border=2, max_size=170,
                 object_only=False, rotate_x=False, rotate_y=False, rotate_z=False, use_timestamp=False):
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

    Returns:
        Der vollständige Pfad zur erstellten STL-Datei
    """
    # Ausgabeverzeichnis erstellen
    output_dir = create_output_dir()

    # Zeitstempel einfügen, falls gewünscht
    if isinstance(output_path, str) and output_path.endswith(".stl"):
        base_name, ext = os.path.splitext(os.path.basename(output_path))

        # Zeitstempel
        if use_timestamp:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
            base_name = f"{base_name}_{timestamp}"

        # Ausgabepfad anpassen
        output_path = os.path.join(output_dir, f"{base_name}{ext}")

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
    object_mask = None
    if object_only and has_scipy:
        # Wir brauchen ein Threshold, wenn keiner angegeben ist
        if threshold is None:
            # Standardwert für bessere Erkennung
            effective_threshold = 50 if invert else 150
        else:
            effective_threshold = threshold

        # Maske für Bereiche über dem Threshold erstellen
        orig_data = np.array(img, dtype=np.float32)
        if invert:
            object_mask = orig_data < effective_threshold
        else:
            object_mask = orig_data > effective_threshold

        # AGGRESSIVE RAHMENENTFERNUNG
        # Speichere die ursprüngliche Maske für spätere Verarbeitung
        original_mask = object_mask.copy()

        # Schritt 1: Führe eine Erosion durch, um den äußeren Rand zu entfernen
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
        object_mask = ndimage.binary_dilation(object_mask, structure=np.ones((2, 2), dtype=bool), iterations=1)

        # Schritt 6: Stelle sicher, dass wir nicht über die ursprüngliche Maske hinausgehen
        object_mask = np.logical_and(object_mask, original_mask)

        # Schritt 7: Entferne explizit den Rahmen durch Maskierung des Randes
        padding = 3  # Größerer Abstand für bessere Ergebnisse
        border_mask = np.ones((rows, cols), dtype=bool)
        border_mask[padding:rows - padding, padding:cols - padding] = False
        object_mask = np.logical_and(object_mask, ~border_mask)

    # Marching Cubes für object_only-Modus
    if object_only and has_skimage and object_mask is not None:
        from skimage import measure

        # 3D-Volume erstellen
        z_scale = max_height
        z_size = int(max_height * 2)
        volume = np.zeros((rows, cols, z_size), dtype=bool)

        # Volume basierend auf Höhenkarte füllen
        for i in range(rows):
            for j in range(cols):
                if object_mask[i, j]:
                    z_height = int((height_map[i, j] - base_height) / max_height * (z_size - 1))
                    volume[i, j, 0:max(1, z_height)] = True

        # Marching Cubes anwenden
        verts, faces, normals, values = measure.marching_cubes(volume, level=0.5)

        # Vertices skalieren
        verts[:, 0] = verts[:, 0]  # X bleibt gleich
        verts[:, 1] = rows - 1 - verts[:, 1]  # Y umkehren
        verts[:, 2] = verts[:, 2] / (z_size - 1) * max_height  # Z skalieren

        # Vertices und Faces übernehmen
        vertices = verts
        faces = faces[:, ::-1]  # Faces umkehren für korrekte Orientierung
    else:
        # Fallback-Methode, wenn object_only aktiv ist aber libs fehlen
        if object_only and not (has_skimage and object_mask is not None):
            object_only = False  # Deaktiviere object_only im Fallback
            print("Object-only-Modus deaktiviert, da erforderliche Bibliotheken fehlen.")

        # Vertices für die Oberseite erzeugen (Höhenkarte)
        for i in range(rows):
            for j in range(cols):
                # Im object_only-Modus nur Punkte für das Objekt hinzufügen
                if not object_only or (object_only and object_mask is not None and object_mask[i, j]):
                    vertices.append([j, (rows - 1) - i, height_map[i, j]])

        # Wenn wir nicht im object_only-Modus sind, erstelle Unterseite
        if not object_only:
            # Vertices für die Unterseite erzeugen (flache Basis)
            for i in range(rows):
                for j in range(cols):
                    vertices.append([j, (rows - 1) - i, 0])

            # Dreiecke für das Mesh erzeugen
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

    return output_path