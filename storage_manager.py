
from firebase_admin import storage
import os

BUCKET_NAME = "mealhack-data"


def upload_meal_image(local_path, meal_id, view_type):
    """
    Wysyła zdjęcie do Firebase Storage.
    Args:
        local_path: Ścieżka do pliku na dysku (np. "Foto/ziemniaki.jpg")
        meal_id: Unikalne ID posiłku (np. UUID)
        view_type: "top" lub "side"
    Returns:
        String: Publiczny URL do zdjęcia lub ścieżka wewnętrzna.
    """
    if not local_path or not os.path.exists(local_path):
        print(f"⚠️ Nie znaleziono pliku: {local_path}")
        return None

    try:
        bucket = storage.bucket(BUCKET_NAME)

        # Tworzymy ładną strukturę folderów w chmurze: meals/{meal_id}/top.jpg
        extension = os.path.splitext(local_path)[1]  # np. .jpg
        destination_blob_name = f"meals/{meal_id}/{view_type}{extension}"

        blob = bucket.blob(destination_blob_name)
        blob.upload_from_filename(local_path)

        # Opcjonalnie: Upubliczniamy plik, żebyś mógł go łatwo podejrzeć w przeglądarce
        # Uwaga: To sprawia, że link jest dostępny dla każdego kto go zna.
        # W produkcji używa się Signed URLs.
        blob.make_public()

        print(f"☁️  Wysłano zdjęcie ({view_type}): {blob.public_url}")
        return blob.public_url

    except Exception as e:
        print(f"❌ Błąd uploadu zdjęcia: {e}")
        return None
