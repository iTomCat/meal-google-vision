import copy

def resolve_user_conflicts(json_data):
    """
    Wybór składników niejednoznacznych przez użytkownika (CLI).
    Łączy interaktywny wybór z logiką scalania nazw (target_name).
    """

    # Robimy kopię, żeby nie psuć oryginału w trakcie pętli
    processed_data = copy.deepcopy(json_data)

    food_analysis = processed_data.get("food_analysis", {})
    pewne = food_analysis.get("skladniki_pewne", [])
    niejednoznaczne = food_analysis.get("skladniki_niejednoznaczne", [])

    # Jeśli nie ma nic do roboty, zwracamy od razu
    if not niejednoznaczne:
        print("✅ Brak składników wymagających decyzji.")
        return processed_data

    print("\n" + "!"*60)
    print(f"😊 WYMAGANA INTERWENCJA UŻYTKOWNIKA ({len(niejednoznaczne)} decyzji)")
    print("!"*60)

    # Iterujemy po każdym niejednoznacznym obiekcie
    for index, item in enumerate(niejednoznaczne):
        print(f"\n👉 DECYZJA {index + 1}/{len(niejednoznaczne)}")
        print(f"   Pytanie: {item.get('przedmiot_wizualny')}")
        
        target_name = item.get("dotyczy_skladnika")
        if target_name:
            print(f"   🔗 DOTYCZY SKŁADNIKA: '{target_name}'")
        else:
            print(f"   ➕ TO BĘDZIE NOWY SKŁADNIK")

        warianty = item.get("warianty", [])

        # Wyświetlamy opcje
        for i, wariant in enumerate(warianty):
            print(f"   [{i + 1}] {wariant.get('nazwa')}")
            # print(f"       Waga: {wariant.get('calculated_weight_g')} g")

        # --- PĘTLA WALIDACJI INPUTU (Manualny wybór) ---
        wybor = -1
        while True:
            try:
                user_input = input("\n   Wybierz numer opcji > ")
                wybor = int(user_input)
                if 1 <= wybor <= len(warianty):
                    break
                else:
                    print(f"   ⚠️ Wpisz liczbę od 1 do {len(warianty)}")
            except ValueError:
                print("   ⚠️ To nie jest liczba.")

        # Pobieramy wybrany wariant
        wybrany_wariant = warianty[wybor - 1]
        print(f"   ✅ Wybrano: {wybrany_wariant.get('nazwa')}")

        # ========================================================
        # 🔥 LOGIKA SCALANIA (MERGE LOGIC) - ZINTEGROWANA 🔥
        # ========================================================
        
        if target_name:
            # SCENARIUSZ A: DOPRECYZOWANIE (Scalanie nazwy)
            znaleziono = False
            for istniejacy in pewne:
                aktualna_nazwa = istniejacy.get("nazwa", "")
                
                # Kluczowy warunek startswith
                if aktualna_nazwa == target_name or aktualna_nazwa.startswith(target_name + " ("):
                    stara_nazwa = istniejacy["nazwa"]
                    dodatek = wybrany_wariant["nazwa"]
                    
                    # Scalanie nazwy
                    istniejacy["nazwa"] = f"{stara_nazwa} ({dodatek})"
                    print(f"      🔄 ZAKTUALIZOWANO NAZWĘ: '{istniejacy['nazwa']}'")
                    znaleziono = True
                    break
            
            if not znaleziono:
                print(f"      ⚠️ NIE ZNALEZIONO '{target_name}'. Dodaję jako nowy.")
                # Fallback - dodajemy jako nowy, formatując go poprawnie
                nowy_skladnik = {
                    "nazwa": wybrany_wariant.get("nazwa"),
                    "calculated_weight_g": wybrany_wariant.get("calculated_weight_g", 0),
                    "stan_wizualny": f"Opcja wybrana: {wybrany_wariant.get('typ', '')}",
                    "procent_talerza": 0
                }
                pewne.append(nowy_skladnik)

        else:
            # SCENARIUSZ B: NOWY SKŁADNIK (np. Wsad wrapa)
            print(f"      ➕ DODANO NOWĄ POZYCJĘ: {wybrany_wariant.get('nazwa')}")
            
            # Tworzymy pełny obiekt składnika
            nowy_skladnik = {
                "nazwa": wybrany_wariant.get("nazwa"),
                "calculated_weight_g": wybrany_wariant.get("calculated_weight_g", 0),
                "stan_wizualny": f"{wybrany_wariant.get('typ', '')} ({item.get('przedmiot_wizualny')})",
                "procent_talerza": item.get("procent_talerza", 0),
                # Przenosimy inne metadane jeśli są potrzebne
                "charakter_przestrzenny": item.get("charakter_przestrzenny"),
                "gestosc_wizualna": item.get("gestosc_wizualna")
            }
            pewne.append(nowy_skladnik)
        
        # ========================================================

    # --- CZYSZCZENIE JSONA ---
    if "skladniki_niejednoznaczne" in processed_data["food_analysis"]:
        del processed_data["food_analysis"]["skladniki_niejednoznaczne"]

    print("\n" + "="*60)
    print("✨ KONIEC INTERAKCJI. JSON GOTOWY.")
    print("="*60)

    return processed_data