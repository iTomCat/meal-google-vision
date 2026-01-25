import vertexai
from vertexai.generative_models import GenerativeModel, Image, GenerationConfig
import os
import json
from datetime import datetime

# -------------------------------------------------------------------
# TEST
# -------------------------------------------------------------------
# Poprawne określanie skłdników posiłku z list skłdników niepewnych
# -------------------------------------------------------------------

# --- KONFIGURACJA ---
PROJECT_ID = "test-wellness-rag"
LOCATION = "us-central1"
MODEL_NAME = "gemini-2.5-flash"
IMAGE_PATH = "test_3.jpg"


def analyze_meal_interactive():
    print(f"🚀 KROK 1: Analiza z opcjami wyboru (Model: {MODEL_NAME})")

    vertexai.init(project=PROJECT_ID, location=LOCATION)

    if not os.path.exists(IMAGE_PATH):
        print(f"❌ Brak pliku {IMAGE_PATH}")
        return
    image = Image.load_from_file(IMAGE_PATH)

    model = GenerativeModel(MODEL_NAME)

    # --- PROMPT INŻYNIERSKI (LOGIKA UX) ---
    prompt = """
      Jesteś sensorem wizualnym dla aplikacji dietetycznej.
      Twoim zadaniem jest ekstrakcja faktów z obrazu. Nie zgaduj tego, czego nie widać.

      Zanalizuj obraz i zwróć JSON podzielony na dwie sekcje:
      1. 'skladniki_pewne': To co widać ewidentnie (np. brokuł, kawałek mięsa, ryż).
        - Dla nich określ stopień przetworzenia (bardzo ważne dla glikemii).
      2. 'skladniki_niejednoznaczne': To produkty, których składu nie widać (np. typ makaronu, rodzaj coli, skład sosu, rodzaj ciasta, rodzaj naleśnika).
        - Dla nich wypełnij pole 'warianty'.
        - Dla nich wygeneruj listę prawdopodobnych wariantów.
        - WAŻNE: Podaj od 2 do maksymalnie 3 najbardziej prawdopodobnych opcji.
        - ZASADA: Jeśli istnieją tylko dwie logiczne możliwości (np. Z cukrem vs Zero), podaj tylko dwie. Nie wymyślaj trzeciej na siłę.

      Zwróć TYLKO czysty JSON w formacie:
      {
        "skladniki_pewne": [
          {
            "nazwa": "String (np. Ziemniaki)",
            "stan_wizualny": "String (np. Pieczone w mundurkach)",
            "procent_talerza": Integer,
            "stopien_przetworzenia": "Niski" | "Sredni" | "Wysoki (Puree/Frytki)"
          }
        ],
        "skladniki_niejednoznaczne": [
          {
            "przedmiot_wizualny": "String (np. Biały Sos, Szklanka z ciemnym napojem, Naleśnik)",
            "procent_talerza": Integer,
            "warianty": [
              { "nazwa": "String (np. Sos Jogurtowy)", "typ": "Light" },
              { "nazwa": "String (np. Sos Śmietanowo-Serowy)", "typ": "Heavy" }
            ]
          }
        ],
        "kontekst_talerza": {
          "czy_widac_warzywa": Boolean,
          "szacowany_rozmiar": "S" | "M" | "L"
        }
      }
  """

    print("👁️  Gemini analizuje i szuka niejednoznaczności...")

    try:
        response = model.generate_content(
            [image, prompt],
            generation_config=GenerationConfig(
                response_mime_type="application/json")
        )

        dane_json = json.loads(response.text)

        # Zapisz
        filename = f"interaktywny_meal_{datetime.now().strftime('%H%M%S')}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(dane_json, f, ensure_ascii=False, indent=4)

        print("\n" + "=" * 40)
        print(f"✅ GOTOWE! Otwórz plik: {filename}")
        print("=" * 40)

        # Szybki podgląd czy są opcje do wyboru
        ile_wyborow = len(dane_json.get("skladniki_do_wyboru", []))
        if ile_wyborow > 0:
            print(
                f"💡 Znaleziono {ile_wyborow} elementów wymagających decyzji użytkownika (np. sos, makaron).")
        else:
            print("💡 Wszystko wydaje się jednoznaczne.")

    except Exception as e:
        print(f"\n❌ Błąd: {e}")


if __name__ == "__main__":
    analyze_meal_interactive()
