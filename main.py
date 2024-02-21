import os
from datetime import datetime as dt

import requests
from geopy.geocoders import Nominatim

from boiler import Boiler
from radiator import Radiateur
from solar import *
import pandas as pd

# -------------------------------------------------------------------------
# --------------------------- PARAMETERS TO STUDY -------------------------
# -------------------------------------------------------------------------
# BOILER ----------------------
PUISSANCE_NOMINALE = 60
PUISSANCE_MIN = 10
T_EXT_BASE = -9
T_EXT_NON_CHAUFFAGE = 19
T_MAX_CHAUDIERE = 60
T_MIN_CHAUDIERE = 24
NOMBRE = 2

# RADIATOR ----------------------
FICHIERS = ["radiateur_bat_principal"]  # Fichiers CSV des radiateurs à utiliser
REGIME_DIM = [(60, 40)]  # Régime de dimensionnement respectifs des radiateurs (entrée, sortie)

# SOLAR ----------------------
BAT_AZIMUTH = [115, 205]  # Azimuth des différentes façades
SURFACE_VITRAGE = [153.5, 25]  # Surface de vitrage en présence sur les façades respectives
FACTEUR_SOLAIRE = 0.37  # Facteur solaire pour double vitrage HR
ANGLE_CONDITION = 10  # Condition d'élévation solaire minimale (dépends de la présence de bâtiment, d'ombrage,...)
ALTITUDE = 66  # Altitude du lieu à étudier
TODAY = dt.now()  # Date
RHO = 0.15  # Albedo du sol en ville

# -------------------------------------------------------------------------
# ------------------------------- CONSTANTS -------------------------------
# -------------------------------------------------------------------------
LAT = float(os.environ["LAT"])  # Latitude du lieu à étudier
LONG = float(os.environ["LONG"])  # Longitude du lieu à étudier
API_KEY_OWM = os.environ["API_KEY_OWM"]


# -------------------------------------------------------------------------
# -------------------------------------------------------------------------
# -------------------------------------------------------------------------
def get_weather_conditions():
    endpoint = "http://api.openweathermap.org/data/2.5/weather"
    params = {
        "lat": LAT,
        "lon": LONG,
        "appid": API_KEY_OWM,
        "units": "metric"}
    try:
        response = requests.get(endpoint, params=params)
        data = response.json()
        if response.status_code == 200:
            nuages = data['clouds']['all']
            temperature = data['main']['temp']
            return nuages, temperature
        else:
            print(response.text)
            return 0, 0
    except Exception as e:
        print(f"Erreur lors de la requête : {str(e)}")
        return 0, 0


# -------------------------------------------------------------------------
def boiler_management(p_nom, p_min, t_ext_b, t_ext_non_ch, t_max_chaud, t_min_chaud, temp, num):
    boiler1 = Boiler(puissance_nom=p_nom,
                     puissance_min=p_min,
                     t_ext_base=t_ext_b,
                     t_ext_non_chauffage=t_ext_non_ch,
                     t_max_chaudiere=t_max_chaud,
                     t_min_chaudiere=t_min_chaud)
    pente_boiler, deplacement_parallele_boiler = boiler1.loi_eau_t_depart_text()
    boiler1.loi_eau_t_ext_puissance()
    boiler1.tracer_graphique()
    t_depart = boiler1.calculer_t_depart(temperature_ext=temp)
    puissance = (boiler1.calculer_puissance(temperature_depart_eau=t_depart)) * num
    return t_depart, puissance, pente_boiler, deplacement_parallele_boiler


# -------------------------------------------------------------------------
def radiator_management(fichier_rad, t_entree_dim, t_sortie_dim, t_entree):
    df_radiateurs = pd.read_csv(f"data/{fichier_rad}.csv", delimiter=";")
    liste_de_radiateur = []
    for index, rows in df_radiateurs.iterrows():
        puissance_nom = int(rows["Puissance [W]"])
        consigne_temp_ambiante = int(rows["Consigne"])
        radiateur = Radiateur(puissance_nominale=puissance_nom,
                              temperature_ambiante=consigne_temp_ambiante,
                              t_entree_dim=t_entree_dim,
                              t_sortie_dim=t_sortie_dim)
        liste_de_radiateur.append(radiateur)
    puissance_tot = 0
    for radiateur in liste_de_radiateur:
        puissance = float(radiateur.calcul_puissance(t_entree=t_entree, t_sortie=((t_entree + radiateur.t_ambiante) / 2)))  # Hypothèse : T sortie = (T entree + T ambiante)/2
        puissance_tot += puissance
    return puissance_tot


# -------------------------------------------------------------------------
def solar_management(cloud):
    azimuth, elevation = get_solar_position(today=TODAY,
                                            lat=LAT,
                                            long=LONG,
                                            altitude=ALTITUDE)
    dni, dhi, ghi = get_clear_sky_rad(latitude=LAT,
                                      longitude=LONG,
                                      today=TODAY,
                                      elevation=elevation)
    cloud_corrected_dni = calculate_real_irradiance(dni=dni,
                                                    cloud_percentage=cloud)

    pv_lib_total = 0
    trigo_total = 0
    for facade, surface in zip(BAT_AZIMUTH, SURFACE_VITRAGE):
        apport_pvlib, apport_trigo = solar_gain_building_side(azimtuh_facade=facade,
                                                              solar_angle=elevation,
                                                              solar_azimuth=azimuth,
                                                              dhi=dhi,
                                                              ghi=ghi,
                                                              corrected_dni=cloud_corrected_dni,
                                                              window_surface=surface,
                                                              facteur_solaire=FACTEUR_SOLAIRE,
                                                              today=TODAY,
                                                              lat=LAT,
                                                              long=LONG,
                                                              rho=RHO,
                                                              angle_condition=ANGLE_CONDITION)
        pv_lib_total += apport_pvlib
        trigo_total += apport_trigo
    result = (pv_lib_total + trigo_total) / 2
    return result, azimuth, elevation, dni, dhi, ghi, cloud_corrected_dni


def get_localisation_name(latitude, longitude):
    geolocator = Nominatim(user_agent="my_geocoder")
    location = geolocator.reverse((latitude, longitude), language='fr')
    address = location.address if location else None
    return address


# -------------------------------------------------------------------------
# -------------------------------------------------------------------------
# -------------------------------------------------------------------------
if __name__ == "__main__":
    localisation = get_localisation_name(LAT, LONG)
    actual_cloud_coverage, actual_temperature = get_weather_conditions()
    temperature_depart_chaudiere, puissance_effective_chaudiere, pente, deplacement = boiler_management(
        p_nom=PUISSANCE_NOMINALE,
        p_min=PUISSANCE_MIN,
        t_ext_b=T_EXT_BASE,
        t_ext_non_ch=T_EXT_NON_CHAUFFAGE,
        t_min_chaud=T_MIN_CHAUDIERE,
        t_max_chaud=T_MAX_CHAUDIERE,
        temp=actual_temperature,
        num=NOMBRE)
    puissance_emise_radiateur = radiator_management(fichier_rad=FICHIERS[0],
                                                    t_entree_dim=REGIME_DIM[0][0],
                                                    t_sortie_dim=REGIME_DIM[0][1],
                                                    t_entree=temperature_depart_chaudiere)

    apports_solaire, solar_azimuth, solar_elevation, clear_sky_dni, clear_sky_dhi, clear_sky_ghi, dni_corrected = solar_management(cloud=actual_cloud_coverage)
    puissance_thermique_totale = puissance_emise_radiateur + apports_solaire
    print("------------------------------------------------------------------------------------------------")
    print("DONNEES :")
    print(f"Localisation : {localisation} \nDate : {TODAY.strftime("%d-%m-%Y")}\nHeure : {TODAY.strftime("%Hh%M")}")
    print(f"La température extérieur est de {actual_temperature} [°C]")
    print(f"La couverture nuageuse est de {actual_cloud_coverage} [%]")
    print(f"Azimut du soleil: {solar_azimuth} [°]")
    print(f"Angle d'inclinaison du soleil: {solar_elevation} [°]")
    print("------------------------------------------------------------------------------------------------")
    print("CHAUDIERE(S) :")
    print(f"Pente de la courbe de chauffe : {pente} [°]")
    print(f"Déplacement parallèle de la courbe de chauffe : {deplacement} [°C] ")
    print(f"Température de départ chaudière : {temperature_depart_chaudiere} [°C] ")
    print(f"Puissance effective de la chaudière : {puissance_effective_chaudiere / NOMBRE} [kW]")
    print(f"Puissance effective totale : {puissance_effective_chaudiere} [kW] pour {NOMBRE} chaudière(s)")
    print("------------------------------------------------------------------------------------------------")
    print("RADIATEUR(S) :")
    print(f"Puissance émise par les radiateurs à {temperature_depart_chaudiere} [°C] : {puissance_emise_radiateur / 1000} [kW] ")
    print("------------------------------------------------------------------------------------------------")
    print("APPORTS SOLAIRES :")
    print(f"L'apport solaire est de : {apports_solaire} [Watts] soit {apports_solaire / 1000} [kW] ")
    print("------------------------------------------------------------------------------------------------")
    print("PUISSANCE THERMIQUE TOTALE :")
    print(f"L'apport thermique est de : {puissance_thermique_totale} [Watts] soit {puissance_thermique_totale / 1000} [kW] ")
