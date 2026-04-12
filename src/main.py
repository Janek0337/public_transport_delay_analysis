import logging
from src.logger_setup import setup_logger
from dotenv import load_dotenv, find_dotenv
import os
import src.kolektor_danych as kolektor_danych
from src.TrackerZTM import TrackerZTM
import time
from pathlib import Path
from src.WeatherTracker import WeatherTracker

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / 'data'

def main():

    logger = logging.getLogger(__name__)
    setup_logger(True)

    logger.info("Start")

    dotenv_path = find_dotenv()
    load_dotenv(dotenv_path)
    API_KEY = os.getenv('API_KEY')
    if API_KEY is None:
        logging.error("Nie znaleziono klucza api w pliku .env")
        exit(1)
    if API_KEY == "":
        logging.error("Klucz api w pliku .env jets pusty")
        exit(1)

    kolektor_danych.stworz_baze_polozen_przystankow(API_KEY)
    linie = ['523', '148']
    for linia in linie:
        kolektor_danych.stworz_trase_linii(API_KEY, linia)
        kolektor_danych.stworz_rozklad_linii(API_KEY, linia)

    tracker = TrackerZTM(linie)

    punkt_wiatraczna = (52.245051314579435, 21.084365124034683)
    punkt_politechnika = (52.245051314579435, 21.084365124034683)
    punkt_metro_bemowo = (52.239277502745445, 20.913181966913832)
    punkt_sggw = (52.158511701349056, 21.0477039225247)
    punkt_dworzec_zachodni = (52.218013523486285, 20.96285349533098)
    punkt_siekierki = (52.192605097067535, 21.04882025589122)
    punkty_pogodowe = [punkt_wiatraczna, punkt_politechnika, punkt_metro_bemowo, punkt_sggw, punkt_dworzec_zachodni, punkt_siekierki]
    pogoda = WeatherTracker(punkty_pogodowe)

    with open(f'{DATA_DIR}/out.csv', 'w') as f:
        f.write("czas_str;linia;brygada;nazwa_trasy;lat;lon;metr;znak minuty:sekundy;opoznienie;temp;czy_dzien;opad_deszczu;opad_sniegu;poryw_wiatru\n")
        while True:
            logging.info("Pobieram dane o położeniu...")
            czas_start = time.time()
            lista_polozen = kolektor_danych.zbierz_obecne_polozenie(API_KEY, linie)
            for pojazd in lista_polozen:
                linia = pojazd['linia']
                brygada = pojazd['brygada']
                lat = pojazd['lat']
                lon = pojazd['lon']
                czas_gps = pojazd['czas']
                czas_str = pojazd['czas_str']
                wynik_przetwarzania = tracker.przetworz_pozycje(linia, brygada, lat, lon, czas_gps)
                if isinstance(wynik_przetwarzania, int):
                    if wynik_przetwarzania == 2:
                        #logging.info(f"Pojazd {linia}/{brygada} oczekuje na dalsze pomiary...")
                        continue
                    if wynik_przetwarzania == 1:
                        #logging.warning(f"Problem ze znalezieniem pojazdu {linia}/{brygada}")
                        continue
                
                if isinstance(wynik_przetwarzania, tuple):
                    opoznienie, metr, nazwa_trasy = wynik_przetwarzania
                    znak = "+" if opoznienie >= 0 else "-"
                    abs_opoznienie = abs(int(opoznienie))
                    minuty, sekundy = divmod(abs_opoznienie, 60)

                    pogoda_tu = pogoda.pogoda_dla_punktu(lat, lon)
                    temp = pogoda_tu.temperatura
                    poryw_wiatru = pogoda_tu.poryw_wiatru
                    opad_deszczu = pogoda_tu.opad_deszczu
                    opad_sniegu = pogoda_tu.opad_sniegu
                    czy_dzien = pogoda_tu.czy_dzien

                    logging.info(f"Pojazd {linia}/{brygada} | Trasa: {nazwa_trasy} | Metr: {metr:.2f}m | Status: {znak}{minuty}m {sekundy}s")
                    linia_tekstu = f"{czas_str};{linia};{brygada};{nazwa_trasy};{lat};{lon};{metr:.2f};{znak}{minuty:02d}:{sekundy:02d};{opoznienie:.0f};{temp};{czy_dzien};{opad_deszczu};{opad_sniegu};{poryw_wiatru}\n"
                    f.write(linia_tekstu)

            time.sleep(max(0, 16 - (time.time() - czas_start)))


    logger.info("Finished")

if __name__ == "__main__":
    main()