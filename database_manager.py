import firebase_admin
from firebase_admin import credentials
# ZMIANA IMPORTU: Musimy zaimportować firestore bezpośrednio z google.cloud
from google.cloud import firestore
from datetime import datetime

# --- KONFIGURACJA ---
PROJECT_ID = "mealhack-app"
DATABASE_NAME = "meal-base"  # nazwa bazy


def init_firebase():
    """
    Inicjalizuje Firebase (dla innych usług) oraz zwraca klienta Firestore
    skonfigurowanego pod konkretną bazę danych.
    """
    # 1. Inicjalizacja aplikacji Firebase (potrzebna, by działały inne moduły w tle)
    if not firebase_admin._apps:
        # Używamy Application Default Credentials (ADC) - to te z gcloud auth login
        cred = credentials.ApplicationDefault()
        firebase_admin.initialize_app(cred, {
            'projectId': PROJECT_ID,
        })
        print(f"🔥 Firebase App zainicjalizowana: {PROJECT_ID}")

    # 2. TWORZENIE KLIENTA FIRESTORE (POPRAWKA)
    # Zamiast używać wrappera firebase_admin.firestore.client(),
    # tworzymy obiekt Client bezpośrednio. To pozwala wskazać 'database'.
    print(f"🔌 Łączenie z bazą danych: {DATABASE_NAME}...")

    db_client = firestore.Client(project=PROJECT_ID, database=DATABASE_NAME)

    return db_client


# Inicjalizacja przy imporcie pliku
db = init_firebase()


def save_final_meal(meal_id, user_id, meal_data_json, url_top, url_side):
    """
    Zapisuje posiłek pod konkretnym ID, dodając linki do zdjęć.
    """
    try:
        # Używamy .document(meal_id) -> SAMI DECYDUJEMY O ID
        doc_ref = db.collection("meals_history").document(meal_id)

        record = {
            "id": meal_id,
            "user_id": user_id,
            "created_at": datetime.now(),

            "images": {
                "top_url": url_top,
                "side_url": url_side
            },

            "meta": meal_data_json.get("meta", {}),
            "skladniki": meal_data_json.get("skladniki", []),
            "total_kcal": 0,
            "status": "completed"
        }

        doc_ref.set(record)
        print(
            f"💾 Zapisano w Firestore (baza: {DATABASE_NAME}) pod ID: {meal_id}")
        return meal_id

    except Exception as e:
        print(f"❌ Błąd zapisu do Firestore: {e}")
        return None
