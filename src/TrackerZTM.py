from typing import TypedDict, Optional, Tuple, List
import utils
import json
import logging

logger = logging.getLogger(__name__)

GpsPoint = Tuple[float, float, int] # lat, lon, czas_s
class StanPojazdu(TypedDict):
    stan: str
    historia_gps: List[GpsPoint]
    id_kursu: Optional[int]
    ostatni_przystanek_idx: Optional[str]

BrygadaInfo = dict[str, StanPojazdu] # numer_brygady: StanPojazdu
LinieInfo = dict[str, BrygadaInfo] # numer_linii: BrygadaInfo

def stworz_nowy_stan(lat: float, lon: float, czas: int) -> StanPojazdu:
    return {
        'stan': 'INICJALIZACJA',
        'historia_gps': [(lat, lon, czas)],
        'id_kursu': None,
        'ostatni_przystanek_idx': None
    }

class TrackerZTM:
    pojazdy: LinieInfo
    rozklady: dict[str, dict[str, List]] # linia: {nr_brygady: [lista kursów]}
    przystanki: dict[str, dict] # id_przystanku: {nazwa, lat, lon}

    def __init__(self, linie: list):
        self.pojazdy = dict()
        self.rozklady = dict()
        self.przystanki = dict()
        for linia in linie:
            with open(utils.DATA_DIR / f'rozklad_{linia}.json') as f:
                wczytany_json = json.load(f)
                self.rozklady[wczytany_json['linia']] = wczytany_json['brygady']
                self.pojazdy[linia] = dict()

        with open(utils.DATA_DIR / 'przystanki.json') as f:
                self.przystanki = json.load(f)

        #"523":
        # {
        #   "16": {
        #       "stan": "INICJALIZACJA",
        #       "historia_gps": [(lat, lon, czas), (lat, lon, czas)],
        #       "id_kursu": None,
        #       "ostatni_przystanek_idx": None
        #   },
        #   "17": {
        #       "stan": "INICJALIZACJA",
        #       "historia_gps": [(lat, lon, czas), (lat, lon, czas)],
        #       "id_kursu": None,
        #       "ostatni_przystanek_idx": None
        #   }
        # }

    # o jednym położeniu jednej brygaday
    def przetworz_pozycje(self, linia: str, brygada: str, lat: float, lon: float, czas_gps: int) -> int:
        """
        Główna metoda wywoływana co 15 sekund dla każdego autobusu z API.
        zwraca:
        0 - sukces
        1 - nie ma takiego pojazdu w rozkladzie
        2 - kalibracja, czekaj
        """

        # to nie jest poprawna wartość brygady dla tej linii
        if brygada not in self.rozklady[linia]:
            return 1

        # to jest nieznany jeszcze autobus (niezainicjowany)
        if brygada not in self.pojazdy[linia]:
            self.pojazdy[linia][brygada] = stworz_nowy_stan(lat, lon, czas_gps)
            return 2 # przerywamy i czekamy na kolejne pingi

        # wyciągamy obecny stan autobusu
        pojazd = self.pojazdy[linia][brygada]


        if pojazd["stan"] == "INICJALIZACJA":

            # jesli pojazd nie ruszyl sie znaczoco to czekamy az sie ruszy
            if not utils.czy_pojazd_sie_ruszyl(pojazd['historia_gps'][0][0], pojazd['historia_gps'][0][1], lat, lon):
                return 2
            
            # dodajemy nowy punkt do historii (to jest drugi punkt)
            pojazd["historia_gps"].append((lat, lon, czas_gps))
            
            rozklad_id = self._znajdz_rozklad(czas_gps, linia, brygada, lat, lon)
            if rozklad_id == -1:
                return 1
            
            pojazd['id_kursu'] = rozklad_id
            pojazd['stan'] = 'W_TRASIE'
            pojazd['historia_gps'] = []
            logger.info(f"Linia {linia}, brygada {brygada}: kurs_id: {rozklad_id}")

        elif pojazd["stan"] == "W_TRASIE":
            # - Znajdź przystanek A i B w przypisanym id_kursu
            # - Sprawdź czy autobus minął B (jeśli tak, zaktualizuj ostatni_przystanek_idx)
            # - Policz Proporcję, Obecny Metr, Oczekiwany Czas i Opóźnienie
            # - Zapisz opóźnienie
            
            # TODO: Kod map-matchingu i matematyki
            pass

        elif pojazd["stan"] == "NA_PETLI":
            # - Sprawdź, czy czas_gps zbliża się do czasu startu kolejnego kursu
            pass

    # ---------------------------------------------------------
    # METODY POMOCNICZE (Prywatne)
    # ---------------------------------------------------------


    def _znajdz_rozklad(self, czas_teraz: int, linia: str, brygada: str, lat_sz: float, lon_sz: float) -> int:

        okno_w_przod = utils.czas_na_sekundy('01:00:00')
        okno_w_tyl = utils.czas_na_sekundy('00:10:00')

        kandydaci = []
        for kurs in self.rozklady[linia][brygada]:
            if (czas_teraz >= kurs['czas_startu'] - okno_w_tyl 
            and czas_teraz <= kurs['czas_konca'] + okno_w_przod):
                kandydaci.append(kurs)

        if len(kandydaci) == 0:
            return -1 # BRAK TAKIEGO ROZKŁADU
        elif len(kandydaci) == 1:
            return kandydaci[0]['id_kursu']
        
        # jeśli jest > 1 kurs (zazwyczaj 2)
        przy_petli = None
        for kurs in kandydaci:
            przystanki = kurs['przystanki']
            
            # ten kurs jest z/do zajezdni
            if len(przystanki) < 2:
                continue

            kolejne_id_najblizszych = self._znajdz_trzy_kolejne_najblizsze_przystanki_na_trasie(linia, brygada, kurs['id_kursu'], lat_sz, lon_sz)

            # najblizszy przystanek jest ostatni, najwyzej zostanie na koncu jak do zadnego innego kursu nie bedzie pasowac
            if len(kolejne_id_najblizszych) == 1:
                przy_petli = kurs
                continue

            id_celu = kolejne_id_najblizszych[1]
            lat_celu = self.przystanki[id_celu]['lat']
            lon_celu = self.przystanki[id_celu]['lon']

            pojazd = self.pojazdy[linia][brygada]
            historia = pojazd['historia_gps']

            lat_A, lon_A = historia[0][0], historia[0][1]
            lat_B, lon_B = historia[1][0], historia[1][1]

            odl_A = utils.oblicz_odleglosc(lat_A, lon_A , lat_celu, lon_celu)
            odl_B = utils.oblicz_odleglosc(lat_B, lon_B , lat_celu, lon_celu)

            if odl_A > odl_B:
                return kurs['id_kursu']
            
            # to nie jest kurs, który za 2 przystanki ma zajezdnie
            if len(kolejne_id_najblizszych) == 3:
                id_celu_2 = kolejne_id_najblizszych[2]
                lat_celu_2 = self.przystanki[id_celu_2]['lat']
                lon_celu_2 = self.przystanki[id_celu_2]['lon']

                odl_A_cel2 = utils.oblicz_odleglosc(lat_A, lon_A, lat_celu_2, lon_celu_2)
                odl_B_cel2 = utils.oblicz_odleglosc(lat_B, lon_B, lat_celu_2, lon_celu_2)

                if odl_A_cel2 > odl_B_cel2:
                    return kurs['id_kursu']
        
        # zostal ten jeden kurs co dojezdza do zajezdni
        if przy_petli is not None:
            return przy_petli['id_kursu']
        
        logging.warning(f"Żadna trasa nie pasuje do tego, co robi ten autobus!\nLinia: {linia}, Brygada: {brygada}")
        return -1

    def _znajdz_trzy_kolejne_najblizsze_przystanki_na_trasie(self, linia: str, brygada: str, id_kursu: int, lat_sz: float, lon_sz: float) -> list:
        lista_przystankow_kursu = self.rozklady[linia][brygada][id_kursu]['przystanki']

        najblizszy_przystanek = min(
            lista_przystankow_kursu, 
            key=lambda x: utils.oblicz_odleglosc(
                lat_sz, lon_sz,
                self.przystanki[x['przystanek_id']]['lat'], 
                self.przystanki[x['przystanek_id']]['lon']
            )
        )

        przystanek_1_id = najblizszy_przystanek['przystanek_id']
        id_przystankow = [przystanek_1_id]

        nr_kolejnosci_najblizszego = najblizszy_przystanek['nr_kolejnosci']

        if nr_kolejnosci_najblizszego + 1 < len(lista_przystankow_kursu):
            przystanek_2_id = lista_przystankow_kursu[nr_kolejnosci_najblizszego + 1]['przystanek_id']
            id_przystankow.append(przystanek_2_id)
            if nr_kolejnosci_najblizszego + 2 < len(lista_przystankow_kursu):
                przystanek_3_id = lista_przystankow_kursu[nr_kolejnosci_najblizszego + 2]['przystanek_id']
                id_przystankow.append(przystanek_3_id)

        return id_przystankow