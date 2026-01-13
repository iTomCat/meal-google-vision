import json
from plate_meal_analysis import analyze_full_plate

# --- KONFIGURACJA ---
PROJECT_ID = "test-wellness-rag"
LOCATION = "global"
MODEL_NAME = "gemini-3-flash-preview"

# ZDJĘCIA TESTOWE
# IMG_PATH_TOP = "Foto_Plates_2/dish_1_T.png"
# IMG_PATH_SIDE = "Foto_Plates_2/dish_1_L.jpg"

IMG_PATH_TOP = "Foto_Plates_2/Carbon_T.jpg"
IMG_PATH_SIDE = "Foto_Plates_2/Carbon_L.jpg"


def main():
    json_data = analyze_full_plate(PROJECT_ID, LOCATION, MODEL_NAME,
                                   IMG_PATH_TOP, IMG_PATH_SIDE)
    if json_data:
        # --- ZAPIS DO PLIKU ---
        try:
            with open('happy_meal.json', 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=4)

            print("💾 Sukces! Plik zapisano jako 'happy_meal.json'")

        except Exception as e:
            print(f"Błąd podczas zapisywania pliku: {e}")


if __name__ == "__main__":
    main()
