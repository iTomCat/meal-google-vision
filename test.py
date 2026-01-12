import vertexai
from vertexai.generative_models import GenerativeModel
from google.api_core.exceptions import PermissionDenied, NotFound

# --- USTAWIENIA ---
PROJECT_ID = "test-wellness-rag"
IMAGE_PATH = "test.jpg"

# Lista regionów do sprawdzenia. Jeśli jeden zadziała - wygrałeś.
regiony_do_testu = ["us-central1", "us-east4", "europe-west1", "us-west1"]


def testuj_polaczenie():
    print(f"🕵️‍♂️ Rozpoczynam diagnostykę dla projektu: {PROJECT_ID}")

    for region in regiony_do_testu:
        print(f"\n--- Sprawdzam region: {region} ---")
        try:
            vertexai.init(project=PROJECT_ID, location=region)
            # Próbujemy najprostszego modelu
            model = GenerativeModel("gemini-2.5-flash")

            # Próba "Ping" - wysyłamy samo "Hello" (bez zdjęcia na razie)
            response = model.generate_content("Hello")

            print(f"✅ SUKCES! Region {region} działa!")
            print(f"🤖 Odpowiedź AI: {response.text}")
            print("👉 Zmień w swoim głównym kodzie LOCATION na ten region.")
            return  # Kończymy, bo znaleźliśmy działający

        except NotFound:
            print(
                f"❌ Błąd 404 w {region}. (Model niedostępny lub brak Billing Account)")
        except PermissionDenied:
            print(
                f"⛔ Błąd Uprawnień w {region}. (Sprawdź Billing lub API Enablement)")
        except Exception as e:
            print(f"⚠️ Inny błąd w {region}: {e}")

    print("\n\n--- WERDYKT ---")
    print("Jeśli wszędzie było 404/PermissionDenied -> Na 100% problem z Billingiem (Kartą).")
    print("Wejdź na: https://console.cloud.google.com/billing")


if __name__ == "__main__":
    testuj_polaczenie()
