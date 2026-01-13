 if not plate_mm or plate_mm < 50:
        return 0

    # 1. Powierzchnia talerza (cm2)
    radius_cm = (plate_mm / 10) / 2
    plate_area = math.pi * (radius_cm ** 2)

    # 2. Powierzchnia składnika
    percentage = component_data.get('procent_talerza', 0)
    if percentage <= 0:
        return 0  # Ani sztuki, ani procent = 0g

    comp_area = plate_area * (percentage / 100)