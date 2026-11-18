"""Cálculos geográficos: distancia entre el cliente y la tienda física."""
import math

from django.conf import settings

RADIO_TIERRA_KM = 6371.0088

# Velocidades promedio en ciudad (km/h) para estimar tiempos de llegada.
VELOCIDADES = {"caminando": 4.8, "bicicleta": 14.0, "carro": 22.0}


def haversine_km(lat1, lon1, lat2, lon2):
    """Distancia en línea recta (gran círculo) entre dos coordenadas, en km."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * RADIO_TIERRA_KM * math.asin(math.sqrt(a))


def distancia_a_tienda(latitud, longitud):
    tienda = settings.TIENDA
    return haversine_km(latitud, longitud, tienda["latitud"], tienda["longitud"])


def minutos(distancia_km, medio):
    return max(1, round(distancia_km / VELOCIDADES[medio] * 60))


def describir_cercania(distancia_km):
    """Mensaje amable según qué tan cerca está el cliente."""
    if distancia_km < 0.5:
        return "muy-cerca", "¡Estás a la vuelta de la esquina! Pasa por un chocolate y un abrazo tejido."
    if distancia_km < 3:
        return "cerca", "Estás muy cerca de nuestro taller. ¡Te esperamos!"
    if distancia_km < 15:
        return "media", "Estás en la ciudad: una visita corta y te llevas algo hecho a mano."
    return "lejos", "Estás lejos, pero no te preocupes: enviamos a todo el país."


def resumen_distancia(distancia_km):
    nivel, mensaje = describir_cercania(distancia_km)
    texto = f"{round(distancia_km * 1000)} m" if distancia_km < 1 else f"{distancia_km:.1f} km".replace(".", ",")
    return {
        "distancia_km": round(distancia_km, 3),
        "distancia_texto": texto,
        "nivel": nivel,
        "mensaje": mensaje,
        "minutos": {medio: minutos(distancia_km, medio) for medio in VELOCIDADES},
    }
