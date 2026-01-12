import vertexai
from vertexai.generative_models import GenerativeModel, Part, HarmCategory, HarmBlockThreshold
import json

# Dwa zdjęcia jako referencja


# --- KONFIGURACJA ---
PROJECT_ID = "test-wellness-rag"

# LOCATION = "us-central1"
LOCATION = "global"

# ZALECENIE: Do zadań wizualnych wymagających precyzji (geometria),
# model 'pro' radzi sobie lepiej niż 'flash'.
# Jeśli masz dostęp, spróbuj "gemini-1.5-pro-001".
# Jeśli musisz używać flash, zostaw ten (zostawiam 1.5-flash, bo 2.5 jeszcze nie ma publicznie)

MODEL_NAME = "gemini-3-flash-preview"
# MODEL_NAME = "gemini-2.5-flash"

# IMAGE_PATH = "Foto_Plates/miska_2_2.jpg"
# IMAGE_PATH = "Foto_Plates/miska_2_1.jpg"
# IMAGE_PATH = "Foto_Plates/miska_3.jpg"

# IMAGE_PATH = "Foto_Plates/big_plate_5.jpg"
# IMAGE_PATH = "Foto_Plates/big_plate_1.jpg"

# IMAGE_PATH = "Foto_Plates/small_palte_2.jpg"
# IMAGE_PATH = "Foto_Plates/plate_2.jpg"
# IMAGE_PATH = "Foto_Plates/big_plate_4.jpg"

# Ścieżki do zdjęć (Top + Side)
# IMG_PATH_TOP = "Foto_Plates_2/Duzy_01_T.jpg"   # Widok z góry
# IMG_PATH_SIDE = "Foto_Plates_2/Duzy_01_L.jpg"  # Widok pod kątem/z boku

IMG_PATH_TOP = "Foto_Plates_2/Miska_01_T.jpg"   # Widok z góry
IMG_PATH_SIDE = "Foto_Plates_2/Miska_01_L.jpg"  # Widok pod kątem/z boku

# IMG_PATH_TOP = "Foto_Plates_2/Tale_Maly_01_T.jpg"   # Widok z góry
# IMG_PATH_SIDE = "Foto_Plates_2/Tale_Maly_01_L.jpg"  # Widok pod kątem/z boku


# Słownik wymiarów standardowych (wymagany do Wariantu B)
FALLBACK_SIZES = {
    "BOWL_STD": 130,
    "PLATE_S": 198,
    "PLATE_L": 260
}

SYSTEM_PROMPT = """
Jesteś ekspertem fotogrametrii i analizy przestrzennej.
Twoim celem jest precyzyjne określenie średnicy naczynia na podstawie sekwencji DWÓCH zdjęć.

MAPPING DANYCH WEJŚCIOWYCH (Kolejność ma znaczenie):
1. PIERWSZY OBRAZ: Widok z góry (Top-View). Służy do detekcji sztućców i pomiaru szerokości.
2. DRUGI OBRAZ: Widok z boku/kąta (Side-View). Służy WYŁĄCZNIE do oceny geometrii (czy to płaski talerz, czy głęboka miska).

HIERARCHIA DZIAŁANIA:

KROK 1: DETEKCJA TYPU NACZYNIA (Patrz na DRUGI obraz - Side-View)
- Czy naczynie ma wysokie ścianki boczne? -> Typ "BOWL".
- Czy naczynie jest płaskie? -> Typ "PLATE".

KROK 2: SZUKANIE REFERENCJI (Patrz na PIERWSZY obraz - Top-View)
- Priorytet 1: Widelec obiadowy (Standard: 192 mm).
- Priorytet 2: Nóż obiadowy (Standard: 220 mm).
- Priorytet 3: Łyżka duża (Standard: 195 mm).
- Priorytet 4: BRAK.

KROK 3: POMIAR LUB KATEGORYZACJA

WARIANT A: Znaleziono sztućce (Metoda: 'reference_scaling')
- Jeśli masz sztućce: Zmierz średnicę naczynia względem nich.
- UWAGA NA RANTY: Wiele talerzy ma szerokie, ozdobne brzegi (wzory, kolory). Mierz ZAWSZE do samej zewnętrznej krawędzi fizycznej talerza (OUTERMOST EDGE), a nie do granicy jedzenia czy wzoru.
- Jeśli w Kroku 1 wykryto "BOWL": Zastosuj korektę perspektywy (zmniejsz wynik o ~10-15%, ponieważ krawędź miski jest bliżej obiektywu).
- Wpisz wynik w pole 'calculated_diameter_mm'.

WARIANT B: Brak sztućców (Metoda: 'visual_category_fallback')
- Nie zgaduj liczb. Przypisz ETYKIETĘ na podstawie wizualnej oceny wielkości:
  - "BOWL_STD" -> Miska standardowa.
  - "PLATE_S"  -> Talerz mały/deserowy.
  - "PLATE_L"  -> Talerz duży/obiadowy.

WYMAGANY FORMAT JSON:
{
  "geometry_analysis": {
    "vessel_type": "string ('PLATE' lub 'BOWL')",
    "reference_found": boolean,
    "detected_reference_type": "string ('FORK', 'KNIFE', 'SPOON', 'NONE')",
    "measurement_method": "string ('reference_scaling' lub 'visual_category_fallback')",
    "calculated_diameter_mm": int lub null,
    "fallback_category_label": "string" lub null
  }
}
"""


def analyze_geometry_final(project_id, location, model_name, path_top, path_side):
    print(f"--- ANALIZA: 1.GÓRA({path_top}) + 2.BOK({path_side}) ---")

    vertexai.init(project=project_id, location=location)
    model = GenerativeModel(model_name, system_instruction=[SYSTEM_PROMPT])

    content_parts = []

    # 1. Dodajemy zdjęcie z GÓRY
    try:
        with open(path_top, "rb") as f:
            content_parts.append(Part.from_data(
                data=f.read(), mime_type="image/jpeg"))
    except FileNotFoundError:
        print(f"BŁĄD: Brak pliku Top-View: {path_top}")
        return

    # 2. Dodajemy zdjęcie z BOKU
    try:
        with open(path_side, "rb") as f:
            content_parts.append(Part.from_data(
                data=f.read(), mime_type="image/jpeg"))
    except FileNotFoundError:
        print(f"BŁĄD: Brak pliku Side-View: {path_side}")
        return

    content_parts.append(
        "Przeanalizuj geometrię zgodnie z ustaloną kolejnością zdjęć.")

    safety_settings = {
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
    }

    generation_config = {
        # "max_output_tokens": 1024,
        "max_output_tokens": 8192,
        "temperature": 0.0,
        "response_mime_type": "application/json"
    }

    try:
        response = model.generate_content(
            content_parts,
            generation_config=generation_config,
            safety_settings=safety_settings
        )

        result = json.loads(response.text)
        geo = result.get("geometry_analysis", {})

        # --- LOGIKA BIZNESOWA (Przetwarzanie wyników) ---
        final_diameter = 0
        method_desc = ""

        method = geo.get("measurement_method")

        # Scenariusz A: Wyliczono na podstawie sztućców
        if method == "reference_scaling" and geo.get("calculated_diameter_mm"):
            final_diameter = geo.get("calculated_diameter_mm")
            method_desc = f"Pomiar precyzyjny (Ref: {geo.get('detected_reference_type')})"

        # Scenariusz B: Użyto Fallbacku (Etykiety)
        elif method == "visual_category_fallback":
            label = geo.get("fallback_category_label")
            # Mapujemy etykietę na milimetry używając słownika z góry skryptu
            final_diameter = FALLBACK_SIZES.get(label, 260)
            method_desc = f"Standardowa kategoria (Etykieta: {label})"

        # --- PREZENTACJA WYNIKÓW ---
        print("\n" + "="*45)
        print(" WYNIK ANALIZY GEOMETRII")
        print("="*45)
        # POPRAWIONE NAZWY KLUCZY PONIŻEJ:
        print(f"TYP NACZYNIA:     {geo.get('vessel_type')}")
        print(f"REFERENCJA:       {geo.get('detected_reference_type')}")
        print(f"METODA:           {method}")
        print("-" * 45)
        print(f"ŚREDNICA (WYNIK): {final_diameter} mm")
        print(f"INFO:             {method_desc}")
        print("="*45)

        # print(json.dumps(result, indent=2)) # Odkomentuj do debugowania

    except Exception as e:
        print(f"BŁĄD: {e}")
        if 'response' in locals():
            print(response.text)


if __name__ == "__main__":
    analyze_geometry_final(PROJECT_ID, LOCATION,
                           MODEL_NAME, IMG_PATH_TOP, IMG_PATH_SIDE)
