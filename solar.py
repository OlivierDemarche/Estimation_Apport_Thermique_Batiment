import math

import pandas as pd
import pvlib


# -------- CLEAR SKY DATA --------
def get_clear_sky_rad(latitude, longitude, today, elevation):
    date = pd.date_range(today, today, freq='1h', tz='UTC')
    # Créez une instance de la classe Location avec les coordonnées de l'endroit souhaité
    location = pvlib.location.Location(latitude, longitude)
    # Utilisez la fonction get_clearsky pour obtenir les estimations
    clearsky = location.get_clearsky(date, model="ineichen")
    clear_sky_dni = clearsky["dni"].values[0]
    clear_sky_dhi = clearsky["dhi"].values[0]
    clear_sky_ghi = clearsky["ghi"].values[0]
    ghi_verif = math.cos((90 - elevation) * (math.pi / 180)) * clear_sky_dni + clear_sky_dhi
    return clear_sky_dni, clear_sky_dhi, clear_sky_ghi


# -------- CALCULATE ON ORIENTED SURFACE WITH PVLIB --------
def get_irr_vertical_surface(dni, dhi, ghi, azimtuh_facade, solar_azimuth, today, lat, long):
    weather_data = pd.DataFrame(index=[today])
    weather_data['dni'] = dni
    if dni_orientation_condition(facade_azimuth=azimtuh_facade, solar_azimuth=solar_azimuth):
        weather_data['dni'] = dni  # Direct Normal Irradiance (W/m^2)
    else:
        weather_data['dni'] = 0  # Direct Normal Irradiance (W/m^2)
    weather_data['dhi'] = dhi  # Diffuse Horizontal Irradiance (W/m^2)
    weather_data['ghi'] = ghi
    # Calcul de la position solaire pour l'heure spécifique
    solpos = pvlib.solarposition.get_solarposition(time=weather_data.index, latitude=lat, longitude=long)
    # Calcul de l'irradiance sur la paroi sud-est verticale
    effective_irradiance_wall = pvlib.irradiance.get_total_irradiance(surface_tilt=90, surface_azimuth=azimtuh_facade,
                                                                      solar_zenith=solpos['apparent_zenith'],
                                                                      solar_azimuth=solpos['azimuth'],
                                                                      dni=weather_data['dni'],
                                                                      ghi=weather_data['ghi'],
                                                                      dhi=weather_data['dhi'],
                                                                      dni_extra=None,
                                                                      albedo=0.15)
    return effective_irradiance_wall['poa_global'].values[0]


# -------- CALCULATE ON ORIENTED SURFACE WITH TRIGO --------
def irradiance_trigo(dni, dhi, ghi, solar_angle, solar_azimuth, facade_azimuth, angle_condition, rho):
    # Conversion des angles en radians si nécessaire
    elevation_rad = solar_angle * (math.pi / 180)
    solar_azimuth_rad = solar_azimuth * (math.pi / 180)
    facade_azimuth_rad = facade_azimuth * (math.pi / 180)
    if angle_condition < solar_angle < 90 and dni_orientation_condition(facade_azimuth=facade_azimuth,
                                                                        solar_azimuth=solar_azimuth):
        direct_component = dni * math.cos(elevation_rad) * math.cos(solar_azimuth_rad - facade_azimuth_rad)
    else:
        direct_component = 0
    b = dhi * ((1 + math.cos(90 * (math.pi / 180))) / 2) + (
                (dhi * math.sin(elevation_rad)) / 2)  # diffuse isotrope + diffusion vers le bas
    c = ghi * rho * ((1 - math.cos(elevation_rad)) / 2)
    diffuse = b + c
    irr = direct_component + diffuse
    return irr


# --------------------------------------------------------------
# ------------------------ OTHERS FUNCTIONS --------------------
# --------------------------------------------------------------

# -------- CREATE CONDITION FOR DIRECT RADIANCE --------
def dni_orientation_condition(facade_azimuth, solar_azimuth):
    if facade_azimuth < 90:
        condition_inf = 360 - (90 - facade_azimuth)
        condition_sup = facade_azimuth + 90
    elif facade_azimuth > 270:
        condition_inf = facade_azimuth - 90
        condition_sup = 0 + (90 - (360 - facade_azimuth))
    else:
        condition_inf = facade_azimuth - 90
        condition_sup = facade_azimuth + 90
    if condition_inf < solar_azimuth < condition_sup:
        return True
    else:
        return False


# -------- DNI CORRECTION WITH CLOUD COVERAGE --------
def calculate_real_irradiance(dni, cloud_percentage):
    facteur_correction_cloud = math.exp(-3 * cloud_percentage / 100)
    facteur_correction = facteur_correction_cloud
    new_dni = dni * facteur_correction
    return new_dni


# -------- GET SOLAR AZIMUTH AND ELEVATION (TILT) [°] --------
def get_solar_position(today, lat, long, altitude):
    data = pd.DataFrame(index=[today])
    # Calcul de la position solaire
    solar_position = pvlib.solarposition.get_solarposition(data.index, lat, long, altitude, method='nrel_numpy')
    # Récupération de l'azimut et de l'angle d'inclinaison du soleil
    solar_azimuth = solar_position['azimuth'].values[0]
    tilt = solar_position['elevation'].values[0]
    return solar_azimuth, tilt


# -------- MAIN LOGIC --------
def solar_gain_building_side(azimtuh_facade, solar_angle, solar_azimuth, dhi, ghi, corrected_dni, window_surface,
                             facteur_solaire, today, lat, long, angle_condition, rho):
    corr_irr_pvlib = get_irr_vertical_surface(dni=corrected_dni, dhi=dhi, ghi=ghi, solar_azimuth=solar_azimuth,
                                              azimtuh_facade=azimtuh_facade, today=today, lat=lat, long=long)
    corr_irr_trigo = irradiance_trigo(dni=corrected_dni, dhi=dhi, ghi=ghi, solar_angle=solar_angle,
                                      solar_azimuth=solar_azimuth, facade_azimuth=azimtuh_facade,
                                      angle_condition=angle_condition, rho=rho)
    corr_irr_finale_pvlib = facteur_solaire * corr_irr_pvlib
    corr_irr_finale_trigo = facteur_solaire * corr_irr_trigo
    corr_apport_puissance_pvlib = window_surface * corr_irr_finale_pvlib
    corr_apport_puissance_trigo = window_surface * corr_irr_finale_trigo
    return corr_apport_puissance_pvlib, corr_apport_puissance_trigo
