// Temporary verification harness (outside the repo). Drives the built UI with
// a stubbed API through Chrome DevTools Protocol; no real credentials/data.
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const targets = await (await fetch("http://localhost:9222/json/list")).json();
const page = targets.find((t) => t.type === "page");
if (!page) throw new Error("no Chrome page target");
const ws = new WebSocket(page.webSocketDebuggerUrl);
await new Promise((resolve, reject) => {
  ws.onopen = resolve;
  ws.onerror = reject;
});

let nextId = 1;
const pending = new Map();
ws.onmessage = (ev) => {
  const msg = JSON.parse(ev.data);
  if (msg.id && pending.has(msg.id)) {
    const { resolve, reject } = pending.get(msg.id);
    pending.delete(msg.id);
    msg.error ? reject(new Error(JSON.stringify(msg.error))) : resolve(msg.result);
  }
};
const send = (method, params = {}) =>
  new Promise((resolve, reject) => {
    const id = nextId++;
    pending.set(id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params }));
  });
const evaluate = async (expression) => {
  const r = await send("Runtime.evaluate", {
    expression,
    returnByValue: true,
    awaitPromise: true,
  });
  if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
  return r.result.value;
};
const results = [];
const check = (name, ok, evidence) => {
  results.push({ name, ok, evidence });
  console.log(`${ok ? "PASS" : "FAIL"} ${name}: ${evidence}`);
};
const waitFor = async (expression, label, timeout = 3000) => {
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) {
    if (await evaluate(expression)) return true;
    await sleep(50);
  }
  console.log(`TIMEOUT waiting for ${label}`);
  return false;
};

const demoMapping = {
  source_artifact: "LEGACYDB.PARCEL",
  canonical_concept: "Assessment.Valuation[type=LAND+IMP].total",
  target_artifact: "total_assessed",
  confidence: { overall: 0.9, drivers: ["domain-rule"], calibrated: true },
  approved_by: "demo-operator",
  approval_ref: "demo-approval",
  version: "0.1.0",
  evidence_refs: ["handbook:parcel-assessment-rules"],
  golden_plan_digest: "golden:fixture-golden-plan",
  levels: [1, 2, 3, 4, 5, 6, 7].map((n) => ({
    level: n, kind: "stub", statement: `stub level ${n}`,
  })),
};

const stubSource = `
(() => {
  const realFetch = window.fetch.bind(window);
  const demo = ${JSON.stringify(demoMapping)};
  const json = (body, status = 200) => new Response(JSON.stringify(body), {
    status, headers: { "Content-Type": "application/json" },
  });
  window.__approvalScenario = "approved";
  window.fetch = async (input, init) => {
    const url = typeof input === "string" ? input : input.url;
    if (url.includes("/api/v1/health")) return json({ status: "ok" });
    if (url.includes("/api/v1/fixture/demo-mapping")) return json(demo);
    if (url.includes("/api/v1/fixture/demo-steps")) return json([{ op: "copy", args: { from: "a", to: "b" } }]);
    if (url.includes("/api/v1/mapping/digest")) {
      const scenario = window.__approvalScenario;
      if (scenario === "error") return new Response("boom", { status: 500 });
      if (scenario === "slow") await new Promise((r) => setTimeout(r, 700));
      const approved = scenario === "approved" || scenario === "slow";
      return json({
        digest: (approved ? "a" : "b").repeat(64),
        complete: approved,
        approved,
        approval_problems: approved ? [] : ["no approver recorded", "semantic levels missing: [1]"],
      });
    }
    return realFetch(input, init);
  };
})();
`;

await send("Page.enable");
await send("Runtime.enable");
await send("Page.addScriptToEvaluateOnNewDocument", { source: stubSource });
await send("Page.navigate", { url: "http://localhost:4173/" });
await sleep(1200);

const clickByText = (text) => `(() => {
  const b = [...document.querySelectorAll('button')].find(b => b.textContent.includes(${JSON.stringify(text)}));
  if (!b) return 'not-found';
  b.click(); return 'clicked';
})()`;
const buttonState = `(() => {
  const b = [...document.querySelectorAll('button')].find(b =>
    b.textContent.includes('Check approval status') ||
    b.textContent.includes('Re-check approval') ||
    b.textContent.includes('Checking approval'));
  return b ? { label: b.textContent.trim(), disabled: b.disabled, busy: b.getAttribute('aria-busy') } : null;
})()`;

check("app mounted", await evaluate("!!document.querySelector('nav')"), "nav element present");
check("open Mapping tab", (await evaluate(clickByText("Mapping"))) === "clicked", "clicked Mapping tab");
await sleep(150);
let state = await evaluate(buttonState);
check("check button disabled with no mapping", !!state && state.disabled === true, JSON.stringify(state));

check("load demo mapping", (await evaluate(clickByText("Load demo mapping"))) === "clicked", "clicked load demo");
await waitFor("!!document.querySelector('input[placeholder=\"Source artifact\"]')", "mapping form");
state = await evaluate(buttonState);
check("check button enabled with mapping", !!state && state.disabled === false, JSON.stringify(state));

check("approved scenario click", (await evaluate(clickByText("Check approval status"))) === "clicked", "clicked check");
const approved = await waitFor("document.body.innerText.includes('Approved — digest')", "approved status");
check("approved status rendered", approved, await evaluate("document.body.innerText.match(/Approved[^\\n]*/)?.[0] || 'none'"));

await evaluate(`window.__approvalScenario = "rejected"; 'ok'`);
check("edit mapping field", await evaluate(`(() => {
  const i = document.querySelector('input[placeholder="Source artifact"]');
  if (!i) return false;
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
  setter.call(i, 'EDITED.SOURCE');
  i.dispatchEvent(new Event('input', { bubbles: true }));
  return true;
})()`), "dispatched input event on source artifact");
await sleep(150);
state = await evaluate(buttonState);
check("edit resets approval state", !!state && state.label === "Check approval status", JSON.stringify(state));

check("rejected scenario click", (await evaluate(clickByText("Check approval status"))) === "clicked", "clicked check");
const rejected = await waitFor("document.body.innerText.includes('Not approved')", "rejected status");
check("rejected status rendered", rejected, await evaluate("document.body.innerText.match(/Not approved[^\\n]*/)?.[0] || 'none'"));
const problems = await evaluate(`(() => {
  const items = [...document.querySelectorAll('li')].map(li => li.textContent.trim()).filter(t => t.includes('approver') || t.includes('levels'));
  return items;
})()`);
check("approval problems listed", problems.length === 2, JSON.stringify(problems));

await evaluate(`window.__approvalScenario = "error"; 'ok'`);
check("error scenario click", (await evaluate(clickByText("Re-check approval"))) === "clicked", "clicked re-check");
const failed = await waitFor("document.body.innerText.includes('Approval check failed.')", "error status");
check("API failure handled in UI", failed, await evaluate("document.body.innerText.match(/API 500[^\\n]*/)?.[0] || 'none'"));

await evaluate(`window.__approvalScenario = "slow"; 'ok'`);
check("slow scenario click", (await evaluate(clickByText("Re-check approval"))) === "clicked", "clicked re-check");
state = await evaluate(buttonState);
check("button disabled while checking", !!state && state.disabled === true && state.busy === "true" && state.label.includes("Checking"), JSON.stringify(state));
const slowDone = await waitFor("document.body.innerText.includes('Approved — digest')", "slow approved status", 4000);
check("slow check completes", slowDone, await evaluate("document.body.innerText.match(/Approved[^\\n]*/)?.[0] || 'none'"));

check("stale scenario click", (await evaluate(clickByText("Re-check approval"))) === "clicked", "clicked re-check (slow)");
state = await evaluate(buttonState);
check("stale: checking started", !!state && state.label.includes("Checking"), JSON.stringify(state));
await evaluate(`(() => {
  const i = document.querySelector('input[placeholder="Source artifact"]');
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
  setter.call(i, 'EDITED-DURING-CHECK');
  i.dispatchEvent(new Event('input', { bubbles: true }));
  return true;
})()`);
await sleep(1000);
state = await evaluate(buttonState);
const staleApproved = await evaluate("document.body.innerText.includes('Approved — digest')");
check("stale result discarded after edit", !!state && state.label === "Check approval status" && !staleApproved, JSON.stringify(state) + ` approvedText=${staleApproved}`);

const failedCount = results.filter((r) => !r.ok).length;
console.log(`SUMMARY total=${results.length} passed=${results.length - failedCount} failed=${failedCount}`);
ws.close();
process.exit(failedCount === 0 ? 0 : 1);
