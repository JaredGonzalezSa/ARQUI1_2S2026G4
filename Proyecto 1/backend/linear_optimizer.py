"""Programacion lineal aplicada a las lecturas del aula inteligente.

El modelo es una mochila fraccionaria: maximiza el beneficio operativo de
ventilacion e iluminacion sin exceder un presupuesto energetico normalizado.
Por su estructura, ordenar por beneficio/costo produce la solucion optima.
"""

from math import isfinite


class LinearOptimizationError(ValueError):
    """Indica que los datos del modelo lineal no son validos."""


def _number(value, default=0.0):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default

    return number if isfinite(number) else default


def _clamp(value, minimum=0.0, maximum=100.0):
    return max(minimum, min(maximum, value))


def _sensor_snapshot(readings):
    readings = readings or {}
    return {
        "temperatura": _number(readings.get("temperatura"), 25.0),
        "humedad": _number(readings.get("humedad"), 50.0),
        "gas": _number(readings.get("gas"), 0.0),
        "distancia": _number(readings.get("distancia"), 100.0),
        "luz": _number(readings.get("luz"), 0.0),
    }


def _build_activities(sensors):
    temperature_need = _clamp((sensors["temperatura"] - 22.0) * 12.5)
    humidity_need = _clamp((sensors["humedad"] - 60.0) * 5.0)
    gas_need = _clamp((sensors["gas"] / 300.0) * 100.0)
    ventilation_need = max(temperature_need, humidity_need, gas_need)

    # En este prototipo un valor alto del LDR representa menor iluminacion.
    light_need = _clamp((sensors["luz"] - 200.0) / 6.0)
    presence = sensors["distancia"] <= 100.0

    ventilation_priority = (
        4.0
        + temperature_need / 25.0
        + humidity_need / 40.0
        + gas_need / 4.0
    )

    zone_priorities = [
        4.5 if presence else 2.8,
        3.4,
        2.8,
    ]

    return [
        {
            "clave": "ventilacion",
            "nombre": "Ventilacion y calidad del aire",
            "demanda": ventilation_need,
            "costo_unitario": 1.8,
            "beneficio_unitario": ventilation_priority,
            "origen": "temperatura, humedad y gas",
        },
        *[
            {
                "clave": f"luz_zona{index + 1}",
                "nombre": f"Iluminacion zona {index + 1}",
                "demanda": light_need,
                "costo_unitario": 0.45,
                "beneficio_unitario": priority,
                "origen": "luz y proximidad" if index == 0 else "nivel de luz",
            }
            for index, priority in enumerate(zone_priorities)
        ],
    ]


def optimize_sensor_resources(readings, energy_budget=120.0):
    """Resuelve el modelo lineal y devuelve una recomendacion auditable."""
    budget = _number(energy_budget, -1.0)

    if budget < 0 or budget > 315:
        raise LinearOptimizationError(
            "El presupuesto energetico debe estar entre 0 y 315 unidades"
        )

    sensors = _sensor_snapshot(readings)
    activities = _build_activities(sensors)
    remaining_budget = budget
    objective_value = 0.0

    for activity in activities:
        activity["indice_prioridad"] = (
            activity["beneficio_unitario"] / activity["costo_unitario"]
        )
        activity["asignacion"] = 0.0

    # Solucion exacta de la mochila fraccionaria: primero el mayor beneficio
    # marginal por unidad de energia.
    for activity in sorted(
        activities,
        key=lambda item: (-item["indice_prioridad"], item["clave"]),
    ):
        maximum_affordable = remaining_budget / activity["costo_unitario"]
        allocation = min(activity["demanda"], maximum_affordable)
        activity["asignacion"] = allocation
        used = allocation * activity["costo_unitario"]
        remaining_budget -= used
        objective_value += allocation * activity["beneficio_unitario"]

    total_used = budget - remaining_budget
    unmet = sum(
        max(0.0, activity["demanda"] - activity["asignacion"])
        for activity in activities
    )

    for activity in activities:
        activity["demanda"] = round(activity["demanda"], 2)
        # Se conservan cuatro decimales para que el detalle de energia no
        # aparente exceder el presupuesto por efecto del redondeo visual.
        activity["asignacion"] = round(activity["asignacion"], 4)
        activity["energia_usada"] = round(
            activity["asignacion"] * activity["costo_unitario"], 2
        )
        activity["beneficio_unitario"] = round(
            activity["beneficio_unitario"], 4
        )
        activity["indice_prioridad"] = round(
            activity["indice_prioridad"], 4
        )
        activity["cobertura"] = (
            100.0
            if activity["demanda"] == 0
            else round(activity["asignacion"] / activity["demanda"] * 100.0, 2)
        )

    warnings = []

    if sensors["gas"] > 300:
        warnings.append(
            "Gas sobre el umbral de seguridad: el protocolo de emergencia "
            "tiene prioridad sobre cualquier recomendacion economica."
        )

    if unmet > 0.01:
        warnings.append(
            "El presupuesto no cubre toda la demanda estimada; aumentelo o "
            "revise las prioridades operativas."
        )

    return {
        "modelo": "Programacion lineal de asignacion energetica",
        "es_optimo": True,
        "sensores": {key: round(value, 2) for key, value in sensors.items()},
        "presupuesto": round(budget, 2),
        "energia_usada": round(total_used, 2),
        "energia_disponible": round(remaining_budget, 2),
        "beneficio_total": round(objective_value, 2),
        "demanda_no_cubierta": round(unmet, 2),
        "actividades": activities,
        "advertencias": warnings,
        "formulacion": {
            "objetivo": "Max Z = suma(beneficio_i * x_i)",
            "presupuesto": "suma(costo_energia_i * x_i) <= presupuesto",
            "limites": "0 <= x_i <= demanda_i calculada por sensores",
            "variables": [activity["clave"] for activity in activities],
        },
    }
