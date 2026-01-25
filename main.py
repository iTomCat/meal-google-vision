import json
import uuid  # Generowanie unikalnych ID posiłków
from meal_analysys.plate_meal_analysis import analyze_full_plate
from interaction_manager import resolve_user_conflicts
from database_manager import save_final_meal
from storage_manager import upload_meal_image

# --- KONFIGURACJA ---
PROJECT_ID = "test-wellness-rag"
LOCATION = "global"
MODEL_NAME = "gemini-3-flash-preview"

TEST_USER_ID = "tomasz_local_dev"
SAVE_TO_CLOUD = True

# ZDJĘCIA TESTOWE
# IMG_PATH_TOP = "Foto_Plates_2/dish_1_T.png"
# IMG_PATH_SIDE = "Foto_Plates_2/dish_1_L.jpg"

# IMG_PATH_TOP = "Foto_Plates_2/Carbon_T.jpg"
# IMG_PATH_SIDE = "Foto_Plates_2/Carbon_L.jpg"

# IMG_PATH_TOP = "Foto_Plates_2/tortilla_T.jpg"
# IMG_PATH_SIDE = "Foto_Plates_2/tortilla_L.jpg"

IMG_PATH_TOP = "Foto_Plates_2/kurczak_ryz_T.jpg"
IMG_PATH_SIDE = "Foto_Plates_2/kurczak_ryz_L.jpg"

# IMG_PATH_TOP = "Foto_Plates_2/ziemniaki_top.jpg"
# IMG_PATH_SIDE = "Foto_Plates_2/ziemniaki.png"


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

    if json_data:
        try:
            # 1. Wywołujemy funkcję interaktywną (tę z input() i logiką scalania)
            # Funkcja ta zwraca zaktualizowany obiekt JSON (wszystko przeniesione do 'skladniki_pewne')
            final_data_processed = resolve_user_conflicts(json_data)

            # 2. GENEROWANIE PLIKU KOŃCOWEGO (Na podstawie wyborów użytkownika)
            print("\n" + "=" * 60)
            print("📂 TWORZENIE PLIKU KOŃCOWEGO: 'happy_meal_final.json'")

            food = final_data_processed.get("food_analysis", {})
            # Po resolve_user_conflicts lista 'skladniki_niejednoznaczne' jest pusta,
            # a scalone wyniki są w 'skladniki_pewne'.
            final_ingredients = food.get("skladniki_pewne", [])

            # Pobieramy średnicę (bezpiecznie)
            diameter = final_data_processed.get(
                "meta_calculation", {}).get("final_diameter_mm", 0)

            final_list_clean = []
            total_meal_weight = 0

            # Przetwarzamy listę do czystego formatu
            for item in final_ingredients:
                nazwa = item.get("nazwa")
                # Waga może być pod calculated_weight_g (z wariantu) lub visual_object_weight_g (z bryły)
                waga = item.get("calculated_weight_g") or item.get(
                    "visual_object_weight_g") or 0

                total_meal_weight += waga

                final_list_clean.append({
                    "nazwa": nazwa,
                    "waga_g": waga,
                    "stan": item.get("stan_wizualny", "Standard")
                })

            # Wyświetlamy podsumowanie w konsoli
            print("-" * 30)
            for f in final_list_clean:
                print(f" - {f['nazwa']:<40} {f['waga_g']} g")
            print("-" * 30)
            print(f"SUMA CAŁKOWITA: {total_meal_weight} g")
            print("=" * 60)

            # Konstrukcja obiektu wyjściowego
            final_json_output = {
                "meta": {
                    "talerz_srednica_mm": diameter,
                    "calkowita_waga_g": total_meal_weight
                },
                "skladniki": final_list_clean
            }

            # Zapis do pliku JSON
            with open('happy_meal_final.json', 'w', encoding='utf-8') as f:
                json.dump(final_json_output, f, ensure_ascii=False, indent=2)
            print("💾 ZAPISANO: happy_meal_final.json")

            # Opcjonalnie zwróć wynik
            # return final_json_output
            print("\n☁️  WYSYŁANIE DO BAZY DANYCH...")

            #  Zapisywanie do Firestore i upload zdjęć
            if not SAVE_TO_CLOUD:
                print("\n🛑 TRYB TESTOWY: Koniec pracy. Nie wysyłam do chmury.")
                return  # <--- TU WYCHODZIMY Z FUNKCJI

            # 1. Generujemy ID (wymaga: import uuid na górze pliku!)
            meal_unique_id = str(uuid.uuid4())

            # 2. Wysyłamy zdjęcia
            url_top = upload_meal_image(IMG_PATH_TOP, meal_unique_id, "top")
            url_side = upload_meal_image(IMG_PATH_SIDE, meal_unique_id, "side")

            # 3. Dodajemy ID do JSONa i zapisujemy do bazy
            final_json_output["meal_id"] = meal_unique_id

            save_final_meal(
                meal_id=meal_unique_id,
                user_id=TEST_USER_ID,
                meal_data_json=final_json_output,
                url_top=url_top,
                url_side=url_side
            )
            print("✅ SUKCES! Zapisano w chmurze.")

        except Exception as e:
            print(f"❌ Błąd podczas przetwarzania końcowego: {e}")


if __name__ == "__main__":
    main()
