/**
 * Central dashboard action bus — lets Temur (AI) drive the whole UI.
 *
 * The backend maps a natural-language command to a small action dict
 * (aria.detect_action); this runner turns it into the same CustomEvents the
 * on-screen buttons fire. Actions that live inside a specific top-level view
 * (calendar filters, risk panels, dashboard widgets) first switch to that view,
 * then deliver the sub-event on the next tick so the target component is
 * mounted and listening.
 */
export type TemurAction = { type: string; params?: any; [k: string]: any };

const fire = (name: string, detail?: any) =>
  window.dispatchEvent(new CustomEvent(name, { detail }));

/** Switch to a top-level view, then deliver the follow-up event to it. */
const via = (view: "dashboard" | "calendar" | "risk", name?: string, detail?: any) => {
  fire("pn-nav", { view });
  if (name) setTimeout(() => fire(name, detail), 140);
};

export function runDashboardAction(a: TemurAction, titles?: Record<string, string>) {
  if (!a || !a.type) return;
  const p = a.params || {};
  switch (a.type) {
    case "navigate":
      fire("pn-nav", { view: p.view || "dashboard" });
      break;
    case "calendar":
      via("calendar", "pn-cal", p);
      break;
    case "risk":
      via("risk", "pn-risk", p);
      break;
    case "open_kanban":
      via("dashboard", "pn-open-kanban");
      break;
    case "ttm_panel":
      via("dashboard", "pn-ttm-panel", p);
      break;
    case "flow_panel":
      via("dashboard", "pn-flow-panel", p);
      break;
    case "pm_board":
      via("dashboard", "pn-pm-period", p);
      break;
    case "open_ttm":
      fire("pn-open-ttm", p);
      break;
    case "open_dq":
      fire("pn-open-dq");
      break;
    case "open_eq":
      fire("pn-open-eq");
      break;
    case "open_admin":
      fire("pn-open-admin");
      break;
    case "open_analyze":
      fire("pn-open-analyze");
      break;
    case "open_issue":
      fire("pn-issue", { key: p.key });
      break;
    case "drill": {
      // new shape: params carries the /api/issues filters; old shape kept for compat
      const prm = Object.keys(p).length ? p : { scope: a.scope || "epics", state: a.state };
      const title =
        a.label ||
        (a.state && titles ? titles[a.state] : "") ||
        prm.pm || prm.status || prm.value || "";
      fire("pn-drill", { title, params: prm });
      break;
    }
    case "theme":
      fire("pn-theme", p);
      break;
    case "set_lang":
      fire("pn-lang", p);
      break;
    case "celebrations":
      fire("pn-celebrations", p);
      break;
    case "close_popups":
      fire("pn-close-popups");
      break;
    // "temur_mode" is handled locally inside AriaPanel (its own state).
  }
}
