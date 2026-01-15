import math

# -------------------------------------------------------------------
# Fizyczny Silnik Obliczeniowy" (Physics Engine)
# Zamiana surowych danych wizualnych z AI na gramaturę (g).
# Ten plik to matematyczne serce aplikacji. Nie łączy się z internetem, nie gada z AI. Bierze JSON-a,
# w którym AI opisało "co widzi" (np. "kopczyk ryżu na 20% talerza")
# i przelicza to na konkretną wagę w gramach.
# -------------------------------------------------------------------

# --- 1. STAŁE I BAZA WIEDZY O WAGACH ---

DEFAULT_DIAMETER_MM = 260

FALLBACK_SIZES = {
    "Miska": 160,
    "Talerz Deserowy": 200,
    "Talerz Obiadowy": 260,
    "Półmisek": 320
}

# Pełna baza wag standardowych
STANDARD_WAGI = {
    'kromka': 35, 'pajda': 50, 'bułka': 60, 'kajzerka': 60,
    'sztuka': 100, 'jajko': 55, 'szklanka': 250, 'kubek': 250,
    'kieliszek': 150, 'plaster': 20, 'garsc': 30,

    # --- WSADY I UKRYTE SKŁADNIKI ---
    'porcja_wsad': 120,      # Domyślna ilość mięsa/farszu wewnątrz dania
    'porcja_ser': 80,        # Domyślna ilość sera halloumi/feta wewnątrz
    'plaster_halloumi': 25,
    'kotlet_falafel': 30,

    # --- SOSY ---
    'miseczka': 50, 'porcja': 50, 'dip': 50, 'sos': 50
}

# Mapa wysokości jedzenia
HEIGHT_MAP = {
    'PLASKI_WARSTWA': 0.4,  # Cienkie: Wędlina, Ser żółty, Naleśnik
    # PLASKI_WARSTWA_GRUBA Średnie: Kotlet, Ryż płasko, Pizza, Omlet (ok. 1cm)
    'PLASKI_WARSTWA_GRUBA': 1.0,
    # Ziemniaki, Pulpety, Gulasz (Wysokie, strome ścianki)
    'KOPCZYK_ZWARTY': 3.0,
    'KOPCZYK_SYPKI': 2.4,        # Ryż, Kasza w górce (Stożek, schodzi do zera)
    'WYSOKI_KOPIEC': 4.5,
    'LUZNY_STOS': 4.5,
    'BRYLA_ZWARTA': 5.5,
    'ROLKA_NADZIEWANA': 3.5,  # Dla Tortilli/Wrapa
    'POWLOKA_SOS': 0.1,  # (1mm grubości dla sosu na makaronie)
    'CIECZ': 3.0,
    'SOS_W_MISECZCE': 2.5
}

# Mapa gęstości
DENSITY_MAP = {
    'NISKA': 0.3,
    'SREDNIA': 0.95,
    'WYSOKA': 1.15
}


# --- 2. SILNIK OBLICZENIOWY ---

def _calculate_single_item_weight(diameter_mm, component_data):
    """
    Oblicza wagę pojedynczego elementu (korzysta z bazy sztuk LUB geometrii).
    """

    # 1. BEZPIECZNE POBIERANIE (None -> 0)
    # Używamy składni (get(...) or 0), która zamienia None na 0
    ilosc = component_data.get('ilosc_sztuk') or 0
    percentage = component_data.get('procent_talerza') or 0

    # --- ŚCIEŻKA 1: PRODUKT POLICZALNY/SZTUKOWY ---
    if ilosc > 0:
        jednostka = component_data.get('typ_jednostki', '')
        if not jednostka:  # Zabezpieczenie na None
            jednostka = 'sztuka'

        jednostka = jednostka.lower()
        waga_jednostkowa = STANDARD_WAGI.get(jednostka, 100)
        return int(ilosc * waga_jednostkowa)

    # --- ŚCIEŻKA 2: GEOMETRIA (NA TALERZU) ---
    if not diameter_mm or diameter_mm < 50:
        return 0

    radius_cm = (diameter_mm / 10) / 2
    plate_area = math.pi * (radius_cm ** 2)

    # Używamy zmiennej percentage pobranej bezpiecznie na górze funkcji
    if percentage <= 0:
        return 0

    comp_area = plate_area * (percentage / 100)

    # Wysokość
    spatial_type = component_data.get('charakter_przestrzenny')
    if not spatial_type:
        spatial_type = 'NISKI_KOPCZYK'  # Fallback dla None

    height = HEIGHT_MAP.get(spatial_type, 2.0)

    # Modyfikatory objętości
    volume_modifier = 1.0

    if spatial_type == 'BRYLA_ZWARTA':
        volume_modifier = 0.66
    elif spatial_type == 'SOS_W_MISECZCE':
        volume_modifier = 0.35
    elif spatial_type == 'LUZNY_STOS':
        volume_modifier = 0.31
    elif spatial_type == 'ROLKA_NADZIEWANA':
        volume_modifier = 0.25
    elif spatial_type == 'KOPCZYK_ZWARTY':  # Ziemniaki wypełniają przestrzeń szczelnie (prawie walec)
        volume_modifier = 0.85
    elif spatial_type == 'KOPCZYK_SYPKI':
        volume_modifier = 0.60  # Ryż tworzy stożek -> ucinamy 40% objętości walca

    # Gęstość
    gestosc_raw = component_data.get('gestosc_wizualna')
    if not gestosc_raw:
        gestosc_raw = 'SREDNIA'  # Fallback dla None

    density_val = DENSITY_MAP.get(gestosc_raw, 0.95)

    # Wynik
    volume = comp_area * height * volume_modifier
    weight = volume * density_val

    return int(weight)


# --- 3. GŁÓWNA FUNKCJA ---

def enrich_meal_json(raw_json):
    """
    Spina dane z AI z fizyką.
    """
    geo = raw_json.get("geometry_analysis", {})
    food = raw_json.get("food_analysis", {})

    # A. Ustalanie średnicy (Priorytety z zabezpieczeniem przed None)
    diameter = 0

    # Bezpieczne pobieranie: (wartość lub 0)
    # To naprawia błąd w sekcji geometrii, gdy AI zwróci null
    calc_diam = geo.get("calculated_diameter_mm") or 0
    raw_width = geo.get("raw_visual_width_mm") or 0

    # Teraz porównanie jest bezpieczne (int > int)
    if calc_diam > 0:
        diameter = calc_diam
    elif raw_width > 0:
        diameter = raw_width
    elif geo.get("fallback_category_label"):
        label = geo.get("fallback_category_label")
        diameter = FALLBACK_SIZES.get(label, DEFAULT_DIAMETER_MM)

    if diameter == 0 and geo.get("vessel_type") == "PLATE":
        diameter = DEFAULT_DIAMETER_MM

    raw_json["meta_calculation"] = {"final_diameter_mm": diameter}

    # B. Składniki Pewne
    for item in food.get("skladniki_pewne", []):
        waga = _calculate_single_item_weight(diameter, item)
        item["calculated_weight_g"] = waga

    # C. Składniki Niejednoznaczne
    for item in food.get("skladniki_niejednoznaczne", []):
        waga_bryly = _calculate_single_item_weight(diameter, item)
        item["visual_object_weight_g"] = waga_bryly

        for wariant in item.get("warianty", []):
            wariant["calculated_weight_g"] = waga_bryly

    return raw_json
