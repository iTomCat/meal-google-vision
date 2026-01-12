from PIL import Image as PilImage, ImageDraw, ImageOps
import vertexai
from vertexai.generative_models import GenerativeModel, Image, GenerationConfig
import os
import json
import math

# --- KONFIGURACJA ---
PROJECT_ID = "test-wellness-rag"
LOCATION = "us-central1"
MODEL_NAME = "gemini-2.5-flash"
IMAGE_PATH = "Foto_Plates/plate_2.jpg"  # Upewnij się co do ścieżki


def analyze_plate_size():
    print(f"🚀 Analiza wielkości naczynia (Model: {MODEL_NAME})")

    # Inicjalizacja Vertex AI
    vertexai.init(project=PROJECT_ID, location=LOCATION)

    if not os.path.exists(IMAGE_PATH):
        print(f"❌ Brak pliku {IMAGE_PATH}")
        return

    # KROK 1: Normalizacja obrazu (Rotacja EXIF + Czysty plik dla Gemini)
    # To kluczowe, aby współrzędne Gemini pasowały do tego co widzimy.
    try:
        pil_img = PilImage.open(IMAGE_PATH)
        # Obróć zgodnie z EXIF (np. zdjęcia z telefonu)
        pil_img = ImageOps.exif_transpose(pil_img)

        # Zapisz jako tymczasowy plik "czysty" (bez EXIF rotation flag, po prostu obrócone piksele)
        temp_filename = "temp_gemini_input.jpg"
        pil_img.save(temp_filename)

        # Użyj tego pliku dla Gemini
        image_for_gemini = Image.load_from_file(temp_filename)
        width, height = pil_img.size
        print(f"📏 Wymiary obrazu po normalizacji: {width}x{height}")

    except Exception as e:
        print(f"❌ Błąd przetwarzania obrazu: {e}")
        return

    model = GenerativeModel(MODEL_NAME)

    # Prompt
    prompt = """
    Jesteś ekspertem wideometrii i precyzyjnego widzenia komputerowego.
    
    Twoim zadaniem jest wykrycie "Outer Bounding Box" (Zewnętrznego Obrysu) dla widelca i naczynia.
    
    1. "widelec": 
       - Ramka musi być MAKSYMALNIE CIASNA na metalu.
       - GÓRA: Czubki zębów.
       - DÓŁ: Koniec metalowego uchwytu.
       - KRYTYCZNE: IGNORUJ CIEŃ I MOKRE PLAMY pod widelcem! Ramka musi kończyć się na metalu! Nie obejmuj cienia rzucanego na stół!
    
    2. "naczynie": 
       - Ramka musi obejmować CAŁE naczynie (zewnętrzna krawędź).
       - Jeśli to talerz, obejmij krawędź (rant).
    
    Zwróć JSON:
    {
      "box_widelec": [ymin, xmin, ymax, xmax],
      "box_naczynie": [ymin, xmin, ymax, xmax],
      "typ_naczynia": "String",
      "meta": {
        "kat_kamery": "String",
        "wspolczynnik_korekcji": Float,
        "wyjasnienie_korekcji": "String"
      }
    }
       - Oszacuj "wspolczynnik_korekcji" (1.0 - 1.5) na podstawie kąta.
       - Pamiętaj: współrzędne muszą być znormalizowane (0.0 - 1.0).
    """

    try:
        response = model.generate_content(
            [image_for_gemini, prompt],
            generation_config=GenerationConfig(
                response_mime_type="application/json",
                temperature=0.0
            )
        )

        dane = json.loads(response.text)

        box_widelec = dane.get("box_widelec")
        box_naczynie = dane.get("box_naczynie")
        typ_naczynia = dane.get("typ_naczynia", "talerz")
        meta = dane.get("meta", {})
        correction = meta.get("wspolczynnik_korekcji", 1.0)

        # Normalizacja współrzędnych
        def normalize_box(box):
            if not box:
                return None
            if any(val > 1.0 for val in box):
                return [val / 1000.0 for val in box]
            return box

        box_widelec = normalize_box(box_widelec)
        box_naczynie = normalize_box(box_naczynie)

        if box_widelec and box_naczynie:
            # 🖼️ Rysowanie (na obrazie pil_img który jest zsynchronizowany z Gemini)
            try:
                debug_img = pil_img.copy()  # Kopia do rysowania
                draw = ImageDraw.Draw(debug_img)

                def draw_rect(box, color, label):
                    if not box:
                        return
                    ymin, xmin, ymax, xmax = box

                    left = xmin * width
                    top = ymin * height
                    right = xmax * width
                    bottom = ymax * height

                    # Rysuj ramkę
                    draw.rectangle([left, top, right, bottom],
                                   outline=color, width=8)
                    draw.line([left, top, right, bottom], fill=color, width=2)
                    draw.line([left, bottom, right, top], fill=color, width=2)

                    print(f"   [{label}] Box Relative: {box}")
                    print(
                        f"   [{label}] Pixels: {int(left)},{int(top)} - {int(right)},{int(bottom)}")

                print("🖌️ Rysowanie obiektów...")
                draw_rect(box_widelec, "red", "WIDELEC")
                draw_rect(box_naczynie, "blue", "NACZYNIE")

                debug_filename = "debug_plate.jpg"
                debug_img.save(debug_filename)
                print(
                    f"🖼️ Zapisano obraz debugowania: {os.path.abspath(debug_filename)}")
            except Exception as e:
                print(f"⚠️ Nie udało się zapisać obrazka debugowania: {e}")

            # Obliczenia
            f_ymin, f_xmin, f_ymax, f_xmax = box_widelec
            f_w_px = (f_xmax - f_xmin) * width
            f_h_px = (f_ymax - f_ymin) * height
            fork_len_px = math.hypot(f_w_px, f_h_px)

            n_ymin, n_xmin, n_ymax, n_xmax = box_naczynie
            n_w_px = (n_xmax - n_xmin) * width
            n_h_px = (n_ymax - n_ymin) * height
            dish_len_px = max(n_w_px, n_h_px)

            # Skalowanie i Korekcja Geometryczna
            scale_raw = 192.0 / fork_len_px
            raw_width_mm = dish_len_px * scale_raw

            # Sprawdzenie kształtu talerza (wykrywanie kąta)
            plate_ratio = 1.0
            if n_h_px > 0:
                plate_ratio = n_w_px / n_h_px if n_w_px > n_h_px else n_h_px / n_w_px

            final_width_mm = raw_width_mm
            method = "Standard"

            # Logika adaptacyjna
            if plate_ratio > 1.15:
                # Wykryto elipsę -> znaczy że jest kąt, nawet jak Gemini twierdzi inaczej
                print(
                    f"⚠️ Wykryto zniekształcenie perspektywiczne (Ratio talerza: {plate_ratio:.2f})")

                # Próba "odkręcenia" skrótu widelca
                # Zakładając że widelec leży w tej samej płaszczyźnie co talerz i jest zorientowany wzdłuż osi skrótu
                fork_len_corrected = fork_len_px * plate_ratio
                scale_geo = 192.0 / fork_len_corrected
                geo_width_mm = dish_len_px * scale_geo

                # Uśredniamy wynik surowy (zakładający brak skrótu widelca) i geometryczny (pełny skrót)
                # Często prawda leży pośrodku (np. widelec nie jest idealnie w osi Y lub głębia wpływa przeciwnie)
                final_width_mm = (raw_width_mm + geo_width_mm) / 2
                method = "Hybrid (Aspect Ratio Fix)"
                correction = plate_ratio  # Nadpisujemy dla raportu
            else:
                # Użyj korekcji z Gemini jeśli jest sensowna
                final_width_mm = raw_width_mm * correction
                if correction != 1.0:
                    method = "AI Correction"

            # Opis
            opis = ""
            if final_width_mm < 160:
                opis = "mała" if typ_naczynia == "miseczka" else "mały"
            elif final_width_mm < 240:
                opis = "średnia" if typ_naczynia == "miseczka" else "średni"
            else:
                opis = "duża" if typ_naczynia == "miseczka" else "duży"

            print("="*40)
            print(f"Wynik analizy (Model: {MODEL_NAME}):")
            print("-" * 20)
            print(f"Kąt kamery (AI): {meta.get('kat_kamery')}")
            print(f"Spłaszczenie talerza: {plate_ratio:.2f}")
            print(f"Metoda obliczeń: {method}")
            print("-" * 20)
            print(f"Widelec (px): {fork_len_px:.1f}")
            print(f"Naczynie (px): {dish_len_px:.1f}")
            print(f"Surowy wynik: {raw_width_mm:.0f} mm")
            print("-" * 20)
            print(f"Widelec (ref): 192 mm")
            print(f"FINALNA SZEROKOŚĆ: {final_width_mm:.0f} mm")
            print(
                f"Opis: {opis.capitalize()} {typ_naczynia} szer {final_width_mm:.0f} mm")
            print("="*40)

            # Sprzątanie
            if os.path.exists(temp_filename):
                os.remove(temp_filename)

        else:
            print("⚠️ Nie udało się wykryć obu obiektów.")

    except Exception as e:
        print(f"\n❌ Błąd: {e}")


if __name__ == "__main__":
    analyze_plate_size()
