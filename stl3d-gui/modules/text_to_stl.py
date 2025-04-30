"""
Modul zur Erstellung von 3D-STL-Dateien aus Text
"""

import os
import numpy as np
import trimesh
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter
from utils.file_utils import ensure_directory_exists


def create_output_dir(script_name="text-to-stl"):
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


def text_to_stl(text, font_path=None, font_size=60, thickness=10, filename="text_3d",
                add_base=True, base_height=2.0, mirror_text=False, blur_radius=0.0,
                use_timestamp=False):
    """
    Konvertiert Text zu einer STL-Datei mit Trimesh und PIL

    Args:
        text: Der zu konvertierende Text
        font_path: Pfad zur Schriftartdatei (ttf)
        font_size: Die Größe der Schrift in Punkten
        thickness: Die Dicke/Tiefe des Textes in mm
        filename: Der Name der Ausgabedatei (ohne .stl)
        add_base: Ob eine Bodenplatte hinzugefügt werden soll
        base_height: Höhe der Bodenplatte in mm
        mirror_text: Ob der Text gespiegelt werden soll
        blur_radius: Stärke der Weichzeichnung (0 für keine Weichzeichnung)
        use_timestamp: Wenn True, wird der Ausgabedatei ein Zeitstempel hinzugefügt

    Returns:
        Der vollständige Pfad zur erstellten STL-Datei oder None bei Fehler
    """
    # Ausgabeverzeichnis erstellen
    output_dir = create_output_dir()

    # Zeitstempel einfügen, falls gewünscht
    if use_timestamp:
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        filename = f"{filename}_{timestamp}"

    # Pfad zur Ausgabedatei
    output_path = os.path.join(output_dir, f"{filename}.stl")

    # Erstelle auch einen Pfad für die Vorschau
    preview_path = os.path.join(output_dir, f"{filename}_preview.png")

    # Bildgröße basierend auf Textlänge schätzen
    width = max(len(text) * font_size, 200)
    height = max(font_size * 2, 100)

    # Weißes Bild erstellen
    image = Image.new('L', (width, height), color=255)
    draw = ImageDraw.Draw(image)

    # Schriftart laden
    try:
        if font_path and os.path.exists(font_path):
            font = ImageFont.truetype(font_path, font_size)
            print(f"Schriftart aus {font_path} geladen")
        else:
            # Fallback-Schriftarten je nach Betriebssystem
            import sys
            if sys.platform == 'darwin':  # macOS
                font_options = [
                    '/Library/Fonts/Arial.ttf',
                    '/System/Library/Fonts/Helvetica.ttc',
                    '/System/Library/Fonts/Times.ttc'
                ]
            elif sys.platform == 'win32':  # Windows
                font_options = [
                    'C:\\Windows\\Fonts\\arial.ttf',
                    'C:\\Windows\\Fonts\\times.ttf',
                    'C:\\Windows\\Fonts\\calibri.ttf'
                ]
            else:  # Linux und andere
                font_options = [
                    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
                    '/usr/share/fonts/TTF/DejaVuSans.ttf',
                    '/usr/share/fonts/truetype/freefont/FreeSans.ttf'
                ]

            font_loaded = False
            for font_option in font_options:
                try:
                    if os.path.exists(font_option):
                        font = ImageFont.truetype(font_option, font_size)
                        print(f"Fallback-Schriftart {font_option} geladen")
                        font_loaded = True
                        break
                except Exception:
                    continue

            if not font_loaded:
                # Wenn keine Schriftart gefunden wird, Standardschriftart verwenden
                font = ImageFont.load_default()
                print("Standard-Schriftart geladen")
    except Exception as e:
        print(f"Fehler beim Laden der Schriftart: {e}")
        # Wenn keine Schriftart gefunden wird, Standardschriftart verwenden
        font = ImageFont.load_default()
        print("Standard-Schriftart geladen")

    # Text zentrieren
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    x = (width - text_width) // 2
    y = (height - text_height) // 2

    # Text schwarz auf weiß zeichnen
    draw.text((x, y), text, font=font, fill=0)

    # Speichere eine Kopie des Bildes für die Vorschau
    image.save(preview_path)
    print(f"Vorschau-Bild gespeichert unter: {preview_path}")

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
        mesh_obj = trimesh.Trimesh(vertices=vertices, faces=faces)

        # Basis (Sockel) hinzufügen wenn gewünscht
        if add_base and base_height > 0:
            print("Erstelle Bodenplatte...")
            # Einen Quader für die Basis erstellen
            min_bounds = mesh_obj.bounds[0]
            max_bounds = mesh_obj.bounds[1]
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
            final_mesh = trimesh.util.concatenate([mesh_obj, base_mesh])
            print("Bodenplatte erstellt.")
        else:
            print("Keine Bodenplatte hinzugefügt.")
            final_mesh = mesh_obj

        # STL speichern im angegebenen Verzeichnis
        final_mesh.export(output_path)

        print(f"STL-Datei erfolgreich erstellt: {output_path}")
        return output_path
    else:
        print("Fehler: Konnte kein gültiges Mesh erstellen.")
        return None


def generate_preview_image(text, font_path=None, font_size=60, output_path=None):
    """
    Erstellt ein Vorschaubild des Textes.

    Args:
        text: Der darzustellende Text
        font_path: Pfad zur Schriftartdatei (ttf)
        font_size: Die Größe der Schrift in Punkten
        output_path: Pfad zum Speichern des Vorschaubilds (optional)

    Returns:
        PIL.Image oder None bei Fehler
    """
    try:
        # Bildgröße basierend auf Textlänge schätzen
        width = max(len(text) * font_size, 200)
        height = max(font_size * 2, 100)

        # Weißes Bild erstellen
        image = Image.new('RGB', (width, height), color=(240, 240, 240))
        draw = ImageDraw.Draw(image)

        # Schriftart laden
        try:
            if font_path and os.path.exists(font_path):
                font = ImageFont.truetype(font_path, font_size)
            else:
                # Fallback-Schriftarten je nach Betriebssystem
                import sys
                if sys.platform == 'darwin':  # macOS
                    font_options = [
                        '/Library/Fonts/Arial.ttf',
                        '/System/Library/Fonts/Helvetica.ttc',
                        '/System/Library/Fonts/Times.ttc'
                    ]
                elif sys.platform == 'win32':  # Windows
                    font_options = [
                        'C:\\Windows\\Fonts\\arial.ttf',
                        'C:\\Windows\\Fonts\\times.ttf',
                        'C:\\Windows\\Fonts\\calibri.ttf'
                    ]
                else:  # Linux und andere
                    font_options = [
                        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
                        '/usr/share/fonts/TTF/DejaVuSans.ttf',
                        '/usr/share/fonts/truetype/freefont/FreeSans.ttf'
                    ]

                font_loaded = False
                for font_option in font_options:
                    try:
                        if os.path.exists(font_option):
                            font = ImageFont.truetype(font_option, font_size)
                            font_loaded = True
                            break
                    except Exception:
                        continue

                if not font_loaded:
                    # Wenn keine Schriftart gefunden wird, Standardschriftart verwenden
                    font = ImageFont.load_default()
        except Exception:
            # Wenn keine Schriftart gefunden wird, Standardschriftart verwenden
            font = ImageFont.load_default()

        # Gradientenhintergrund erstellen für bessere Visualisierung
        for y in range(height):
            for x in range(width):
                # Subtiler Gradient von oben nach unten
                r = int(240 - y * 20 / height)
                g = int(240 - y * 20 / height)
                b = int(255 - y * 30 / height)
                image.putpixel((x, y), (r, g, b))

        # Text zentrieren
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        x = (width - text_width) // 2
        y = (height - text_height) // 2

        # Textshadow für 3D-Effekt in der Vorschau
        shadow_offset = max(1, int(font_size * 0.05))
        draw.text((x + shadow_offset, y + shadow_offset), text, font=font, fill=(180, 180, 180))

        # Text zeichnen
        draw.text((x, y), text, font=font, fill=(50, 50, 50))

        # Bild speichern, falls Pfad angegeben
        if output_path:
            image.save(output_path)

        return image
    except Exception as e:
        print(f"Fehler bei der Vorschau-Erstellung: {str(e)}")
        return None