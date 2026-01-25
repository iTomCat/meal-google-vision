# flake8: noqa

import json

# -------------------------------------------------------------------
# Wybór czy foto zawiera danie - etylietę - menu
# -------------------------------------------------------------------
# Zwraca info czego zdjęcie zosatło zrobione
# Uwaga: w pierwszej linii na razie wyświetlanie błędów jest zablokowane bo na eazie nie rozwijam tego mofułu
# -------------------------------------------------------------------

# --- KONFIGURACJA ---
PROJECT_ID = "test-wellness-rag"
LOCATION = "global"
MODEL_NAME = "gemini-3-flash-preview"

# ZDJĘCIA TESTOWE
# IMG_PATH_TOP = "Foto_Plates_2/dish_1_T.png"
# IMG_PATH_SIDE = "Foto_Plates_2/dish_1_L.jpg"


def analyze_image(image_bytes):
    # 1. Szybka klasyfikacja
    image_type = classify_image(image_bytes) 
    
    # 2. Wybór ścieżki (Router)
    if image_type == "posilek":
        # Tutaj Twój obecny duży prompt
        return process_meal_analysis(image_bytes)
    
    elif image_type == "menu":
        # Prompt zoptymalizowany pod OCR i wybory glikemiczne
        return process_menu_scanner(image_bytes)
    
    elif image_type == "etykieta":
        # Prompt skupiony na składnikach i tabeli wartości
        return process_label_scanner(image_bytes)
    
    else:
        return {"error": "Nie rozpoznałem jedzenia, menu ani etykiety."}