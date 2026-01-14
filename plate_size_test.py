import vertexai
from vertexai.generative_models import GenerativeModel, Part, HarmCategory, HarmBlockThreshold
import json

# --- KONFIGURACJA ---
PROJECT_ID = "test-wellness-rag"
LOCATION = "global"

# MODEL_NAME = "gemini-3-flash-preview"
# Stabilny model, ale 3-preview też zadziała z tym kodem
MODEL_NAME = "gemini-3-flash-preview"

# --- WYBIERZ ZDJĘCIA DO TESTU ---
# IMG_PATH_TOP = "Foto_Plates_2/danie_2a_T.jpg"   # Widok z góry
# IMG_PATH_SIDE = "Foto_Plates_2/danie_2_L.jpg"  # Widok pod kątem/z boku

# IMG_PATH_TOP = "Foto_Plates_2/danie_1_T.jpg"   # Widok z góry
# IMG_PATH_SIDE = "Foto_Plates_2/danie_1_L.jpg"  # Widok pod kątem/z boku

# IMG_PATH_TOP = "Foto_Plates_2/Duzy_01_T.jpg"   # Widok z góry
# IMG_PATH_SIDE = "Foto_Plates_2/Duzy_01_L.jpg"  # Widok pod kątem/z boku

# IMG_PATH_TOP = "Foto_Plates_2/Duzy_02_T.jpg"   # Widok z góry
# IMG_PATH_SIDE = "Foto_Plates_2/Duzy_02_L.jpg"  # Widok pod kątem/z boku

IMG_PATH_TOP = "Foto_Plates_2/Miska_01_T.jpg"
IMG_PATH_SIDE = "Foto_Plates_2/Miska_01_L.jpg"

# IMG_PATH_TOP = "Foto_Plates_2/Tale_Maly_02_T.jpg"
# IMG_PATH_SIDE = "Foto_Plates_2/Tale_Maly_02_L.jpg"


# -------------------------------------------------------------------
# TEST
# Określanie wielkości talerza/miski na podstawie dwóch zdjęć. OK
# -------------------------------------------------------------------
# UWAGA LEPIEJ LICZY GDY TALERZ JEST WIĘKSZY TAK JAK NA ZDJĘCIU
# danie_2a_T.jpg A NIE JAK NA ZDJĘCIU danie_2_T.jpg
# -------------------------------------------------------------------

# Słownik wymiarów standardowych (TYLKO dla Wariantu B - gdy brak sztućców)
FALLBACK_SIZES = {
    "BOWL_STD": 130,
    "PLATE_S": 198,
    "PLATE_L": 260
}

# --- PROMPT (SERCE ROZWIĄZANIA) ---
SYSTEM_PROMPT = """
Jesteś ekspertem fotogrametrii. Twoim celem jest precyzyjne określenie średnicy naczynia na podstawie DWÓCH zdjęć.

MAPPING DANYCH WEJŚCIOWYCH (Kolejność ma znaczenie):
1. PIERWSZY OBRAZ: Widok z góry (Top-View). Służy do detekcji sztućców i pomiaru szerokości.
2. DRUGI OBRAZ: Widok z boku/kąta (Side-View). Służy WYŁĄCZNIE do oceny geometrii.

ALGORYTM DECYZYJNY:

KROK 1: IDENTYFIKACJA (Side-View)
- Zdecyduj: Czy to "BOWL" (wysokie ścianki) czy "PLATE" (płaski)?

KROK 2: REFERENCJA (Top-View)
- Znajdź: Widelec (192mm), Nóż (220mm) lub Łyżkę (195mm).

KROK 3: WYBÓR LOGIKI POMIAROWEJ
Poniżej znajdują się dwie rozłączne definicje pomiaru.
JEŚLI zidentyfikowałeś PLATE -> Stosuj WYŁĄCZNIE zasady wewnątrz znacznika <CASE_PLATE>.
JEŚLI zidentyfikowałeś BOWL  -> Stosuj WYŁĄCZNIE zasady wewnątrz znacznika <CASE_BOWL>.

<CASE_PLATE>
    CEL: Maksymalna średnica fizyczna (włącznie z rantem).
    1. ELIMINACJA JEDZENIA (Zasada Koncentryczności): Spójrz na środek. Czy widzisz okrągły obiekt (owoc, pomelo, bułka) leżący na talerzu?
       - JEŚLI TAK: To jest jedzenie. IGNORUJ mniejszy, wewnętrzny okrąg.
       - SZUKAJ: Większego okręgu pod spodem (naczynia).
    2. ANALIZA RANTU: Sprawdź najbardziej zewnętrzną krawędź. Jeśli widzisz wzór (romby, paski, dekoracje) - to JEST część talerza.
    3. POMIAR: Mierz od zewnętrznego końca wzoru z lewej do zewnętrznego końca wzoru z prawej (NAJSZERSZY możliwy obrys).
    4. ZAPIS:
       - Wpisz ten wymiar do pola 'raw_visual_width_mm'.
       - Ponieważ talerz jest płaski, wpisz ten sam wymiar do pola 'calculated_diameter_mm'.
</CASE_PLATE>

<CASE_BOWL>
    CEL: Realna średnica otworu (skorygowana o perspektywę).
    1. ELIMINACJA JEDZENIA: Jeśli w misce znajduje się okrągły obiekt (np. zupa, owoc) tworzący mniejszy krąg -> IGNORUJ GO. Interesuje nas krawędź naczynia.
    2. POMIAR WSTĘPNY: Zmierz wizualną szerokość otworu na zdjęciu z góry (między najbardziej zewnętrznymi punktami krawędzi naczynia).
    3. ZAPIS SUROWY: Wpisz ten wizualny pomiar do pola 'raw_visual_width_mm'.
    4. OBLICZENIE KOREKTY: Odejmij 16% od wizualnego pomiaru naczynia.
       (Formuła: calculated_diameter_mm = raw_visual_width_mm * 0.16).
</CASE_BOWL>

WARIANT C: BRAK SZTUĆCÓW (Fallback)
- Przypisz etykietę: "BOWL_STD", "PLATE_S", "PLATE_L".

WYMAGANY FORMAT JSON:
{
  "geometry_analysis": {
    "vessel_type": "string ('PLATE' lub 'BOWL')",
    "visual_rim_check": "string (Opis rantu/krawędzi)",
    "reference_found": boolean,
    "detected_reference_type": "string",
    "measurement_method": "string ('reference_scaling' lub 'visual_category_fallback')",
    "raw_visual_width_mm": int lub null (Wymiar wizualny PRZED korektą),
    "calculated_diameter_mm": int lub null (Wynik końcowy PO korekcie),
    "fallback_category_label": "string" lub null
  }
}
"""


def analyze_geometry_final(project_id, location, model_name, path_top, path_side):
    print(f"--- ANALIZA: 1.GÓRA({path_top}) + 2.BOK({path_side}) ---")

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
        print("BŁĄD: Brak plików zdjęć.")
        return

    content_parts.append("Przeanalizuj geometrię. Zwróć JSON.")

    # Używamy liczby 3 (BLOCK_ONLY_HIGH) dla kompatybilności
    safety_settings = {
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
    }

    # Limit 8192 tokenów - zapobiega ucinaniu odpowiedzi
    generation_config = {
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

        # --- LOGIKA WYŚWIETLANIA ---
        final_diameter = 0
        raw_width = 0
        method_desc = ""

        # Pobieranie kluczy zgodnych z nowym Promptem
        vessel_type = geo.get("vessel_type")
        ref_type = geo.get("detected_reference_type")
        method = geo.get("measurement_method")
        raw_width = geo.get("raw_visual_width_mm")

        if method == "reference_scaling" and geo.get("calculated_diameter_mm"):
            # BEZPOŚREDNI WYNIK Z MODELU (Bez dociągania)
            final_diameter = geo.get("calculated_diameter_mm")
            method_desc = f"Ref: {ref_type} (Czysty pomiar AI)"

        elif method == "visual_category_fallback":
            label = geo.get("fallback_category_label")
            final_diameter = FALLBACK_SIZES.get(label, 260)
            method_desc = f"Brak referencji (Kategoria: {label})"

        # --- RAPORT ---
        print("\n" + "="*45)
        print(" WYNIK ANALIZY GEOMETRII")
        print("="*45)
        print(f"TYP NACZYNIA:     {vessel_type}")
        print(f"REFERENCJA:       {ref_type}")
        print(f"METODA:           {method}")
        if raw_width:
            print(f"SUROWY OBRAZ:     {raw_width} mm")
        print("-" * 45)
        print(f"ŚREDNICA (WYNIK): {final_diameter} mm")
        print(f"INFO:             {method_desc}")
        print("="*45)

    except Exception as e:
        print(f"BŁĄD: {e}")
        if 'response' in locals():
            print("Fragment odpowiedzi:", response.text[:200])


if __name__ == "__main__":
    analyze_geometry_final(PROJECT_ID, LOCATION,
                           MODEL_NAME, IMG_PATH_TOP, IMG_PATH_SIDE)
