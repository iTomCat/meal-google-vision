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

# Pełna baza wag standardowych (Twoja lista)
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

    # --- NOWE: WSADY I UKRYTE SKŁADNIKI ---
    'porcja_wsad': 120,      # Domyślna ilość mięsa/farszu wewnątrz dania
    'porcja_ser': 80,        # Domyślna ilość sera halloumi/feta wewnątrz
    'plaster_halloumi': 25,
    'kotlet_falafel': 30,    # Jeden falafel

    # --- ZABEZPIECZENIA DLA SOSÓW POZA TALERZEM ---
    'miseczka': 50,     # Standardowy ramekin sosu
    'porcja': 50,       # Porcja sosu/dipu
    'dip': 50,
    'sos': 50
}

# Mapa wysokości jedzenia
HEIGHT_MAP = {
    'PLASKI_WARSTWA': 0.8,
    'NISKI_KOPCZYK': 2.0,
    'WYSOKI_KOPIEC': 4.5,
    'LUZNY_STOS': 4.5,
    'BRYLA_ZWARTA': 5.5,
    'ROLKA_NADZIEWANA': 3.5,  # Dla Tortilli/Wrapa
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
    # Jeśli nie ma sztuk, musi być procent.

    # Zabezpieczenie przed błędnym wymiarem talerza
    if not diameter_mm or diameter_mm < 50:
        return 0

    # 1. Powierzchnia talerza (cm2)
    radius_cm = (diameter_mm / 10) / 2
    plate_area = math.pi * (radius_cm ** 2)

    # 2. Powierzchnia składnika
    percentage = component_data.get('procent_talerza', 0)
    if percentage <= 0:
        return 0  # Ani sztuki, ani procent = 0g

    comp_area = plate_area * (percentage / 100)

    # 3. Wysokość + Modyfikatory (logika modyfikatorów)
    spatial_type = component_data.get(
        'charakter_przestrzenny', 'NISKI_KOPCZYK')
    height = HEIGHT_MAP.get(spatial_type, 2.0)

    # Modyfikatory objętości (korekta dla specyficznych kształtów)
    volume_modifier = 1.0
    if spatial_type == 'BRYLA_ZWARTA':
        volume_modifier = 0.66
    elif spatial_type == 'SOS_W_MISECZCE':
        volume_modifier = 0.35
    elif spatial_type == 'LUZNY_STOS':
        volume_modifier = 0.31
    elif spatial_type == 'ROLKA_NADZIEWANA':
        volume_modifier = 0.25

    # 4. Gęstość
    density_val = DENSITY_MAP.get(component_data.get('gestosc_wizualna'), 0.95)

    # 5. Wynik
    volume = comp_area * height * volume_modifier
    weight = volume * density_val

    return int(weight)


# --- 3. GŁÓWNA FUNKCJA PODAJE GOTOWE DANE DO FLUTTERA ---

def enrich_meal_json(raw_json):
    """
    Przyjmuje surowy JSON z Vertex AI.
    Zwraca JSON z przeliczonymi wagami dla wszystkich opcji.
    """
    geo = raw_json.get("geometry_analysis", {})
    food = raw_json.get("food_analysis", {})

    # A. Ustalanie średnicy (Priorytety)
    diameter = 0
    if geo.get("calculated_diameter_mm", 0) > 0:
        diameter = geo.get("calculated_diameter_mm")
    elif geo.get("raw_visual_width_mm", 0) > 0:
        diameter = geo.get("raw_visual_width_mm")
    elif geo.get("fallback_category_label"):
        label = geo.get("fallback_category_label")
        diameter = FALLBACK_SIZES.get(label, DEFAULT_DIAMETER_MM)

    if diameter == 0 and geo.get("vessel_type") == "PLATE":
        diameter = DEFAULT_DIAMETER_MM

    # Zapisujemy info dla aplikacji, jaka średnica została użyta
    raw_json["meta_calculation"] = {"final_diameter_mm": diameter}

    # B. Przeliczanie SKŁADNIKÓW PEWNYCH
    skladniki_pewne = food.get("skladniki_pewne", [])
    for item in skladniki_pewne:
        # Tu używamy naszej pełnej logiki (Standardy + Geometria)
        waga = _calculate_single_item_weight(diameter, item)
        item["calculated_weight_g"] = waga

    # C. Przeliczanie SKŁADNIKÓW NIEJEDNOZNACZNYCH
    skladniki_niejedno = food.get("skladniki_niejednoznaczne", [])
    for item in skladniki_niejedno:
        # 1. Liczymy wagę wizualną "bryły" (np. szklanki)
        waga_bryly = _calculate_single_item_weight(diameter, item)

        # Zapisujemy w obiekcie nadrzędnym
        item["visual_object_weight_g"] = waga_bryly

        # 2. Przypisujemy tę wagę do KAŻDEGO wariantu
        # Dzięki temu Flutter ma gotową wagę niezależnie co user kliknie
        for wariant in item.get("warianty", []):
            wariant["calculated_weight_g"] = waga_bryly

    return raw_json
