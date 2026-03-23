import logging
from logger_setup import setup_logger
from dotenv import load_dotenv, find_dotenv
import os
import kolektor_danych

def main():

    logger = logging.getLogger(__name__)
    setup_logger(True)

    logger.info("Start")

    dotenv_path = find_dotenv()
    load_dotenv(dotenv_path)
    API_KEY = os.getenv('API_KEY')

    linie = ['523']
    kolektor_danych.zbierz_obecne_polozenie(API_KEY, linie)
    kolektor_danych.stworz_trase_linii(API_KEY, linie[0])
    kolektor_danych.stworz_rozklad_linii(API_KEY, linie[0])
    kolektor_danych.stworz_baze_polozen_przystankow(API_KEY)

    logger.info("Stop")

if __name__ == "__main__":
    main()