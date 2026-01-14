import json
from plate_meal_analysis import analyze_full_plate
from interaction_manager import resolve_user_conflicts

# --- KONFIGURACJA ---
PROJECT_ID = "test-wellness-rag"
LOCATION = "global"
MODEL_NAME = "gemini-3-flash-preview"

# ZDJĘCIA TESTOWE
# IMG_PATH_TOP = "Foto_Plates_2/dish_1_T.png"
# IMG_PATH_SIDE = "Foto_Plates_2/dish_1_L.jpg"

# IMG_PATH_TOP = "Foto_Plates_2/Carbon_T.jpg"
# IMG_PATH_SIDE = "Foto_Plates_2/Carbon_L.jpg"

IMG_PATH_TOP = "Foto_Plates_2/tortilla_T.jpg"
IMG_PATH_SIDE = "Foto_Plates_2/tortilla_L.jpg"


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

    # --- Symulacja wybory nieznanych skłdników i zapis do JSON ---
    if json_data:
        try:
            # KROK 2: Interakcja z użytkownikiem
            print("\n--- ROZPOCZYNAMY INTERAKCJĘ ---")
            final_json = resolve_user_conflicts(json_data)

            # Zabezpieczenie: Sprawdzamy czy funkcja nie zwróciła pustego obiektu/None
            if not final_json:
                raise ValueError(
                    "Funkcja resolve_user_conflicts nie zwróciła danych.")

            # KROK 3: Bezpieczne pobieranie listy składników (używamy .get() zamiast nawiasów [])
            # Dzięki temu, jeśli klucz nie istnieje, dostaniemy pustą listę zamiast błędu KeyError
            food_analysis = final_json.get("food_analysis", {})
            skladniki = food_analysis.get("skladniki_pewne", [])

            print("\n📂 FINALNA ZAWARTOŚĆ SKŁADNIKÓW:")
            if not skladniki:
                print("   (Lista składników jest pusta)")
            else:
                for item in skladniki:
                    nazwa = item.get('nazwa', 'Nieznany produkt')
                    waga = item.get('calculated_weight_g', 0)
                    print(f" - {nazwa} ({waga}g)")

            # KROK 4: Zapis pliku (Osobny try-except dla operacji na plikach)
            filename = 'happy_meal_final.json'
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(final_json, f, ensure_ascii=False, indent=4)
                print(f"\n💾 Sukces! Zapisano wynik w pliku '{filename}'")
            except IOError as e:
                print(
                    f"\n❌ BŁĄD ZAPISU PLIKU: Nie udało się zapisać '{filename}'. Powód: {e}")

        except Exception as e:
            # Ten blok złapie błędy logiczne w kodzie powyżej
            print(f"\n❌ WYSTĄPIŁ BŁĄD PODCZAS PRZETWARZANIA: {e}")

    else:
        print("❌ Nie otrzymano danych z analizy obrazu (json_data is None).")


if __name__ == "__main__":
    main()
