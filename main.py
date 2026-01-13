import vertexai
from vertexai.generative_models import GenerativeModel, Part, HarmCategory, HarmBlockThreshold
import json
import math

# --- KONFIGURACJA ---
PROJECT_ID = "test-wellness-rag"
LOCATION = "global"
MODEL_NAME = "gemini-3-flash-preview"

# ZDJĘCIA TESTOWE
# IMG_PATH_TOP = "Foto_Plates_2/dish_1_T.png"
# IMG_PATH_SIDE = "Foto_Plates_2/dish_1_L.jpg"

IMG_PATH_TOP = "Foto_Plates_2/Carbon_T.jpg"
IMG_PATH_SIDE = "Foto_Plates_2/Carbon_L.jpg"

# Słownik wymiarów (Fallback)
FALLBACK_SIZES = {"BOWL_STD": 130, "PLATE_S": 198, "PLATE_L": 260}

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
- 'charakter_przestrzenny': 'PLASKI_WARSTWA' (0.5cm - Wędlina, Naleśnik), 'NISKI_KOPCZYK' (2cm - Kotlet, Filet, Ryż, Kasza, Ziemniaki kawałki/całe), 'WYSOKI_KOPIEC' (4cm - Puree, Makaron), 'LUZNY_STOS' (4cm - Spaghetti, Sałata, Frytki, Chipsy - Dużo powietrza), 'BRYLA_ZWARTA' (3D - Jabłko, Udko z kością), 'SOS_W_MISECZCE' (Małe naczynie), 'CIECZ'.
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
        "charakter_przestrzenny": "String (Z LISTY POWYŻEJ)",
        "gestosc_wizualna": "String (Z LISTY POWYŻEJ)",
        "stopien_przetworzenia": "Niski" | "Sredni" | "Wysoki"
      }
    ],
    "skladniki_niejednoznaczne": [
      {
        "przedmiot_wizualny": "String (np. Biały Sos, Szklanka coli)",
        "procent_talerza": Integer,
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

# --- FUNKCJA MATEMATYCZNA (PYTHON) ---


def calculate_grammage(plate_mm, component_data):
    """
    Uniwersalny przelicznik wagi.
    Obsługuje:
    1. Produkty policzalne/poza talerzem (Sztuki * Waga standardowa).
    2. Produkty geometryczne (Geometria talerza * % * Wysokość * Gęstość).
    """

    # --- ŚCIEŻKA 1: CZY TO PRODUKT POLICZALNY/SZTUKOWY? ---
    # Sprawdzamy, czy AI zwróciło ilość sztuk (np. 1 miseczka, 2 kromki)
    ilosc = component_data.get('ilosc_sztuk')

    if ilosc and ilosc > 0:
        jednostka = component_data.get('typ_jednostki', '').lower()

        # Baza standardowych wag (w gramach)
        STANDARD_WAGI = {
            'kromka': 35,       # Chleb standard
            'pajda': 50,        # Duży chleb
            'bułka': 60,
            'kajzerka': 60,
            'sztuka': 100,      # Domyślny owoc/warzywo (np. jabłko)
            'jajko': 55,
            'szklanka': 250,    # Napój
            'kubek': 250,
            'kieliszek': 150,   # Wino
            'plaster': 20,      # Ser/Szynka
            'garsc': 30,        # Orzechy/Jagody

            # --- ZABEZPIECZENIA DLA SOSÓW POZA TALERZEM ---
            'miseczka': 50,     # Standardowy ramekin sosu
            'porcja': 50,       # Porcja sosu/dipu
            'dip': 50,
            'sos': 50
        }

        # Pobieramy wagę. Jeśli AI wymyśli dziwną nazwę jednostki, przyjmujemy bezpieczne 100g.
        # Ale dla sosów "miseczka" trafi idealnie w 50g.
        waga_jednostkowa = STANDARD_WAGI.get(jednostka, 100)

        return int(ilosc * waga_jednostkowa)

    # --- ŚCIEŻKA 2: GEOMETRIA (NA TALERZU) ---
    # Jeśli nie ma sztuk, musi być procent.

    if not plate_mm or plate_mm < 50:
        return 0

    # 1. Powierzchnia talerza (cm2)
    radius_cm = (plate_mm / 10) / 2
    plate_area = math.pi * (radius_cm ** 2)

    # 2. Powierzchnia składnika
    percentage = component_data.get('procent_talerza', 0)
    if percentage <= 0:
        return 0  # Ani sztuki, ani procent = 0g

    comp_area = plate_area * (percentage / 100)

    # 3. Wysokość i Modyfikatory
    h_map = {
        'PLASKI_WARSTWA': 0.8,
        'NISKI_KOPCZYK': 2.0,
        'WYSOKI_KOPIEC': 4.5,
        'LUZNY_STOS': 4.5,
        'BRYLA_ZWARTA': 5.5,
        'CIECZ': 3.0,
        'SOS_W_MISECZCE': 2.5
    }
    spatial_type = component_data.get(
        'charakter_przestrzenny', 'NISKI_KOPCZYK')
    height = h_map.get(spatial_type, 2.0)

    volume_modifier = 1.0
    if spatial_type == 'BRYLA_ZWARTA':
        volume_modifier = 0.66
    elif spatial_type == 'SOS_W_MISECZCE':
        volume_modifier = 0.35,
    elif spatial_type == 'LUZNY_STOS':
        volume_modifier = 0.31

    # 4. Gęstość
    d_map = {'NISKA': 0.3, 'SREDNIA': 0.95, 'WYSOKA': 1.15}
    density = d_map.get(component_data.get('gestosc_wizualna'), 0.95)

    # 5. Wynik
    volume = comp_area * height * volume_modifier
    return int(volume * density)


def analyze_full_plate_v2(project_id, location, model_name, path_top, path_side):
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

    response = model.generate_content(
        content_parts,
        generation_config={"max_output_tokens": 8192,
                           "temperature": 0.0, "response_mime_type": "application/json"},
        safety_settings=safety_config
    )

    try:
        result = json.loads(response.text)

        if isinstance(result, list):
            result = result[0]

        geo = result.get("geometry_analysis", {})
        food = result.get("food_analysis", {})

        # --- POPRAWKA LOGIKI POBIERANIA WYMIARU ---
        diameter = 0

        # 1. Najpierw szukamy konkretnej liczby obliczonej przez AI
        if geo.get("calculated_diameter_mm") and geo.get("calculated_diameter_mm") > 0:
            diameter = geo.get("calculated_diameter_mm")

        # 2. Jeśli nie ma, szukamy surowego wymiaru
        elif geo.get("raw_visual_width_mm") and geo.get("raw_visual_width_mm") > 0:
            diameter = geo.get("raw_visual_width_mm")

        # 3. Jeśli nadal 0, szukamy kategorii (Fallback)
        elif geo.get("fallback_category_label"):
            label = geo.get("fallback_category_label")
            diameter = FALLBACK_SIZES.get(label, 260)

        # Zabezpieczenie ostateczne - jeśli nadal 0, a wykryto talerz, przyjmij średni standard
        if diameter == 0 and geo.get("vessel_type") == "PLATE":
            diameter = 260
        # ------------------------------------------

        # --- RAPORT KOŃCOWY ---
        print("\n" + "="*70)
        print(f"🍽️  RAPORT PEŁNY (Talerz: {diameter} mm)")
        print("="*70)

        print(f"REFERENCJA:    {geo.get('detected_reference_type', 'Brak')}")
        print(f"DEBUG METODY:  {geo.get('measurement_method')}")
        print("-" * 70)

        # A. SKŁADNIKI PEWNE
        print("✅ SKŁADNIKI PEWNE (Automatyczne):")
        pewne = food.get("skladniki_pewne", [])

        if not pewne:
            print("   (Brak)")
        else:
            # Nagłówek tabeli
            print(
                f"   {'NAZWA':<25} | {'ILOŚĆ':<10} | {'STAN':<20} | {'WAGA (EST)'}")
            print("-" * 80)

            for item in pewne:
                # 1. Oblicz wagę (funkcja sama zdecyduje czy użyć % czy sztuk)
                waga = calculate_grammage(diameter, item)

                # 2. Sformatuj opis ilości (Sztuki vs Procenty)
                if item.get("ilosc_sztuk") and item.get("ilosc_sztuk") > 0:
                    # np. "1 sztuka"
                    ilosc_desc = f"{item.get('ilosc_sztuk')} x {item.get('typ_jednostki')}"
                else:
                    ilosc_desc = f"{item.get('procent_talerza')}%"  # np. "25%"

                # 3. Wyświetl
                print(
                    f"   {item.get('nazwa'):<25} | {ilosc_desc:<10} | {item.get('stan_wizualny'):<20} | {waga} g")

        print("-" * 80)

        # B. SKŁADNIKI NIEJEDNOZNACZNE (To co idzie do aplikacji do wyboru)
        print("❓ SKŁADNIKI NIEJEDNOZNACZNE (Do wyboru w UI):")
        niejedno = food.get("skladniki_niejednoznaczne", [])
        if not niejedno:
            print("   (Brak - wszystko jasne)")
        else:
            for item in niejedno:
                # Tu też liczymy wagę "brylę", bo objętość jest ta sama niezależnie od wariantu
                waga_baza = calculate_grammage(diameter, item)
                print(
                    f"   👁️  WIDZĘ: {item.get('przedmiot_wizualny')} (~{waga_baza} g)")
                print("       OPCJE DO WYBORU:")
                for wariant in item.get('warianty', []):
                    print(
                        f"         - {wariant.get('nazwa')} ({wariant.get('typ')})")

        print("="*70)
        print(
            f"DEBUG GEO: {geo.get('vessel_type')} | Raw: {geo.get('raw_visual_width_mm')} -> Calc: {geo.get('calculated_diameter_mm')}")

    except Exception as e:
        print(f"BŁĄD: {e}")
        print("Fragment odpowiedzi:", response.text[:500])


if __name__ == "__main__":
    analyze_full_plate_v2(PROJECT_ID, LOCATION, MODEL_NAME,
                          IMG_PATH_TOP, IMG_PATH_SIDE)
