import unittest

from linear_optimizer import LinearOptimizationError, optimize_sensor_resources


class LinearOptimizerTest(unittest.TestCase):
    def test_respects_budget_and_bounds(self):
        result = optimize_sensor_resources(
            {
                "temperatura": 31,
                "humedad": 75,
                "gas": 180,
                "distancia": 30,
                "luz": 620,
            },
            100,
        )

        self.assertLessEqual(result["energia_usada"], 100)
        self.assertLessEqual(
            sum(activity["energia_usada"] for activity in result["actividades"]),
            100,
        )

        for activity in result["actividades"]:
            self.assertGreaterEqual(activity["asignacion"], 0)
            self.assertLessEqual(activity["asignacion"], activity["demanda"])

    def test_gas_emergency_prioritizes_ventilation(self):
        result = optimize_sensor_resources(
            {
                "temperatura": 25,
                "humedad": 50,
                "gas": 500,
                "distancia": 30,
                "luz": 800,
            },
            90,
        )
        allocations = {
            activity["clave"]: activity["asignacion"]
            for activity in result["actividades"]
        }

        self.assertEqual(allocations["ventilacion"], 50)
        self.assertEqual(allocations["luz_zona1"], 0)
        self.assertTrue(result["advertencias"])

    def test_zero_demand_does_not_consume_energy(self):
        result = optimize_sensor_resources(
            {
                "temperatura": 20,
                "humedad": 50,
                "gas": 0,
                "distancia": 200,
                "luz": 100,
            },
            120,
        )
        self.assertEqual(result["energia_usada"], 0)
        self.assertEqual(result["demanda_no_cubierta"], 0)

    def test_rejects_invalid_budget(self):
        with self.assertRaises(LinearOptimizationError):
            optimize_sensor_resources({}, 400)


if __name__ == "__main__":
    unittest.main()
