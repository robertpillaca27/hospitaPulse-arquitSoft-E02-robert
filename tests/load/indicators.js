import http from "k6/http";
import { check } from "k6";

const BASE_URL = __ENV.LOAD_TEST_BASE_URL || "http://127.0.0.1:8000";
const USERNAME = __ENV.LOAD_TEST_USERNAME;
const PASSWORD = __ENV.LOAD_TEST_PASSWORD;
const now = new Date();
const YEAR = __ENV.LOAD_TEST_YEAR || String(now.getFullYear());
const MONTH = __ENV.LOAD_TEST_MONTH || String(now.getMonth() + 1);
const INDICATORS_URL = `${BASE_URL}/api/v1/encuestas/indicadores?anio=${YEAR}&mes=${MONTH}`;

export const options = {
  vus: 50,
  duration: "2m",
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<500"],
  },
};

function assertLoopbackTarget() {
  if (!/^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?(\/|$)/.test(BASE_URL)) {
    throw new Error("La prueba de carga solo permite destinos localhost o 127.0.0.1.");
  }
}

export function setup() {
  assertLoopbackTarget();
  if (!USERNAME || !PASSWORD) {
    throw new Error("Define LOAD_TEST_USERNAME y LOAD_TEST_PASSWORD en el entorno.");
  }

  const login = http.post(
    `${BASE_URL}/api/v1/auth/login`,
    JSON.stringify({ username: USERNAME, password: PASSWORD }),
    { headers: { "Content-Type": "application/json" } },
  );
  const sessionCookie = login.cookies.hospitapulse_session?.[0]?.value;
  if (login.status !== 200 || !sessionCookie) {
    throw new Error(`El login para la prueba falló con HTTP ${login.status}.`);
  }
  return { sessionCookie };
}

export default function (data) {
  const response = http.get(INDICATORS_URL, {
    headers: { Cookie: `hospitapulse_session=${data.sessionCookie}` },
    tags: { endpoint: "indicators" },
  });
  check(response, {
    "indicadores responde HTTP 200": (result) => result.status === 200,
    "respuesta de indicadores es JSON": (result) =>
      result.headers["Content-Type"]?.includes("application/json"),
  });
}
