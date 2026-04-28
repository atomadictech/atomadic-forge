// Recognised by forge certify (tests/*.test.js).

import { echo } from "../a1_at_functions/echo.js";

export function testEcho() {
  if (echo("x") !== "ok: hello, x") throw new Error("echo wrong");
}
