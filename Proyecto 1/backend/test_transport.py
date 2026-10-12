import random
import unittest

from transport import TransportValidationError, solve_transport


class TransportTest(unittest.TestCase):
    def setUp(self):
        self.costos = [[4, 8, 8], [2, 5, 7], [6, 4, 3]]
        self.oferta = [80, 100, 120]
        self.demanda = [90, 110, 100]

    def test_todos_los_metodos_respetan_oferta_y_demanda(self):
        for metodo in ("noroeste", "costo_minimo", "vogel", "optimo"):
            resultado = solve_transport(
                self.costos,
                self.oferta,
                self.demanda,
                metodo,
            )
            asignacion = resultado["matriz_asignacion"]

            self.assertEqual([sum(fila) for fila in asignacion], self.oferta)
            self.assertEqual(
                [
                    sum(asignacion[fila][columna] for fila in range(3))
                    for columna in range(3)
                ],
                self.demanda,
            )

    def test_optimo_coincide_con_busqueda_exhaustiva_en_casos_2x2(self):
        random.seed(7)

        for _ in range(100):
            costos = [
                [random.randint(0, 9), random.randint(0, 9)],
                [random.randint(0, 9), random.randint(0, 9)],
            ]
            oferta = [random.randint(1, 9), 0]
            oferta[1] = 10 - oferta[0]
            demanda = [random.randint(1, 9), 0]
            demanda[1] = 10 - demanda[0]
            minimo = max(0, demanda[0] - oferta[1])
            maximo = min(oferta[0], demanda[0])
            costo_exhaustivo = min(
                cantidad * costos[0][0]
                + (oferta[0] - cantidad) * costos[0][1]
                + (demanda[0] - cantidad) * costos[1][0]
                + (oferta[1] - demanda[0] + cantidad) * costos[1][1]
                for cantidad in range(minimo, maximo + 1)
            )

            resultado = solve_transport(costos, oferta, demanda, "optimo")
            self.assertEqual(resultado["costo_total"], costo_exhaustivo)

    def test_balancea_con_destino_ficticio(self):
        resultado = solve_transport([[1, 2], [3, 4]], [10, 5], [7, 3], "optimo")
        self.assertIn("destino ficticio", resultado["balance"].lower())
        self.assertEqual(sum(resultado["oferta"]), sum(resultado["demanda"]))

    def test_rechaza_costos_negativos(self):
        with self.assertRaises(TransportValidationError):
            solve_transport([[-1]], [1], [1], "vogel")


if __name__ == "__main__":
    unittest.main()
