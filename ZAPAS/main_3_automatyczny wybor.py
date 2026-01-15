import json
from meal_analysys.plate_meal_analysis import analyze_full_plate
from interaction_manager import resolve_user_conflicts

# --- KONFIGURACJA ---
PROJECT_ID = "test-wellness-rag"
LOCATION = "global"
MODEL_NAME = "gemini-3-flash-preview"

# ZDJĘCIA TESTOWE
# IMG_PATH_TOP = "Foto_Plates_2/dish_1_T.png"
# IMG_PATH_SIDE = "Foto_Plates_2/dish_1_L.jpg"

IMG_PATH_TOP = "Foto_Plates_2/Carbon_T.jpg"
IMG_PATH_SIDE = "Foto_Plates_2/Carbon_L.jpg"

# IMG_PATH_TOP = "Foto_Plates_2/tortilla_T.jpg"
# IMG_PATH_SIDE = "Foto_Plates_2/tortilla_L.jpg"

# IMG_PATH_TOP = "Foto_Plates_2/kurczak_ryz_T.jpg"
# IMG_PATH_SIDE = "Foto_Plates_2/kurczak_ryz_L.jpg"


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
            
            # --- 1. DEFINICJE ZMIENNYCH (Tu brakowało definicji!) ---
            food = json_data.get("food_analysis", {})
            
            # ### <<< POPRAWKA BŁĘDU F821 (Undefined diameter)
            # Musimy pobrać średnicę z JSON-a, bo zmienna lokalna może już nie istnieć
            diameter = json_data.get("meta_calculation", {}).get("final_diameter_mm", 0) 
            
            print("\n" + "=" * 60)
            print("--- ROZPOCZYNAMY INTERAKCJĘ (SYMULACJA UI) ---")
            
            # 2. TWORZYMY LISTĘ ROBOCZĄ
            final_ingredients = [item.copy() for item in food.get("skladniki_pewne", [])]
            niejednoznaczne = food.get("skladniki_niejednoznaczne", [])

            if niejednoznaczne:
                print(f"😊 WYMAGANA INTERWENCJA UŻYTKOWNIKA ({len(niejednoznaczne)} decyzji)")

                for i, pytanie in enumerate(niejednoznaczne):
                    print(f"\n👉 DECYZJA {i + 1}/{len(niejednoznaczne)}")
                    print(f"   Pytanie: {pytanie.get('przedmiot_wizualny')}")
                    
                    target_name = pytanie.get("dotyczy_skladnika")
                    if target_name:
                        print(f"   🔗 DOTYCZY SKŁADNIKA: '{target_name}'")

                    warianty = pytanie.get('warianty', [])
                    
                    # --- SYMULACJA WYBORU ---
                    wybor_idx = 0 

                    if warianty and 0 <= wybor_idx < len(warianty):
                        wybrany_wariant = warianty[wybor_idx]
                        print(f"   ✅ Wybrano: {wybrany_wariant.get('nazwa')} ({wybrany_wariant.get('calculated_weight_g', 0)}g)")

                        # --- LOGIKA SCALANIA ---
                        if target_name:
                            # SCENARIUSZ A: DOPRECYZOWANIE
                            znaleziono = False
                            for istniejacy in final_ingredients:
                                aktualna_nazwa = istniejacy.get("nazwa", "")
                                
                                # Sprawdzamy czy to ten składnik.
                                # 1. Czy nazwa jest identyczna? (dla pierwszej decyzji)
                                # 2. Czy nazwa ZACZYNA SIĘ od targetu + " ("? (dla drugiej decyzji, np. panierki)
                                if aktualna_nazwa == target_name or aktualna_nazwa.startswith(target_name + " ("):
                                    stara_nazwa = istniejacy["nazwa"]
                                    dodatek = wybrany_wariant["nazwa"]
                                    
                                    # Scalanie nazwy: doklejamy kolejny nawias
                                    istniejacy["nazwa"] = f"{stara_nazwa} ({dodatek})"
                                    print(f"      🔄 ZAKTUALIZOWANO NAZWĘ: '{istniejacy['nazwa']}'")
                                    znaleziono = True
                                    break
                            
                            if not znaleziono:
                                print(f"      ⚠️ NIE ZNALEZIONO '{target_name}'. Dodaję jako nowy.")
                                final_ingredients.append(wybrany_wariant)

                        else:
                            # SCENARIUSZ B: NOWY SKŁADNIK
                            print(f"      ➕ DODANO NOWĄ POZYCJĘ: {wybrany_wariant.get('nazwa')}")
                            final_ingredients.append(wybrany_wariant)

            # --- FINALIZACJA I ZAPIS PLIKU ---
            print("\n" + "=" * 60)
            print("📂 TWORZENIE PLIKU KOŃCOWEGO: 'happy_meal_final.json'")
            
            final_list_clean = []
            total_meal_weight = 0

            for item in final_ingredients:
                nazwa = item.get("nazwa")
                waga = item.get("calculated_weight_g") or item.get("visual_object_weight_g") or 0
                
                total_meal_weight += waga
                
                final_list_clean.append({
                    "nazwa": nazwa,
                    "waga_g": waga,
                    "stan": item.get("stan_wizualny", "Standard")
                })

            # Podsumowanie
            print("-" * 30)
            for f in final_list_clean:
                print(f" - {f['nazwa']:<40} {f['waga_g']} g")
            print("-" * 30)
            print(f"SUMA CAŁKOWITA: {total_meal_weight} g")
            print("=" * 60)

            # Konstrukcja JSON (Tu używamy naprawionej zmiennej diameter)
            final_json_output = {
                "meta": {
                    "talerz_srednica_mm": diameter,  # TERAZ TO ZADZIAŁA
                    "calkowita_waga_g": total_meal_weight
                },
                "skladniki": final_list_clean
            }

            # Zapis do pliku
            with open('happy_meal_final.json', 'w', encoding='utf-8') as f:
                json.dump(final_json_output, f, ensure_ascii=False, indent=2)
            print("💾 ZAPISANO: happy_meal_final.json")
            
            # Zwracamy wynik (jeśli to funkcja)
            # return final_json_output 

        except Exception as e:
            print(f"❌ KRYTYCZNY BŁĄD PRZETWARZANIA: {e}")
            # Opcjonalnie: return None


if __name__ == "__main__":
    main()
