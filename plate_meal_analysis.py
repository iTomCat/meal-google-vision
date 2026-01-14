import vertexai
from vertexai.generative_models import GenerativeModel, Part, HarmCategory, HarmBlockThreshold
import json
from meal_weight_estimator import enrich_meal_json

# -------------------------------------------------------------------
# Określanie wielkości talerza/miski na podstawie dwóch zdjęć.
# referencjie - widelc, łyzka itp
# Skanowanie skłdnków posiłku
# obliczanie przyblionej wagi składników - analiza ile procent zajmuje danie na talerzu
# a następnie przeliczanie na gramy w zaleności od średniej wysokości i gęstości
# -------------------------------------------------------------------
# UWAGA LEPIEJ LICZY GDY TALERZ JEST WIĘKSZY TAK JAK NA ZDJĘCIU
# danie_2a_T.jpg A NIE JAK NA ZDJĘCIU danie_2_T.jpg
# -------------------------------------------------------------------

# --- FINALNY SCALONY PROMPT ---
SYSTEM_PROMPT = """
Jesteś zaawansowanym sensorem wizualnym dla aplikacji dietetycznej.
Twoim zadaniem jest ekstrakcja faktów z obrazu w dwóch wymiarach:
1. GEOMETRIA: Precyzyjny pomiar naczynia (ignorując jedzenie).
2. DIETETYKA I FIZYKA: Identyfikacja składników oraz ocena ich objętości (żeby algorytm policzył wagę).

MAPPING DANYCH WEJŚCIOWYCH (Kolejność ma kluczowe znaczenie):
1. PIERWSZY OBRAZ: Widok z góry (Top-View). Służy do pomiaru szerokości naczynia i identyfikacji składników.
2. DRUGI OBRAZ: Widok z boku/kąta (Side-View). Służy WYŁĄCZNIE do oceny geometrii naczynia (płaskie/głębokie) oraz wysokości jedzenia (3D).

--- SEKCJA 1: GEOMETRIA NACZYNIA ---

ALGORYTM DECYZYJNY:
KROK 1: Decyzja Typu (Patrz na DRUGI OBRAZ): Czy to "BOWL" (wysokie ścianki) czy "PLATE" (płaski)?
KROK 2: Referencja (Patrz na PIERWSZY OBRAZ): Widelec (192mm), Nóż (220mm), Łyżka (195mm).
KROK 3: Wykonaj pomiar stosując odpowiedni znacznik CASE (ignorując inne):

<CASE_PLATE>
    CEL: Maksymalna średnica fizyczna (włącznie z rantem).
    1. ELIMINACJA JEDZENIA: Spójrz na środek. Czy widzisz okrągły obiekt (owoc, pomelo, bułka) leżący na talerzu?
       - JEŚLI TAK: To jedzenie. IGNORUJ mniejszy, wewnętrzny okrąg. Szukaj większego okręgu pod spodem.
    2. ANALIZA RANTU: Sprawdź najbardziej zewnętrzną krawędź. Jeśli widzisz wzór (romby, paski, dekoracje) - to JEST część talerza.
    3. POMIAR: Mierz od zewnętrznego końca wzoru z lewej do zewnętrznego końca wzoru z prawej (NAJSZERSZY obrys).
    4. ZAPIS: Wpisz ten sam wynik do pól 'raw_visual_width_mm' oraz 'calculated_diameter_mm'.
</CASE_PLATE>

<CASE_BOWL>
    CEL: Realna średnica otworu (skorygowana o perspektywę).
    1. ELIMINACJA JEDZENIA: Jeśli w misce znajduje się obiekt (np. zupa, owoc) tworzący mniejszy krąg -> IGNORUJ GO. Mierz krawędź naczynia.
    2. POMIAR WSTĘPNY: Zmierz wizualną szerokość otworu na zdjęciu z góry (między zewnętrznymi punktami).
    3. ZAPIS SUROWY: Wpisz do 'raw_visual_width_mm'.
    4. KOREKTA: Odejmij 16% od wizualnego pomiaru (Formuła: calculated_diameter_mm = raw_visual_width_mm * 0.16).
</CASE_BOWL>

WARIANT C: Fallback -> "BOWL_STD", "PLATE_S", "PLATE_L".


--- SEKCJA 2: ANALIZA SKŁADNIKÓW (PEWNE vs NIEJEDNOZNACZNE) ---

Twoim celem jest rozbicie posiłku na składniki i opisanie ich FIZYKI (żeby policzyć wagę).
Spójrz na DRUGI OBRAZ (Side-View), aby ocenić parametr 'charakter_przestrzenny' (wysokość).

DEFINICJE PARAMETRÓW FIZYCZNYCH:
- 'charakter_przestrzenny': 'PLASKI_WARSTWA' (0.5cm - Wędlina, Naleśnik), 'NISKI_KOPCZYK' (2cm - Kotlet, Filet, Ryż, Kasza, Ziemniaki kawałki/całe), 'WYSOKI_KOPIEC' (4cm - Puree, Makaron), 'LUZNY_STOS' (4cm - Spaghetti, Sałata, Frytki, Chipsy - Dużo powietrza), 'BRYLA_ZWARTA' (3D - Jabłko, Udko z kością), 'SOS_W_MISECZCE' (Małe naczynie), 'ROLKA_NADZIEWANA' (Wrap, Tortilla, Naleśnik zwinięty - Dużo powietrza/lekki farsz), 'CIECZ'.
- 'gestosc_wizualna': 'NISKA' (Sałata), 'SREDNIA' (Ziemniaki, Ryż), 'WYSOKA' (Mięso, Ciasto).

ZASADY KATEGORYZACJI (Kluczowa logika):
1. 'skladniki_pewne': Produkty, które rozpoznajesz bez wątpliwości i nie wymagają wyboru (np. Ryż, Udko, Całe Jabłko).
   - MOGĄ BYĆ NA TALERZU (licz procentem).
   - MOGĄ BYĆ POZA TALERZEM (licz sztukami).

2. 'skladniki_niejednoznaczne': Produkty, które wymagają doprecyzowania przez użytkownika.
   - PRZYKŁADY: Rodzaj chleba, Typ sosu, Rodzaj napoju (Cola vs Zero), Skład kotleta.
   - INSTRUKCJA WAŻNA: Dla każdego takiego produktu WYGENERUJ listę 'warianty' (Podaj od 2 do 3 najbardziej logicznych opcji dietetycznych, np. "Z Cukrem" vs "Słodzik").

ZASADA WYBORU METODY POMIARU (Dotyczy obu powyższych kategorii):
   - WARIANT A: PRODUKT ROZMYTY / NA TALERZU (np. Puree, Kasza, Sos w miseczce)
     -> Wypełnij 'procent_talerza' (0-100).
     -> Pozostaw 'ilosc_sztuk': null.

   - WARIANT B: PRODUKT POLICZALNY / POZA TALERZEM (np. Całe Jabłko, Kromka chleba, Szklanka)
     -> Ustaw 'procent_talerza': 0.
     -> Wypełnij 'ilosc_sztuk' (Integer) oraz 'typ_jednostki' (np. 'sztuka', 'kromka', 'szklanka').

WYMAGANY FORMAT JSON:
{
  "geometry_analysis": {
    "vessel_type": "string ('PLATE' lub 'BOWL')",
    "visual_rim_check": "string",
    "reference_found": boolean,
    "detected_reference_type": "string",
    "measurement_method": "string",
    "raw_visual_width_mm": int,
    "calculated_diameter_mm": int,
    "fallback_category_label": "string"
  },
  "food_analysis": {
    "skladniki_pewne": [
      {
        "nazwa": "String (np. Ziemniaki)",
        "stan_wizualny": "String (np. Pieczone w mundurkach)",
        "procent_talerza": Integer (0-100),
        "ilosc_sztuk": IntegerOrNull,
        "typ_jednostki": "StringOrNull",
        "charakter_przestrzenny": "String (Z LISTY POWYŻEJ)",
        "gestosc_wizualna": "String (Z LISTY POWYŻEJ)",
      }
    ],
    "skladniki_niejednoznaczne": [
      {
        "przedmiot_wizualny": "String (np. Biały Sos, Szklanka coli)",
        "procent_talerza": Integer,
        "ilosc_sztuk": IntegerOrNull,
        "typ_jednostki": "StringOrNull",
        "charakter_przestrzenny": "String (Z LISTY POWYŻEJ)",
        "gestosc_wizualna": "String (Z LISTY POWYŻEJ)",
        "warianty": [
          { "nazwa": "String (np. Cola Zero)", "typ": "Bez Cukru" },
          { "nazwa": "String (np. Cola Klasyczna)", "typ": "Cukier" }
        ]
      }
    ],
    "kontekst_talerza": {
      "czy_widac_warzywa": Boolean,
      "szacowany_rozmiar": "S" | "M" | "L"
    }
  }
}
"""


def analyze_full_plate(project_id, location, model_name, path_top, path_side):
    '''
    Analiza wielkości talerza/miski oraz składników posiłku na podstawie dwóch zdjęć.
    Zwraca JSON z przybliona waga składników.
    '''
    print("--- START ANALIZY (HYBRYDA PEWNE/NIEJEDNOZNACZNE) ---")

    vertexai.init(project=project_id, location=location)
    model = GenerativeModel(model_name, system_instruction=[SYSTEM_PROMPT])

    content_parts = []
    try:
        with open(path_top, "rb") as f:
            content_parts.append(Part.from_data(
                data=f.read(), mime_type="image/jpeg"))
        with open(path_side, "rb") as f:
            content_parts.append(Part.from_data(
                data=f.read(), mime_type="image/jpeg"))
    except FileNotFoundError:
        print("BŁĄD: Brak plików.")
        return

    content_parts.append("Przeanalizuj to.")

    # Definiujemy konfigurację znoszącą WSZYSTKIE blokady
    safety_config = {
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    }

    print("🤖 START Vertex AI...")
    response = model.generate_content(
        content_parts,
        generation_config={"max_output_tokens": 8192,
                           "temperature": 0.0, "response_mime_type": "application/json"},
        safety_settings=safety_config
    )

    try:
        raw_result = json.loads(response.text)

        if isinstance(raw_result, list) and raw_result:
            raw_result = raw_result[0]

        final_data = enrich_meal_json(raw_result)

        geometry = final_data.get("geometry_analysis", {})
        food = final_data.get("food_analysis", {})

        # --- POPRAWKA LOGIKI POBIERANIA WYMIARU ---
        diameter = 0

        # Średnicę bierzemy z meta-danych, które obliczył procesor
        diameter = final_data.get("meta_calculation", {}).get(
            "final_diameter_mm", 0)
        # ------------------------------------------

        # --- RAPORT KOŃCOWY ---
        print("\n" + "="*70)
        print(f"🍽️  RAPORT PEŁNY (Talerz: {diameter} mm)")
        print("="*70)

        print(
            f"REFERENCJA:    {geometry.get('detected_reference_type', 'Brak')}")
        print(f"DEBUG METODY:  {geometry.get('measurement_method')}")
        print("-" * 70)

        # A. SKŁADNIKI PEWNE
        print("✅ SKŁADNIKI PEWNE (Już przeliczone):")
        pewne = food.get("skladniki_pewne", [])

        if not pewne:
            print("   (Brak)")
        else:
            # PRZYWRÓCONO KOLUMNĘ 'STAN'
            print(f"   {'NAZWA':<25} | {'ILOŚĆ':<12} | {'STAN':<20} | {'WAGA'}")
            print("-" * 80)

            for item in pewne:
                # 1. Pobieramy gotową wagę
                waga = item.get("calculated_weight_g", 0)

                # 2. Formatujemy opis ilości
                ilosc = item.get("ilosc_sztuk") or 0

                if ilosc > 0:
                    typ = item.get('typ_jednostki') or 'szt'
                    desc = f"{ilosc} x {typ}"
                else:
                    proc = item.get('procent_talerza') or 0
                    desc = f"{proc}%"

                # 3. Wyświetlamy ze stanem wizualnym (używamy .get('', '') na wypadek braku opisu)
                stan = item.get('stan_wizualny', '')

                print(
                    f"   {item.get('nazwa'):<25} | {desc:<12} | {stan:<20} | {waga} g")
        print("-" * 80)

        # B. SKŁADNIKI NIEJEDNOZNACZNE (To co idzie do aplikacji do wyboru)
        print("❓ SKŁADNIKI NIEJEDNOZNACZNE (Do wyboru w UI):")
        niejedno = food.get("skladniki_niejednoznaczne", [])
        if not niejedno:
            print("   (Brak - wszystko jasne)")
        else:
            for item in niejedno:
                # Tu też liczymy wagę "brylę", bo objętość jest ta sama niezależnie od wariantu
                waga_bryly = item.get("visual_object_weight_g", 0)
                print(
                    f"   👁️  WIDZĘ: {item.get('przedmiot_wizualny')} (~{waga_bryly} g)")
                print("       OPCJE DO WYBORU:")

                for wariant in item.get('warianty', []):
                    # Każdy wariant ma już swoją wagę!
                    waga_wariantu = wariant.get("calculated_weight_g", 0)
                    print(
                        f"         - [ ] {wariant.get('nazwa'):<20} -> {waga_wariantu} g")

        print("="*70)
        print(
            f"DEBUG GEO: {geometry.get('vessel_type')} | Raw: {geometry.get('raw_visual_width_mm')} -> Calc: {geometry.get('calculated_diameter_mm')}")

        # WAŻNE: Na końcu funkcji zwracamy ten obiekt,
        # żeby API (np. Flask/FastAPI) mogło go wysłać do telefonu.
        return final_data

    except Exception as e:
        print(f"BŁĄD: {e}")
        print("Fragment odpowiedzi:", response.text[:500])
        return None
