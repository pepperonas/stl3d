#!/usr/bin/env python3
import os

import numpy as np
import trimesh
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter


def text_to_stl(text, font_path=None, font_size=60, thickness=10, filename="text_3d",
                output_dir="output/text-to-stl", add_base=True, base_height=2.0,
                mirror_text=False, blur_radius=0.0):
    """
    Konvertiert Text zu einer STL-Datei mit Trimesh und PIL

    Args:
        text: Der zu konvertierende Text
        font_path: Pfad zur Schriftartdatei (ttf)
        font_size: Die Größe der Schrift in Punkten
        thickness: Die Dicke/Tiefe des Textes in mm
        filename: Der Name der Ausgabedatei (ohne .stl)
        output_dir: Verzeichnis für die Ausgabedatei
        add_base: Ob eine Bodenplatte hinzugefügt werden soll
        base_height: Höhe der Bodenplatte in mm
        mirror_text: Ob der Text gespiegelt werden soll
        blur_radius: Stärke der Weichzeichnung (0 für keine Weichzeichnung)
    """
    # Ausgabeverzeichnis erstellen, falls es nicht existiert
    os.makedirs(output_dir, exist_ok=True)

    # Bildgröße basierend auf Textlänge schätzen
    width = max(len(text) * font_size, 200)
    height = max(font_size * 2, 100)

    # Weißes Bild erstellen
    image = Image.new('L', (width, height), color=255)
    draw = ImageDraw.Draw(image)

    # Schriftart laden
    try:
        if font_path:
            font = ImageFont.truetype(font_path, font_size)
        else:
            # Fallback zu Standard-Schriftart
            font = ImageFont.truetype('/Library/Fonts/Arial.ttf', font_size)
    except Exception as e:
        print(f"Fehler beim Laden der Schriftart: {e}")
        # Wenn keine Schriftart gefunden wird, Standardschriftart verwenden
        font = ImageFont.load_default()

    # Text zentrieren
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    x = (width - text_width) // 2
    y = (height - text_height) // 2

    # Text schwarz auf weiß zeichnen
    draw.text((x, y), text, font=font, fill=0)

    # Weichzeichnung anwenden, wenn gewünscht
    if blur_radius > 0:
        image = image.filter(ImageFilter.GaussianBlur(radius=blur_radius))
        print(f"Weichzeichnung mit Radius {blur_radius} angewendet.")

    # Wenn Text nicht gespiegelt werden soll, Bild horizontal spiegeln
    if not mirror_text:
        image = ImageOps.mirror(image)

    # Bild zu Numpy-Array konvertieren
    img_array = np.array(image)

    # WICHTIG: Neue Methode zur Textextraktion
    if not add_base:
        # Schwellenwert anwenden - nur Text behalten, Hintergrund entfernen
        # 200 ist ein guter Schwellenwert für Text (0=schwarz, 255=weiß)
        threshold = 200
        # Maske erstellen, wo Pixel dunkler als Schwellenwert sind (Text)
        mask = img_array < threshold

        # Höhenfeld nur für Textpixel erstellen, Rest auf 0 setzen
        height_field = np.zeros_like(img_array)
        height_field[mask] = 255 - img_array[mask]
    else:
        # Höhenfeld für alle Pixel erstellen (Text und Hintergrund)
        height_field = 255 - img_array

    # X und Y Koordinaten erstellen
    x_grid, y_grid = np.meshgrid(
        np.arange(width) / 100 * 25.4,  # X-Koordinaten in mm
        np.arange(height) / 100 * 25.4  # Y-Koordinaten in mm
    )

    # Z-Koordinaten aus dem Höhenfeld
    z_grid = height_field / 255.0 * thickness

    if not add_base:
        # Vertices nur für Textpixel erstellen
        # Finde alle Nicht-Null-Punkte im Höhenfeld
        mask = z_grid > 0

        # Wenn keine Textpixel gefunden wurden, Fehler ausgeben
        if not np.any(mask):
            print("FEHLER: Kein Text gefunden oder Schwellenwert zu niedrig.")
            return None

        # Vertices für Textpixel erstellen
        text_vertices = []
        text_faces = []

        # Finde alle Indizes, wo Maske True ist
        y_indices, x_indices = np.where(mask)

        # Erzeuge Mesh nur für diese Bereiche
        vertex_count = 0
        vertex_map = {}  # Speichert Zuordnung (y, x) -> vertex_index

        for i, (y, x) in enumerate(zip(y_indices, x_indices)):
            # Prüfe, ob Pixel Teil eines zusammenhängenden Bereichs ist
            # (hat mindestens einen Nachbarn, der auch Text ist)
            has_neighbors = False
            for ny, nx in [(y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)]:
                if 0 <= ny < height and 0 <= nx < width and mask[ny, nx]:
                    has_neighbors = True
                    break

            if has_neighbors:
                # Erstelle zwei Dreiecke für jedes Pixel (Ober- und Unterseite)
                # Obere Ecken
                top_left = vertex_count
                text_vertices.append([x_grid[y, x], y_grid[y, x], z_grid[y, x]])
                vertex_count += 1

                top_right = vertex_count
                text_vertices.append([x_grid[y, x] + 0.254, y_grid[y, x], z_grid[y, x]])
                vertex_count += 1

                bottom_left = vertex_count
                text_vertices.append([x_grid[y, x], y_grid[y, x] + 0.254, z_grid[y, x]])
                vertex_count += 1

                bottom_right = vertex_count
                text_vertices.append([x_grid[y, x] + 0.254, y_grid[y, x] + 0.254, z_grid[y, x]])
                vertex_count += 1

                # Untere Ecken (z=0)
                base_top_left = vertex_count
                text_vertices.append([x_grid[y, x], y_grid[y, x], 0])
                vertex_count += 1

                base_top_right = vertex_count
                text_vertices.append([x_grid[y, x] + 0.254, y_grid[y, x], 0])
                vertex_count += 1

                base_bottom_left = vertex_count
                text_vertices.append([x_grid[y, x], y_grid[y, x] + 0.254, 0])
                vertex_count += 1

                base_bottom_right = vertex_count
                text_vertices.append([x_grid[y, x] + 0.254, y_grid[y, x] + 0.254, 0])
                vertex_count += 1

                # Oberseite (zwei Dreiecke)
                text_faces.append([top_left, top_right, bottom_left])
                text_faces.append([bottom_left, top_right, bottom_right])

                # Unterseite (zwei Dreiecke)
                text_faces.append([base_top_left, base_bottom_left, base_top_right])
                text_faces.append([base_bottom_left, base_bottom_right, base_top_right])

                # Seitenwände (je zwei Dreiecke pro Seite)
                # Vorne
                text_faces.append([top_left, base_top_left, top_right])
                text_faces.append([top_right, base_top_left, base_top_right])

                # Rechts
                text_faces.append([top_right, base_top_right, bottom_right])
                text_faces.append([bottom_right, base_top_right, base_bottom_right])

                # Hinten
                text_faces.append([bottom_right, base_bottom_right, bottom_left])
                text_faces.append([bottom_left, base_bottom_right, base_bottom_left])

                # Links
                text_faces.append([bottom_left, base_bottom_left, top_left])
                text_faces.append([top_left, base_bottom_left, base_top_left])

        # Vertices und Faces in NumPy-Arrays umwandeln
        vertices = np.array(text_vertices)
        faces = np.array(text_faces)
    else:
        # Normale Höhenfeld-zu-Mesh-Methode für alle Pixel
        # Vertices erstellen
        vertices = np.column_stack([
            x_grid.flatten(),
            y_grid.flatten(),
            z_grid.flatten()
        ])

        # Faces (Dreiecke) erstellen
        faces = []
        for y in range(height - 1):
            for x in range(width - 1):
                # Index der vier Eckpunkte eines Quadrats
                i = y * width + x
                j = y * width + (x + 1)
                k = (y + 1) * width + x
                l = (y + 1) * width + (x + 1)

                # Zwei Dreiecke pro Quadrat
                faces.append([i, j, k])
                faces.append([j, l, k])

        faces = np.array(faces)

    # Mesh erstellen
    if len(vertices) > 0 and len(faces) > 0:
        mesh = trimesh.Trimesh(vertices=vertices, faces=faces)

        # Basis (Sockel) hinzufügen wenn gewünscht
        if add_base and base_height > 0:
            print("Erstelle Bodenplatte...")
            # Einen Quader für die Basis erstellen
            min_bounds = mesh.bounds[0]
            max_bounds = mesh.bounds[1]
            base_dimensions = [
                max_bounds[0] - min_bounds[0],  # Breite
                max_bounds[1] - min_bounds[1],  # Länge
                base_height  # Höhe
            ]

            # Box erstellen
            base_mesh = trimesh.creation.box(base_dimensions)

            # Box unter dem Text positionieren
            base_mesh.apply_translation([
                min_bounds[0],
                min_bounds[1],
                min_bounds[2] - base_height
            ])

            # Meshs zusammenführen
            final_mesh = trimesh.util.concatenate([mesh, base_mesh])
            print("Bodenplatte erstellt.")
        else:
            print("Keine Bodenplatte hinzugefügt.")
            final_mesh = mesh

        # STL speichern im angegebenen Verzeichnis
        output_path = os.path.join(output_dir, f"{filename}.stl")
        final_mesh.export(output_path)

        print(f"STL-Datei erfolgreich erstellt: {output_path}")
        return output_path
    else:
        print("Fehler: Konnte kein gültiges Mesh erstellen.")
        return None


if __name__ == "__main__":
    # Beispielaufruf
    text = input("Gib den Text ein: ")

    # Standard-Fontpfad für macOS
    default_font = '/Library/Fonts/Arial.ttf'
    custom_font = input(f"Gib den Pfad zur Schriftart ein (leer für {default_font}): ") or default_font

    size = int(input("Gib die Schriftgröße ein (Standard: 120): ") or "120")
    thickness = float(input("Gib die Dicke in mm ein (Standard: 10): ") or "10")

    add_base = False

    if add_base:
        base_height = float(input("Höhe der Bodenplatte in mm (Standard: 2.0): ") or "2.0")
    else:
        base_height = 0.0

    blur_radius = float(
        input("Stärke der Weichzeichnung (0 für keine, 1-5 für leicht bis stark, Standard: 0): ") or "0")

    mirror = False

    filename = input("Gib den Dateinamen ein (ohne .stl): ") or "text_3d"
    output_dir = "output/text-to-stl"

    text_to_stl(text, custom_font, size, thickness, filename, output_dir, add_base, base_height, mirror, blur_radius)
