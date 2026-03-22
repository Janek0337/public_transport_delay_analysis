import math

def oblicz_odleglosc(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000.0
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    lon1_rad = math.radians(lon1)
    lon2_rad = math.radians(lon2)

    delta_lat = abs(lon2_rad - lon1_rad)
    delta_lon = abs(lat2_rad - lat1_rad)

    srednia_lat = (lat1_rad + lat2_rad) / 2.0
    x = delta_lon * math.cos(srednia_lat)
    y = delta_lat
    dystans = R * math.sqrt(x**2 + y**2)

    return round(dystans)

def czas_na_sekundy(czas_str: str) -> int:
    
    czas_str = czas_str.split(' ')[-1] # jeśli z datą to odcinam
    godziny, minuty, sekundy = map(int, czas_str.split(':'))

    wynik = sekundy + 60*minuty + 3600*godziny
    return wynik