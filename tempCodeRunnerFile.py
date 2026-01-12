<CASE_PLATE>
    CEL: Maksymalna średnica fizyczna (włącznie z rantem).
    1. ELIMINACJA JEDZENIA (Zasada Koncentryczności): Spójrz na środek. Czy widzisz okrągły obiekt (owoc, bułka) leżący na talerzu?
       - JEŚLI TAK: To jedzenie. IGNORUJ mniejszy, wewnętrzny okrąg. Szukaj większego okręgu pod spodem.
    2. ANALIZA RANTU: Sprawdź krawędź. Jeśli widzisz wzór (romby, paski) - to JEST część talerza.
    3. POMIAR: Mierz od zewnętrznego końca wzoru z lewej do zewnętrznego końca wzoru z prawej (NAJSZERSZY obrys).
    4. ZAPIS: Wpisz wynik do 'raw_visual_width_mm' oraz 'calculated_diameter_mm'.
</CASE_PLATE>

<CASE_BOWL>
    CEL: Realna średnica otworu (skorygowana o perspektywę).
    1. ELIMINACJA JEDZENIA: Jeśli w misce znajduje się obiekt tworzący mniejszy krąg -> IGNORUJ GO. Mierz krawędź naczynia.
    2. POMIAR WSTĘPNY: Zmierz wizualną szerokość otworu na zdjęciu z góry.
    3. ZAPIS SUROWY: Wpisz do 'raw_visual_width_mm'.
    4. KOREKTA: Odejmij 16% od wizualnego pomiaru.
       (Formuła: calculated_diameter_mm = raw_visual_width_mm * 0.84).
</CASE_BOWL>