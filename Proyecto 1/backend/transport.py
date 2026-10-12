"""Métodos para resolver problemas balanceados de transporte."""

from collections import deque
from math import isfinite


class TransportValidationError(ValueError):
    """Indica que los datos del modelo de transporte no son válidos."""


METHOD_NAMES = {
    "noroeste": "Esquina Noroeste",
    "costo_minimo": "Costo Mínimo",
    "vogel": "Aproximación de Vogel",
    "optimo": "Óptimo por flujo de costo mínimo",
}


def _number(value, label):
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise TransportValidationError(f"{label} debe ser numérico") from error

    if not isfinite(number):
        raise TransportValidationError(f"{label} debe ser finito")

    return number


def _quantity(value, label):
    number = _number(value, label)

    if number < 0 or not number.is_integer():
        raise TransportValidationError(
            f"{label} debe ser un entero mayor o igual que cero"
        )

    return int(number)


def _validate_and_balance(costs, supply, demand, supplier_names, destination_names):
    if not isinstance(costs, list) or not costs:
        raise TransportValidationError("Debe ingresar una matriz de costos")

    if not isinstance(supply, list) or len(supply) != len(costs):
        raise TransportValidationError("La oferta no coincide con los proveedores")

    if not isinstance(demand, list) or not demand:
        raise TransportValidationError("Debe ingresar la demanda")

    columns = len(demand)

    if len(costs) > 20 or columns > 20:
        raise TransportValidationError("El modelo admite como máximo 20 x 20")

    normalized_costs = []

    for row_index, row in enumerate(costs):
        if not isinstance(row, list) or len(row) != columns:
            raise TransportValidationError("La matriz de costos no es rectangular")

        normalized_row = []

        for column_index, value in enumerate(row):
            cost = _number(
                value,
                f"Costo {row_index + 1},{column_index + 1}"
            )

            if cost < 0:
                raise TransportValidationError("Los costos no pueden ser negativos")

            normalized_row.append(cost)

        normalized_costs.append(normalized_row)

    normalized_supply = [
        _quantity(value, f"Oferta {index + 1}")
        for index, value in enumerate(supply)
    ]
    normalized_demand = [
        _quantity(value, f"Demanda {index + 1}")
        for index, value in enumerate(demand)
    ]

    if sum(normalized_supply) == 0 or sum(normalized_demand) == 0:
        raise TransportValidationError("La oferta y la demanda totales deben ser mayores que cero")

    suppliers = [
        str(name).strip() or f"Proveedor {index + 1}"
        for index, name in enumerate(supplier_names or [])
    ]
    destinations = [
        str(name).strip() or f"Destino {index + 1}"
        for index, name in enumerate(destination_names or [])
    ]

    if len(suppliers) != len(normalized_supply):
        suppliers = [f"Proveedor {index + 1}" for index in range(len(normalized_supply))]

    if len(destinations) != len(normalized_demand):
        destinations = [f"Destino {index + 1}" for index in range(len(normalized_demand))]

    total_supply = sum(normalized_supply)
    total_demand = sum(normalized_demand)
    balance_message = "El problema ya estaba balanceado."

    if total_supply < total_demand:
        difference = total_demand - total_supply
        normalized_costs.append([0.0] * columns)
        normalized_supply.append(difference)
        suppliers.append("Proveedor ficticio")
        balance_message = (
            f"Se agregó un proveedor ficticio con oferta {difference}."
        )

    elif total_supply > total_demand:
        difference = total_supply - total_demand

        for row in normalized_costs:
            row.append(0.0)

        normalized_demand.append(difference)
        destinations.append("Destino ficticio")
        balance_message = (
            f"Se agregó un destino ficticio con demanda {difference}."
        )

    return (
        normalized_costs,
        normalized_supply,
        normalized_demand,
        suppliers,
        destinations,
        balance_message,
    )


def _northwest(supply, demand):
    remaining_supply = supply.copy()
    remaining_demand = demand.copy()
    allocation = [[0] * len(demand) for _ in supply]
    steps = []
    row = 0
    column = 0

    while row < len(supply) and column < len(demand):
        quantity = min(remaining_supply[row], remaining_demand[column])
        allocation[row][column] = quantity

        if quantity:
            steps.append(
                f"Asignar {quantity} en la celda ({row + 1}, {column + 1})."
            )

        remaining_supply[row] -= quantity
        remaining_demand[column] -= quantity

        row_done = remaining_supply[row] == 0
        column_done = remaining_demand[column] == 0

        if row_done:
            row += 1
        if column_done:
            column += 1

    return allocation, steps


def _least_cost(costs, supply, demand):
    remaining_supply = supply.copy()
    remaining_demand = demand.copy()
    allocation = [[0] * len(demand) for _ in supply]
    steps = []

    while sum(remaining_supply) > 0:
        candidates = []

        for row in range(len(supply)):
            if remaining_supply[row] == 0:
                continue

            for column in range(len(demand)):
                if remaining_demand[column] == 0:
                    continue

                possible = min(remaining_supply[row], remaining_demand[column])
                candidates.append((costs[row][column], -possible, row, column))

        if not candidates:
            break

        cost, _, row, column = min(candidates)
        quantity = min(remaining_supply[row], remaining_demand[column])
        allocation[row][column] += quantity
        remaining_supply[row] -= quantity
        remaining_demand[column] -= quantity
        steps.append(
            f"Elegir costo {cost:g} y asignar {quantity} en "
            f"({row + 1}, {column + 1})."
        )

    return allocation, steps


def _vogel(costs, supply, demand):
    remaining_supply = supply.copy()
    remaining_demand = demand.copy()
    allocation = [[0] * len(demand) for _ in supply]
    steps = []

    def penalty(values):
        ordered = sorted(values)
        return ordered[0] if len(ordered) == 1 else ordered[1] - ordered[0]

    while sum(remaining_supply) > 0:
        options = []

        for row in range(len(supply)):
            if remaining_supply[row] == 0:
                continue

            active = [
                costs[row][column]
                for column in range(len(demand))
                if remaining_demand[column] > 0
            ]

            if active:
                options.append((penalty(active), -min(active), "row", row))

        for column in range(len(demand)):
            if remaining_demand[column] == 0:
                continue

            active = [
                costs[row][column]
                for row in range(len(supply))
                if remaining_supply[row] > 0
            ]

            if active:
                options.append((penalty(active), -min(active), "column", column))

        if not options:
            break

        selected_penalty, _, kind, index = max(options)

        if kind == "row":
            cells = [
                (
                    costs[index][column],
                    -min(remaining_supply[index], remaining_demand[column]),
                    index,
                    column,
                )
                for column in range(len(demand))
                if remaining_demand[column] > 0
            ]
        else:
            cells = [
                (
                    costs[row][index],
                    -min(remaining_supply[row], remaining_demand[index]),
                    row,
                    index,
                )
                for row in range(len(supply))
                if remaining_supply[row] > 0
            ]

        cost, _, row, column = min(cells)
        quantity = min(remaining_supply[row], remaining_demand[column])
        allocation[row][column] += quantity
        remaining_supply[row] -= quantity
        remaining_demand[column] -= quantity
        steps.append(
            f"Penalización {selected_penalty:g}: asignar {quantity} al costo "
            f"{cost:g} en ({row + 1}, {column + 1})."
        )

    return allocation, steps


def _optimal_min_cost_flow(costs, supply, demand):
    supplier_count = len(supply)
    destination_count = len(demand)
    source = 0
    first_supplier = 1
    first_destination = first_supplier + supplier_count
    sink = first_destination + destination_count
    graph = [[] for _ in range(sink + 1)]
    tracked_edges = []

    def add_edge(origin, destination, capacity, cost):
        forward = [destination, len(graph[destination]), capacity, cost]
        reverse = [origin, len(graph[origin]), 0, -cost]
        graph[origin].append(forward)
        graph[destination].append(reverse)
        return forward

    for row, quantity in enumerate(supply):
        add_edge(source, first_supplier + row, quantity, 0.0)

    total = sum(supply)

    for row in range(supplier_count):
        for column in range(destination_count):
            edge = add_edge(
                first_supplier + row,
                first_destination + column,
                total,
                costs[row][column],
            )
            tracked_edges.append((row, column, edge, total))

    for column, quantity in enumerate(demand):
        add_edge(first_destination + column, sink, quantity, 0.0)

    flow = 0
    steps = []

    while flow < total:
        distance = [float("inf")] * len(graph)
        previous = [None] * len(graph)
        in_queue = [False] * len(graph)
        distance[source] = 0.0
        queue = deque([source])
        in_queue[source] = True

        while queue:
            node = queue.popleft()
            in_queue[node] = False

            for edge_index, edge in enumerate(graph[node]):
                destination, _, capacity, cost = edge

                if capacity <= 0:
                    continue

                new_distance = distance[node] + cost

                if new_distance + 1e-12 < distance[destination]:
                    distance[destination] = new_distance
                    previous[destination] = (node, edge_index)

                    if not in_queue[destination]:
                        queue.append(destination)
                        in_queue[destination] = True

        if previous[sink] is None:
            raise TransportValidationError("No se encontró una solución factible")

        quantity = total - flow
        node = sink

        while node != source:
            previous_node, edge_index = previous[node]
            quantity = min(quantity, graph[previous_node][edge_index][2])
            node = previous_node

        node = sink

        while node != source:
            previous_node, edge_index = previous[node]
            edge = graph[previous_node][edge_index]
            reverse_index = edge[1]
            edge[2] -= quantity
            graph[node][reverse_index][2] += quantity
            node = previous_node

        flow += quantity
        steps.append(
            f"Enviar {quantity} unidades por una ruta de costo marginal "
            f"{distance[sink]:g}."
        )

    allocation = [[0] * destination_count for _ in range(supplier_count)]

    for row, column, edge, original_capacity in tracked_edges:
        allocation[row][column] = original_capacity - edge[2]

    return allocation, steps


def _format_result(method, costs, allocation, suppliers, destinations, steps,
                   supply, demand, balance_message):
    total_cost = sum(
        allocation[row][column] * costs[row][column]
        for row in range(len(allocation))
        for column in range(len(allocation[row]))
    )

    shipments = []

    for row, supplier in enumerate(suppliers):
        for column, destination in enumerate(destinations):
            quantity = allocation[row][column]

            if quantity:
                shipments.append({
                    "proveedor": supplier,
                    "destino": destination,
                    "cantidad": quantity,
                    "costo_unitario": costs[row][column],
                    "subtotal": round(quantity * costs[row][column], 4),
                })

    return {
        "metodo": method,
        "metodo_nombre": METHOD_NAMES[method],
        "costo_total": round(total_cost, 4),
        "matriz_asignacion": allocation,
        "costos": costs,
        "proveedores": suppliers,
        "destinos": destinations,
        "oferta": supply,
        "demanda": demand,
        "envios": shipments,
        "pasos": steps,
        "balance": balance_message,
        "es_optimo": method == "optimo",
    }


def solve_transport(costs, supply, demand, method="vogel",
                    supplier_names=None, destination_names=None):
    """Valida, balancea y resuelve un modelo de transporte."""

    if method not in METHOD_NAMES:
        raise TransportValidationError("Método de transporte no reconocido")

    (
        normalized_costs,
        normalized_supply,
        normalized_demand,
        suppliers,
        destinations,
        balance_message,
    ) = _validate_and_balance(
        costs,
        supply,
        demand,
        supplier_names,
        destination_names,
    )

    if method == "noroeste":
        allocation, steps = _northwest(normalized_supply, normalized_demand)
    elif method == "costo_minimo":
        allocation, steps = _least_cost(
            normalized_costs,
            normalized_supply,
            normalized_demand,
        )
    elif method == "vogel":
        allocation, steps = _vogel(
            normalized_costs,
            normalized_supply,
            normalized_demand,
        )
    else:
        allocation, steps = _optimal_min_cost_flow(
            normalized_costs,
            normalized_supply,
            normalized_demand,
        )

    return _format_result(
        method,
        normalized_costs,
        allocation,
        suppliers,
        destinations,
        steps,
        normalized_supply,
        normalized_demand,
        balance_message,
    )
