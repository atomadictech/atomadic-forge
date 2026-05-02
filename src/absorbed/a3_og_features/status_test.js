// JS test — recognised by forge certify (tests/*.test.js).

import { formatStatus } from "../web/a1_at_functions/format_status.js";

export function testFormatStatus() {
  if (formatStatus("ok", "alive") !== "ok: alive") {
    throw new Error("formatStatus did not produce expected string");
  }
}
