"""Les services lancés localement ne doivent pas s'exposer sur 0.0.0.0."""

import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

SERVICES = (
    "src/ai_router.py",
    "src/agent_mesh.py",
    "src/orchestrator.py",
    "src/dsh_bridge.py",
    "src/homedock_dashboard.py",
)


class ServiceBindingTest(unittest.TestCase):
    def test_services_bind_loopback_only(self):
        for rel in SERVICES:
            text = (BASE_DIR / rel).read_text(encoding="utf-8", errors="ignore")
            self.assertNotIn('app.run(host="0.0.0.0"', text, rel)
            self.assertNotIn("app.run(host='0.0.0.0'", text, rel)

    def test_web_launcher_uses_the_loopback_env_host(self):
        text = (BASE_DIR / "start_web_server.py").read_text(encoding="utf-8", errors="ignore")
        self.assertIn("WEB_HOST", text)
        self.assertNotIn("app.run(host='0.0.0.0'", text)
        self.assertNotIn('app.run(host="0.0.0.0"', text)

    def test_web_does_not_start_a_second_robot_engine(self):
        text = (BASE_DIR / "src/web_interface.py").read_text(encoding="utf-8", errors="ignore")
        self.assertIn('ESPRIA_WEB_ROBOT_LOOP", "0"', text)

    def test_g0dm0d3_api_binds_loopback_only(self):
        text = (BASE_DIR / "G0DM0D3" / "api" / "server.ts").read_text(
            encoding="utf-8", errors="ignore"
        )
        self.assertNotIn("app.listen(PORT, '0.0.0.0'", text)
        self.assertNotIn('app.listen(PORT, "0.0.0.0"', text)
        self.assertIn("'127.0.0.1'", text)

    def test_g0dm0d3_api_uses_express5_named_wildcards(self):
        base = BASE_DIR / "G0DM0D3" / "api"
        for path in sorted(base.glob("routes/*.ts")) + [base / "server.ts"]:
            text = path.read_text(encoding="utf-8", errors="ignore")
            self.assertNotIn("('/batch/*'", text, str(path))
            self.assertIn("*splat", (base / "routes/research.ts").read_text(
                encoding="utf-8", errors="ignore"
            ))

    def test_cloud_desktop_uses_dedicated_loopback_port(self):
        text = (BASE_DIR / "src/cloud_desktop_agent.py").read_text(encoding="utf-8", errors="ignore")
        self.assertIn('CLOUD_DESKTOP_PORT", "5002"', text)
        self.assertIn('CLOUD_DESKTOP_HOST", "127.0.0.1"', text)
        self.assertNotIn('app.run(host="0.0.0.0"', text)


if __name__ == "__main__":
    unittest.main()
