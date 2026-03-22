from django.test import Client, TestCase


class HealthEndpointsTestCase(TestCase):
    def setUp(self):
        self.client = Client()

    def test_health_live_publico(self):
        r = self.client.get("/api/v1/health/live/")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertTrue(body.get("ok"))
        self.assertTrue(body.get("data", {}).get("live"))

    def test_health_ready_base_datos(self):
        r = self.client.get("/api/v1/health/ready/")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertTrue(body.get("ok"))
        self.assertEqual(body.get("data", {}).get("database"), "ok")
