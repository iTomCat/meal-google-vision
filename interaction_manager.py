
import copy


def resolve_user_conflicts(json_data):
    """
    Wybór skłdników niejednoznacznych przez użytkownika.
    SYMULACJA DZIAŁANIA W APLIKACJI FLUTTER.
    Iteruje po składnikach niejednoznacznych, prosi użytkownika o wybór
    i przenosi wybrany wariant do składników pewnych.
    Zwraca czysty JSON bez sekcji 'niejednoznaczne'.
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
    print(
        f"😊 WYMAGANA INTERWENCJA UŻYTKOWNIKA ({len(niejednoznaczne)} decyzji)")
    print("!"*60)

    # Iterujemy po każdym niejednoznacznym obiekcie
    for index, item in enumerate(niejednoznaczne):
        print(f"\n👉 DECYZJA {index + 1}/{len(niejednoznaczne)}")
        print(f"   Widzę: {item.get('przedmiot_wizualny')}")
        print(f"   Waga bryły: ~{item.get('visual_object_weight_g')} g")
        print(f"   Kontekst: {item.get('procent_talerza')}% talerza")
        print("-" * 40)

        warianty = item.get("warianty", [])

        # Wyświetlamy opcje
        for i, wariant in enumerate(warianty):
            print(f"   [{i + 1}] {wariant.get('nazwa')}")
            print(f"       Opis: {wariant.get('typ')}")
            print(f"       Waga: {wariant.get('calculated_weight_g')} g")

        # Pętla walidacji inputu
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

        # --- TWORZENIE NOWEGO SKŁADNIKA PEWNEGO ---
        # Łączymy dane fizyczne z rodzica (item) z danymi dietetycznymi z dziecka (wariant)
        nowy_skladnik = {
            "nazwa": wybrany_wariant.get("nazwa"),
            # Łączymy typ wariantu z opisem wizualnym dla pełnego kontekstu
            "stan_wizualny": f"{wybrany_wariant.get('typ')} ({item.get('przedmiot_wizualny')})",
            "procent_talerza": item.get("procent_talerza"),
            "charakter_przestrzenny": item.get("charakter_przestrzenny"),
            "gestosc_wizualna": item.get("gestosc_wizualna"),
            # Ważne: Może nie być stopnia przetworzenia w niejednoznacznych, ustawiamy domyślny
            "stopien_przetworzenia": "Nieznany",
            "calculated_weight_g": wybrany_wariant.get("calculated_weight_g"),
            "is_user_selected": True  # Opcjonalna flaga, że to user wybrał
        }

        pewne.append(nowy_skladnik)
        print(f"   ✅ Dodano: {nowy_skladnik['nazwa']}")

    # --- CZYSZCZENIE JSONA ---
    # Po rozwiązaniu wszystkich konfliktów, lista niejednoznaczna ma być pusta
    # processed_data["food_analysis"]["skladniki_niejednoznaczne"] = []
    # Usuwamy całkowicie klucz 'skladniki_niejednoznaczne', bo już wszystko wyjaśniliśmy
    if "skladniki_niejednoznaczne" in processed_data["food_analysis"]:
        del processed_data["food_analysis"]["skladniki_niejednoznaczne"]

    # Sortujemy listę pewnych (opcjonalnie), żeby była porządek
    # (np. od najcięższego składnika)
    pewne.sort(key=lambda x: x.get('calculated_weight_g', 0), reverse=True)

    print("\n" + "="*60)
    print("✨ KONIEC INTERAKCJI. JSON GOTOWY.")
    print("="*60)

    return processed_data
