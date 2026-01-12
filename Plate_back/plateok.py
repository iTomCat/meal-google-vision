import vertexai
from vertexai.generative_models import GenerativeModel, Part, FinishReason
import vertexai.preview.generative_models as generative_models
import json

# Tu jest dobre określanie wielkośći talerza. Wielkość miski jest zawyona do poprawenia
# Jedno zdjęcie, widelec jako referencja

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
IMAGE_PATH = "Foto_Plates/miska_2_1.jpg"
# IMAGE_PATH = "Foto_Plates/miska_3.jpg"

# IMAGE_PATH = "Foto_Plates/big_plate_5.jpg"
# IMAGE_PATH = "Foto_Plates/big_plate_1.jpg"

# IMAGE_PATH = "Foto_Plates/small_palte_2.jpg"
# IMAGE_PATH = "Foto_Plates/plate_2.jpg"
# IMAGE_PATH = "Foto_Plates/big_plate_4.jpg"

# --- NOWY, LEPSZY PROMPT (CHAIN OF THOUGHT) ---
SYSTEM_PROMPT = """
Jesteś ekspertem Computer Vision specjalizującym się w fotogrametrii żywności.
Twoim celem jest precyzyjny pomiar średnicy naczynia, używając widelca jako referencji, uwzględniając zniekształcenia perspektywy.

STANDARDY:
- Widelec obiadowy (Reference) = 192 mm.

INSTRUKCJA ANALIZY (Chain of Thought):

KROK 1: KLASYFIKACJA GEOMETRII (Kluczowe dla precyzji)
- Określ typ naczynia:
  A) "FLAT_PLATE" (Talerz płaski) - Krawędź naczynia leży blisko blatu (na tej samej wysokości co widelec).
  B) "DEEP_BOWL" (Miska/Głęboki talerz) - Krawędź naczynia jest uniesiona względem blatu (bliżej kamery).

KROK 2: WIZUALNE PORÓWNANIE (PIKSELE)
- Porównaj wizualną szerokość naczynia do długości widelca w pikselach.
- Ustal "Raw Visual Ratio" (np. naczynie wygląda na 0.9 długości widelca).

KROK 3: KOREKTA PERSPEKTYWY (FIZYKA)
- Jeśli typ to "FLAT_PLATE": Twoje "Raw Visual Ratio" jest poprawne.
- Jeśli typ to "DEEP_BOWL": Zastosuj korektę paralaksy. Ponieważ krawędź miski jest bliżej kamery niż widelec, wydaje się ona sztucznie większa.
  -> AKCJA: Zmniejsz oszacowane Ratio o około 10-15% (np. z 1.0 na 0.85-0.90), aby uzyskać rzeczywisty rozmiar podstawy/średnicy użytkowej.

KROK 4: OBLICZENIA
- Wynik = Reference Length * Corrected Ratio.

ZASADA BEZPIECZEŃSTWA:
- Jeśli brak sztućców -> Fallback 260 mm (tylko w ostateczności).

WYMAGANY FORMAT ODPOWIEDZI (JSON):
{
  "analysis_steps": {
    "detected_reference": "string",
    "vessel_type": "string ('FLAT_PLATE' lub 'DEEP_BOWL')",
    "visual_comparison_desc": "string (Opisz co widzisz + wzmianka o wysokości krawędzi jeśli to miska)",
    "raw_visual_ratio": float (To co widzą oczy),
    "perspective_correction_factor": float (np. 1.0 dla talerza, 0.85-0.9 dla miski),
    "final_corrected_ratio": float
  },
  "measurement_result": {
    "reference_length_mm": int,
    "calculated_diameter_mm": int,
    "calculated_diameter_cm": float,
    "method_used": "string"
  }
}
"""


def test_plate_size_cot(project_id, location, model_name, image_path):
    print(f"--- ANALIZA OBRAZU: {image_path} ---")

    vertexai.init(project=project_id, location=location)
    model = GenerativeModel(model_name, system_instruction=[SYSTEM_PROMPT])

    try:
        with open(image_path, "rb") as f:
            image_bytes = f.read()
        image_part = Part.from_data(data=image_bytes, mime_type="image/jpeg")
    except FileNotFoundError:
        print(f"BŁĄD: Nie znaleziono pliku {image_path}")
        return

    generation_config = {
        "max_output_tokens": 8192,
        "temperature": 0.0,  # Zero kreatywności, czysta logika
        "response_mime_type": "application/json"
    }

    safety_settings = {
        generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: generative_models.HarmBlockThreshold.BLOCK_ONLY_HIGH,
    }

    print(f"Model: {model_name}. Przetwarzanie...")

    try:
        response = model.generate_content(
            [image_part, ""],
            generation_config=generation_config,
            safety_settings=safety_settings
        )

        result = json.loads(response.text)

        print("\n" + "="*40)
        print(" WYNIK Z LOGIKĄ PROPORCJI (CoT)")
        print("="*40)

        steps = result.get('analysis_steps', {})
        measure = result.get('measurement_result', {})

        print(f"1. OPIS RELACJI: {steps.get('visual_comparison_desc')}")
        print(
            f"2. OSZACOWANY STOSUNEK (Ratio): {steps.get('estimated_ratio_plate_to_ref')}")
        print(
            f"3. DŁUGOŚĆ WIDELCA (Ref): {measure.get('reference_length_mm')} mm")
        print("-" * 40)
        print(
            f"WYNIK KOŃCOWY (ŚREDNICA): {measure.get('calculated_diameter_cm')} cm")
        print("-" * 40)
        print("DEBUG JSON:\n", json.dumps(result, indent=2, ensure_ascii=False))

    except Exception as e:
        print(f"BŁĄD: {e}")
        if 'response' in locals():
            print(response.text)


if __name__ == "__main__":
    test_plate_size_cot(PROJECT_ID, LOCATION, MODEL_NAME, IMAGE_PATH)
