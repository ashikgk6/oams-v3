const API = "";

function token() {
  return localStorage.getItem("oams_token");
}

function setAuth(data) {
  localStorage.setItem("oams_token", data.access_token);
  localStorage.setItem("oams_role", data.role);
  localStorage.setItem("oams_name", data.name);
  localStorage.setItem("oams_user_id", String(data.user_id));
}

function clearAuth() {
  ["oams_token", "oams_role", "oams_name", "oams_user_id"].forEach((k) =>
    localStorage.removeItem(k)
  );
}

function authHeaders(json = true) {
  const h = {};
  if (json) h["Content-Type"] = "application/json";
  const t = token();
  if (t) h.Authorization = `Bearer ${t}`;
  return h;
}

async function api(path, opts = {}) {
  const res = await fetch(API + path, {
    ...opts,
    headers: { ...authHeaders(!(opts.body instanceof FormData)), ...(opts.headers || {}) },
  });
  if (res.status === 401) {
    clearAuth();
    if (!location.pathname.startsWith("/kiosk") && !location.pathname.startsWith("/display")) {
      location.href = "/login";
    }
    throw new Error("Unauthorized");
  }
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) {
    const data = await res.json();
    if (!res.ok) {
      const d = data.detail;
      const msg = Array.isArray(d)
        ? d.map((x) => x.msg || JSON.stringify(x)).join("; ")
        : d || JSON.stringify(data);
      throw new Error(msg);
    }
    return data;
  }
  if (!res.ok) throw new Error(await res.text());
  return res;
}

function fmtDetail(err) {
  if (typeof err === "string") return err;
  if (err && err.message) return err.message;
  return "Request failed";
}

function badge(status) {
  return `<span class="badge ${status}">${status.replace("_", " ")}</span>`;
}

function route() {
  const path = location.pathname;
  if (!token() && !["/login", "/kiosk", "/kiosk/pair"].some((p) => path === p || path.startsWith("/display"))) {
    if (path !== "/login") location.href = "/login";
  }
  const app = document.getElementById("app");
  if (path === "/login" || path === "/") {
    if (token() && path === "/") {
      location.href = "/dashboard";
      return;
    }
    if (path === "/login") return renderLogin(app);
  }
  if (path === "/dashboard") return renderDashboard(app);
  if (path === "/punch") return renderPunch(app);
  if (path === "/leave") return renderLeave(app);
  if (path === "/approvals") return renderApprovals(app);
  if (path === "/admin") return renderAdmin(app);
  if (path === "/kiosk") return renderKiosk(app);
  if (path === "/kiosk/pair") return renderKioskPair(app);
  renderLogin(app);
}

function shell(content, active) {
  const role = localStorage.getItem("oams_role") || "";
  const name = localStorage.getItem("oams_name") || "";
  const links = [
    ["/dashboard", "Today", true],
    ["/punch", "Punch", true],
    ["/leave", "Leave", true],
    ["/approvals", "Approvals", role === "admin" || role === "manager"],
    ["/admin", "Admin", role === "admin"],
  ];
  return `
  <div class="shell">
    <div class="topbar">
      <div class="brand">OAMS</div>
      <nav class="nav">
        ${links
          .filter(([, , show]) => show)
          .map(
            ([href, label]) =>
              `<a href="${href}" class="${active === href ? "active" : ""}">${label}</a>`
          )
          .join("")}
        <span class="muted">${name}</span>
        <button class="secondary" type="button" id="logoutBtn">Logout</button>
      </nav>
    </div>
    ${content}
  </div>`;
}

function bindLogout() {
  const btn = document.getElementById("logoutBtn");
  if (btn)
    btn.onclick = () => {
      clearAuth();
      location.href = "/login";
    };
}

function renderLogin(app) {
  app.innerHTML = `
  <div class="login-wrap">
    <div class="card login-card">
      <h1>OAMS</h1>
      <p class="muted">In-office attendance for your Indian office</p>
      <div class="field"><label>Email</label><input id="email" type="email" value="admin@office.local" /></div>
      <div class="field"><label>Password</label><input id="password" type="password" value="admin123" /></div>
      <p class="error hidden" id="err"></p>
      <button id="loginBtn" style="width:100%">Sign in</button>
      <p class="muted" style="margin-top:1rem;font-size:0.85rem">
        Demo: admin@office.local / admin123 · manager@office.local / manager123 · employee@office.local / employee123
      </p>
    </div>
  </div>`;
  document.getElementById("loginBtn").onclick = async () => {
    const err = document.getElementById("err");
    err.classList.add("hidden");
    try {
      const data = await api("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({
          email: document.getElementById("email").value,
          password: document.getElementById("password").value,
        }),
      });
      setAuth(data);
      location.href = "/dashboard";
    } catch (e) {
      err.textContent = fmtDetail(e);
      err.classList.remove("hidden");
    }
  };
}

async function renderDashboard(app) {
  app.innerHTML = shell(`<div class="card"><p class="muted">Loading…</p></div>`, "/dashboard");
  bindLogout();
  try {
    const me = await api("/api/auth/me");
    const mine = await api("/api/attendance/me?days=14");
    let todayBlock = "";
    const role = me.role;
    if (role === "admin" || role === "manager") {
      const today = await api("/api/attendance/today");
      const counts = today.members.reduce((a, m) => {
        a[m.status] = (a[m.status] || 0) + 1;
        return a;
      }, {});
      todayBlock = `
        <div class="grid stats">
          <div class="stat"><div class="n">${counts.present || 0}</div><div class="l">Present</div></div>
          <div class="stat"><div class="n">${counts.late || 0}</div><div class="l">Late</div></div>
          <div class="stat"><div class="n">${counts.absent || 0}</div><div class="l">Absent</div></div>
          <div class="stat"><div class="n">${counts.on_leave || 0}</div><div class="l">On leave</div></div>
        </div>
        <div class="card">
          <h3>Team today (${today.date})</h3>
          <table><thead><tr><th>Name</th><th>Team</th><th>Status</th><th>In</th><th>Out</th></tr></thead>
          <tbody>
          ${today.members
            .map(
              (m) => `<tr>
              <td>${m.name}</td><td>${m.team || "—"}</td>
              <td>${badge(m.status)}</td>
              <td>${m.first_in ? new Date(m.first_in).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" }) : "—"}</td>
              <td>${m.last_out ? new Date(m.last_out).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" }) : "—"}</td>
            </tr>`
            )
            .join("")}
          </tbody></table>
        </div>`;
    }
    app.innerHTML = shell(
      `
      <p class="muted">Signed in as ${me.name} · ${me.role}</p>
      ${todayBlock}
      <div class="card">
        <h3>My last 14 days</h3>
        <table><thead><tr><th>Date</th><th>Status</th><th>In</th><th>Out</th><th>Minutes</th></tr></thead>
        <tbody>
        ${mine
          .map(
            (d) => `<tr>
            <td>${d.date}</td><td>${badge(d.status)}</td>
            <td>${d.first_in ? new Date(d.first_in).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" }) : "—"}</td>
            <td>${d.last_out ? new Date(d.last_out).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" }) : "—"}</td>
            <td>${d.work_minutes ?? "—"}</td>
          </tr>`
          )
          .join("")}
        </tbody></table>
      </div>`,
      "/dashboard"
    );
    bindLogout();
  } catch (e) {
    app.innerHTML = shell(`<div class="card error">${fmtDetail(e)}</div>`, "/dashboard");
    bindLogout();
  }
}

let html5QrCode = null;

async function renderPunch(app) {
  app.innerHTML = shell(
    `
    <div class="card">
      <h2>Scan door QR</h2>
      <p class="muted">Point your camera at the rotating kiosk QR to punch IN or OUT.</p>
      <div id="reader"></div>
      <div id="punchMsg" class="punch-result"></div>
      <div class="row" style="justify-content:center;margin-top:1rem">
        <button type="button" class="secondary" id="stopScan">Stop camera</button>
      </div>
    </div>`,
    "/punch"
  );
  bindLogout();
  const msg = document.getElementById("punchMsg");
  let busy = false;

  async function onScan(decoded) {
    if (busy) return;
    busy = true;
    msg.textContent = "QR scanned. Checking your location…";
    try {
      if (!navigator.geolocation) {
        throw new Error("This browser does not support location verification.");
      }
      const position = await new Promise((resolve, reject) => {
        navigator.geolocation.getCurrentPosition(resolve, reject, {
          enableHighAccuracy: true,
          timeout: 15000,
          maximumAge: 0,
        });
      }).catch((err) => {
        if (err && typeof err.code === "number") {
          const messages = {
            1: "Location permission was denied. Allow location access and scan again.",
            2: "Your location is unavailable. Move to an area with better GPS reception and try again.",
            3: "Location request timed out. Please try again.",
          };
          throw new Error(messages[err.code] || "Could not verify your location.");
        }
        throw err;
      });
      msg.textContent = "Location received. Verifying QR and office distance…";
      const data = await api("/api/punches", {
        method: "POST",
        body: JSON.stringify({
          qr_token: decoded,
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          accuracy_meters: position.coords.accuracy,
        }),
      });
      msg.innerHTML = `<div class="success"><strong>${data.direction}</strong> · ${new Date(data.ts).toLocaleTimeString("en-IN")}<br/>${data.message}</div>`;
      if (navigator.vibrate) navigator.vibrate(80);
    } catch (e) {
      const message = e && typeof e.message === "string" ? e.message : fmtDetail(e);
      msg.textContent = message;
      msg.className = "punch-result error";
    } finally {
      setTimeout(() => {
        busy = false;
      }, 2000);
    }
  }

  if (window.Html5Qrcode) {
    html5QrCode = new Html5Qrcode("reader");
    Html5Qrcode.getCameras()
      .then((cameras) => {
        const cam = cameras.find((c) => /back|rear|environment/i.test(c.label)) || cameras[0];
        if (!cam) {
          msg.textContent = "No camera found";
          return;
        }
        html5QrCode.start(
          cam.id,
          { fps: 8, qrbox: { width: 250, height: 250 } },
          onScan,
          () => {}
        );
      })
      .catch((e) => {
        msg.textContent = "Camera error: " + e;
      });
  } else {
    msg.textContent = "QR library failed to load";
  }

  document.getElementById("stopScan").onclick = async () => {
    if (html5QrCode) {
      try {
        await html5QrCode.stop();
      } catch (_) {}
    }
  };
}

async function renderLeave(app) {
  app.innerHTML = shell(`<div class="card">Loading…</div>`, "/leave");
  bindLogout();
  const mine = await api("/api/leave/mine");
  app.innerHTML = shell(
    `
    <div class="card">
      <h2>Request leave</h2>
      <div class="field"><label>Type</label>
        <select id="leaveType"><option>CL</option><option>SL</option><option>EL</option><option>OTHER</option></select>
      </div>
      <div class="row">
        <div class="field" style="flex:1"><label>Start</label><input type="date" id="start" /></div>
        <div class="field" style="flex:1"><label>End</label><input type="date" id="end" /></div>
      </div>
      <div class="field"><label>Reason</label><textarea id="reason" rows="2"></textarea></div>
      <button id="submitLeave">Submit</button>
      <p id="leaveMsg" class="muted"></p>
    </div>
    <div class="card">
      <h3>My requests</h3>
      <table><thead><tr><th>Type</th><th>Dates</th><th>Status</th></tr></thead>
      <tbody>
      ${mine
        .map(
          (l) =>
            `<tr><td>${l.leave_type}</td><td>${l.start_date} → ${l.end_date}</td><td>${badge(l.status)}</td></tr>`
        )
        .join("")}
      </tbody></table>
    </div>
    <div class="card">
      <h3>Punch correction</h3>
      <div class="field"><label>Date</label><input type="date" id="cDate" /></div>
      <div class="row">
        <div class="field" style="flex:1"><label>Requested IN (ISO local)</label><input type="datetime-local" id="cIn" /></div>
        <div class="field" style="flex:1"><label>Requested OUT</label><input type="datetime-local" id="cOut" /></div>
      </div>
      <div class="field"><label>Reason</label><input id="cReason" /></div>
      <button id="submitCorr">Request correction</button>
      <p id="corrMsg" class="muted"></p>
    </div>`,
    "/leave"
  );
  bindLogout();
  document.getElementById("submitLeave").onclick = async () => {
    try {
      await api("/api/leave", {
        method: "POST",
        body: JSON.stringify({
          leave_type: document.getElementById("leaveType").value,
          start_date: document.getElementById("start").value,
          end_date: document.getElementById("end").value,
          reason: document.getElementById("reason").value,
        }),
      });
      location.reload();
    } catch (e) {
      document.getElementById("leaveMsg").textContent = fmtDetail(e);
    }
  };
  document.getElementById("submitCorr").onclick = async () => {
    const toIso = (v) => (v ? new Date(v).toISOString() : null);
    try {
      await api("/api/corrections", {
        method: "POST",
        body: JSON.stringify({
          date: document.getElementById("cDate").value,
          requested_in: toIso(document.getElementById("cIn").value),
          requested_out: toIso(document.getElementById("cOut").value),
          reason: document.getElementById("cReason").value || "Forgot punch",
        }),
      });
      document.getElementById("corrMsg").textContent = "Submitted";
    } catch (e) {
      document.getElementById("corrMsg").textContent = fmtDetail(e);
    }
  };
}

async function renderApprovals(app) {
  app.innerHTML = shell(`<div class="card">Loading…</div>`, "/approvals");
  bindLogout();
  const [leaves, corrs] = await Promise.all([
    api("/api/leave/pending"),
    api("/api/corrections/pending"),
  ]);
  app.innerHTML = shell(
    `
    <div class="card">
      <h2>Pending leave</h2>
      ${
        leaves.length === 0
          ? "<p class='muted'>None</p>"
          : `<table><thead><tr><th>Employee</th><th>Type</th><th>Dates</th><th></th></tr></thead><tbody>
        ${leaves
          .map(
            (l) => `<tr>
            <td>${l.user_name}</td><td>${l.leave_type}</td><td>${l.start_date} → ${l.end_date}</td>
            <td class="row">
              <button data-leave="${l.id}" data-ok="1">Approve</button>
              <button class="danger" data-leave="${l.id}" data-ok="0">Reject</button>
            </td></tr>`
          )
          .join("")}
        </tbody></table>`
      }
    </div>
    <div class="card">
      <h2>Pending corrections</h2>
      ${
        corrs.length === 0
          ? "<p class='muted'>None</p>"
          : `<table><thead><tr><th>Employee</th><th>Date</th><th>Reason</th><th></th></tr></thead><tbody>
        ${corrs
          .map(
            (c) => `<tr>
            <td>${c.user_name}</td><td>${c.date}</td><td>${c.reason}</td>
            <td class="row">
              <button data-corr="${c.id}" data-ok="1">Approve</button>
              <button class="danger" data-corr="${c.id}" data-ok="0">Reject</button>
            </td></tr>`
          )
          .join("")}
        </tbody></table>`
      }
    </div>`,
    "/approvals"
  );
  bindLogout();
  app.querySelectorAll("[data-leave]").forEach((btn) => {
    btn.onclick = async () => {
      await api(`/api/leave/${btn.dataset.leave}/decide`, {
        method: "POST",
        body: JSON.stringify({ approve: btn.dataset.ok === "1" }),
      });
      renderApprovals(app);
    };
  });
  app.querySelectorAll("[data-corr]").forEach((btn) => {
    btn.onclick = async () => {
      await api(`/api/corrections/${btn.dataset.corr}/decide`, {
        method: "POST",
        body: JSON.stringify({ approve: btn.dataset.ok === "1" }),
      });
      renderApprovals(app);
    };
  });
}

async function renderAdmin(app) {
  app.innerHTML = shell(`<div class="card">Loading…</div>`, "/admin");
  bindLogout();
  const [settings, kiosks, tokens, holidays, teams] = await Promise.all([
    api("/api/admin/settings"),
    api("/api/kiosks"),
    api("/api/display-tokens"),
    api("/api/admin/holidays"),
    api("/api/teams"),
  ]);
  const now = new Date();
  app.innerHTML = shell(
    `
    <div class="card">
      <h2>Office settings (IST)</h2>
      <div class="field"><label>Office name</label><input id="officeName" value="${settings.office_name}" /></div>
      <div class="row">
        <div class="field" style="flex:1"><label>Shift start</label><input id="shiftStart" type="time" value="${settings.shift_start.slice(0, 5)}" /></div>
        <div class="field" style="flex:1"><label>Shift end</label><input id="shiftEnd" type="time" value="${settings.shift_end.slice(0, 5)}" /></div>
        <div class="field" style="flex:1"><label>Grace (min)</label><input id="grace" type="number" value="${settings.grace_minutes}" /></div>
      </div>
      <button id="saveSettings">Save settings</button>
      <p id="setMsg" class="muted"></p>
    </div>
    <div class="card">
      <h2>Import employees (CSV)</h2>
      <p class="muted">Columns: name,email,role,team,password</p>
      <input type="file" id="csvFile" accept=".csv" />
      <button id="importCsv" style="margin-top:0.75rem">Import</button>
      <pre id="importOut" class="muted"></pre>
    </div>
    <div class="card">
      <h2>Door kiosks</h2>
      <div class="row">
        <input id="kioskName" placeholder="Lobby tablet" style="max-width:240px" />
        <button id="createKiosk">Create kiosk</button>
      </div>
      <table style="margin-top:1rem"><thead><tr><th>Name</th><th>Pair code</th><th>Paired</th></tr></thead>
      <tbody>
      ${kiosks
        .map(
          (k) =>
            `<tr><td>${k.name}</td><td><code>${k.pair_code || "—"}</code></td><td>${k.paired_at ? "Yes" : "No"}</td></tr>`
        )
        .join("")}
      </tbody></table>
      <p class="muted">On the tablet open <a href="/kiosk/pair">/kiosk/pair</a> and enter the pair code.</p>
    </div>
    <div class="card">
      <h2>TV display tokens</h2>
      <div class="row">
        <input id="tvLabel" value="Reception TV" style="max-width:240px" />
        <button id="createTv">Create display URL</button>
      </div>
      <p id="tvOut" class="success"></p>
      <table style="margin-top:1rem"><thead><tr><th>Label</th><th>Prefix</th><th>Revoked</th></tr></thead>
      <tbody>
      ${tokens
        .map(
          (t) =>
            `<tr><td>${t.label}</td><td>${t.token_prefix}…</td><td>${t.revoked_at ? "Yes" : "No"}</td></tr>`
        )
        .join("")}
      </tbody></table>
    </div>
    <div class="card">
      <h2>Holidays</h2>
      <div class="row">
        <input type="date" id="hDate" />
        <input id="hName" placeholder="Name" />
        <button id="addHoliday">Add</button>
      </div>
      <ul>${holidays.map((h) => `<li>${h.date} — ${h.name}</li>`).join("")}</ul>
    </div>
    <div class="card">
      <h2>Monthly CSV</h2>
      <div class="row">
        <input type="number" id="y" value="${now.getFullYear()}" style="max-width:100px" />
        <input type="number" id="m" value="${now.getMonth() + 1}" min="1" max="12" style="max-width:80px" />
        <button id="dlCsv">Download</button>
      </div>
      <p class="muted">Teams: ${teams.map((t) => t.name).join(", ")}</p>
    </div>`,
    "/admin"
  );
  bindLogout();

  document.getElementById("saveSettings").onclick = async () => {
    try {
      await api("/api/admin/settings", {
        method: "PATCH",
        body: JSON.stringify({
          office_name: document.getElementById("officeName").value,
          shift_start: document.getElementById("shiftStart").value + ":00",
          shift_end: document.getElementById("shiftEnd").value + ":00",
          grace_minutes: Number(document.getElementById("grace").value),
        }),
      });
      document.getElementById("setMsg").textContent = "Saved";
    } catch (e) {
      document.getElementById("setMsg").textContent = fmtDetail(e);
    }
  };

  document.getElementById("importCsv").onclick = async () => {
    const f = document.getElementById("csvFile").files[0];
    if (!f) return;
    const fd = new FormData();
    fd.append("file", f);
    const res = await fetch("/api/users/import-csv", {
      method: "POST",
      headers: { Authorization: `Bearer ${token()}` },
      body: fd,
    });
    const data = await res.json();
    document.getElementById("importOut").textContent = JSON.stringify(data, null, 2);
  };

  document.getElementById("createKiosk").onclick = async () => {
    await api("/api/kiosks", {
      method: "POST",
      body: JSON.stringify({ name: document.getElementById("kioskName").value || "Door Kiosk" }),
    });
    renderAdmin(app);
  };

  document.getElementById("createTv").onclick = async () => {
    const data = await api("/api/display-tokens", {
      method: "POST",
      body: JSON.stringify({ label: document.getElementById("tvLabel").value || "Reception TV" }),
    });
    const url = location.origin + data.display_path;
    document.getElementById("tvOut").innerHTML = `Open on TV: <a href="${url}" target="_blank">${url}</a> (copy now — shown once)`;
  };

  document.getElementById("addHoliday").onclick = async () => {
    await api("/api/admin/holidays", {
      method: "POST",
      body: JSON.stringify({
        date: document.getElementById("hDate").value,
        name: document.getElementById("hName").value,
      }),
    });
    renderAdmin(app);
  };

  document.getElementById("dlCsv").onclick = async () => {
    const y = document.getElementById("y").value;
    const m = document.getElementById("m").value;
    const res = await fetch(`/api/reports/monthly.csv?year=${y}&month=${m}`, {
      headers: { Authorization: `Bearer ${token()}` },
    });
    const blob = await res.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `attendance_${y}_${m}.csv`;
    a.click();
  };
}

function renderKioskPair(app) {
  app.innerHTML = `
  <div class="kiosk-screen">
    <h1>Pair this kiosk</h1>
    <p class="muted">Enter the pair code from Admin</p>
    <div class="card" style="width:min(360px,100%)">
      <input id="pairCode" placeholder="ABC123" style="text-transform:uppercase;text-align:center;font-size:1.4rem;letter-spacing:0.2em" />
      <button id="pairBtn" style="width:100%;margin-top:1rem">Pair</button>
      <p id="pairMsg" class="muted"></p>
    </div>
  </div>`;
  document.getElementById("pairBtn").onclick = async () => {
    try {
      const data = await api("/api/kiosks/pair", {
        method: "POST",
        body: JSON.stringify({ pair_code: document.getElementById("pairCode").value }),
      });
      localStorage.setItem("oams_kiosk_id", String(data.kiosk_id));
      localStorage.setItem("oams_kiosk_secret", data.device_secret);
      localStorage.setItem("oams_kiosk_name", data.name);
      location.href = "/kiosk";
    } catch (e) {
      document.getElementById("pairMsg").textContent = fmtDetail(e);
    }
  };
}

async function renderKiosk(app) {
  const kioskId = localStorage.getItem("oams_kiosk_id");
  const secret = localStorage.getItem("oams_kiosk_secret");
  if (!kioskId || !secret) {
    location.href = "/kiosk/pair";
    return;
  }
  app.innerHTML = `
  <div class="kiosk-screen">
    <h1 id="kioskTitle">Door check-in</h1>
    <p class="kiosk-meta">Scan with the OAMS punch page on your phone</p>
    <div id="qrcode"></div>
    <p class="kiosk-meta" id="kioskTimer">Refreshing…</p>
  </div>`;

  async function refresh() {
    try {
      const data = await fetch(`/api/kiosks/${kioskId}/qr`, {
        headers: { "X-Kiosk-Secret": secret },
      }).then(async (r) => {
        if (!r.ok) throw new Error((await r.json()).detail || "QR failed");
        return r.json();
      });
      document.getElementById("kioskTitle").textContent = data.kiosk_name;
      const el = document.getElementById("qrcode");
      el.innerHTML = "";
      new QRCode(el, { text: data.token, width: 280, height: 280, correctLevel: QRCode.CorrectLevel.M });
      let left = data.expires_in;
      document.getElementById("kioskTimer").textContent = `Code refreshes in ${left}s`;
    } catch (e) {
      document.getElementById("kioskTimer").textContent = fmtDetail(e) + " — re-pair if needed";
    }
  }
  await refresh();
  setInterval(refresh, 12000);
}

window.addEventListener("popstate", route);
document.addEventListener("DOMContentLoaded", () => {
  document.body.addEventListener("click", (e) => {
    const a = e.target.closest("a");
    if (a && a.origin === location.origin && !a.pathname.startsWith("/display") && !a.target) {
      e.preventDefault();
      history.pushState({}, "", a.pathname);
      route();
    }
  });
  route();
});
