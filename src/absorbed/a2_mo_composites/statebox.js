// Tier a2 — stateful counter. May import from a0 + a1 only (legal here).

import { ECHO_OK } from "../a0_qk_constants/messages.js";

export class StateBox {
  constructor() {
    this.label = ECHO_OK;
    this.events = [];
  }

  push(value) {
    this.events.push(value);
  }
}
