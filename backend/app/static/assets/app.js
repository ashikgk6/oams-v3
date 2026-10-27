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

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[char]);
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
      <div class="brand">Employee Attendance Portal</div>
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
        <h1>Employee Attendance Portal</h1>
        <p class="muted">
          Sign in with your work credentials to access your attendance
          dashboard and workplace services.
        </p>

        <div class="field">
          <label for="email">Work email</label>
          <input
            id="email"
            type="email"
            placeholder="Enter your work email address"
            autocomplete="username"
            required
          />
        </div>

        <div class="field">
          <label for="password">Password</label>
          <input
            id="password"
            type="password"
            placeholder="Enter your password"
            autocomplete="current-password"
            required
          />
        </div>

        <p class="error hidden" id="err" role="alert"></p>

        <button id="loginBtn" type="button" style="width:100%">
          Sign in
        </button>

        <p class="muted" style="margin-top:1rem;font-size:0.85rem">
          For authorized employees only. Please use your registered
          work account to sign in.
        </p>
      </div>
    </div>`;

  const emailInput = document.getElementById("email");
  const passwordInput = document.getElementById("password");
  const loginBtn = document.getElementById("loginBtn");
  const err = document.getElementById("err");

  async function handleLogin() {
    if (loginBtn.disabled) {
      return;
    }

    err.classList.add("hidden");
    err.textContent = "";

    const email = emailInput.value.trim();
    const password = passwordInput.value;

    if (!email || !password) {
      err.textContent = "Please enter your work email and password.";
      err.classList.remove("hidden");
      return;
    }

    loginBtn.disabled = true;
    loginBtn.textContent = "Signing in…";

    try {
      const data = await api("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({
          email,
          password,
        }),
      });

      setAuth(data);
      location.href = "/dashboard";
    } catch (e) {
      err.textContent =
        "We couldn't sign you in. Check your email and password, then try again.";
      err.classList.remove("hidden");
    } finally {
      loginBtn.disabled = false;
      loginBtn.textContent = "Sign in";
    }
  }

  loginBtn.onclick = handleLogin;

  // Allow employees to submit the form using the Enter key.
  [emailInput, passwordInput].forEach((input) => {
    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        handleLogin();
      }
    });
  });
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
        <button type="button" id="scanAgain" hidden>Scan again</button>
      </div>
    </div>`,
    "/punch"
  );
  bindLogout();

  const msg = document.getElementById("punchMsg");
  const stopBtn = document.getElementById("stopScan");
  const scanAgainBtn = document.getElementById("scanAgain");

  let busy = false;
  let scanActive = false;
  let cameraId = null;

   // Stop the camera before processing the scanned QR code.
  async function stopScanner() {
    if (!html5QrCode || !scanActive) {
      return;
    }

    try {
      await html5QrCode.stop();
    } finally {
      scanActive = false;
      stopBtn.disabled = true;
    }
  }

  // Start scanning only when explicitly requested.
  async function startScanner() {
    if (!html5QrCode || !cameraId || scanActive) {
      return;
    }

    try {
      await html5QrCode.start(
        cameraId,
        { fps: 8, qrbox: { width: 250, height: 250 } },
        onScan,
        () => {}
      );

      scanActive = true;
      stopBtn.disabled = false;
      msg.className = "punch-result";
      msg.textContent = "Ready to scan one QR code.";
    } catch (error) {
      scanActive = false;
      throw error;
    }
  }

   // Process one QR scan, then require the employee to scan again manually.
  async function onScan(decoded) {
    if (busy) {
      return;
    }

    // Set the lock synchronously before awaiting anything.
    busy = true;
    stopBtn.disabled = true;
    msg.className = "punch-result";
    msg.textContent = "QR scanned. Stopping camera…";

    try {
      // Stop repeated QR detections before requesting location or sending
      // the attendance request.
      await stopScanner();

      msg.textContent = "QR scanned. Checking your location…";

      if (!navigator.geolocation) {
        throw new Error(
          "This browser does not support location verification."
        );
      }

      const position = await new Promise((resolve, reject) => {
        navigator.geolocation.getCurrentPosition(resolve, reject, {
          enableHighAccuracy: true,
          timeout: 15000,
          maximumAge: 0,
        });
      }).catch((error) => {
        if (error && typeof error.code === "number") {
          const messages = {
            1: "Location permission was denied. Allow location access and scan again.",
            2: "Your location is unavailable. Move to an area with better GPS reception and try again.",
            3: "Location request timed out. Please try again.",
          };

          throw new Error(
            messages[error.code] || "Could not verify your location."
          );
        }

        throw error;
      });

      msg.textContent =
        "Location received. Verifying QR and office distance…";

      const data = await api("/api/punches", {
        method: "POST",
        body: JSON.stringify({
          qr_token: decoded,
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          accuracy_meters: position.coords.accuracy,
        }),
      });

      msg.className = "punch-result";
      msg.innerHTML =
        `<div class="success"><strong>${data.direction}</strong> · ` +
        `${new Date(data.ts).toLocaleTimeString("en-IN")}<br/>` +
        `${data.message}</div>`;

      if (navigator.vibrate) {
        navigator.vibrate(80);
      }
    } catch (error) {
      const message =
        error && typeof error.message === "string"
          ? error.message
          : fmtDetail(error);

      msg.textContent = message;
      msg.className = "punch-result error";
    } finally {
      // Do not automatically unlock after a timeout.
      // An explicit user action is required to scan again.
      scanAgainBtn.hidden = false;
      scanAgainBtn.disabled = false;
      stopBtn.disabled = true;
    }
  }

  // Start the camera and select the rear camera when available.
  if (window.Html5Qrcode) {
    html5QrCode = new Html5Qrcode("reader");

    Html5Qrcode.getCameras()
      .then(async (cameras) => {
        const camera =
          cameras.find((item) =>
            /back|rear|environment/i.test(item.label)
          ) || cameras[0];

        if (!camera) {
          msg.textContent = "No camera found.";
          return;
        }

        cameraId = camera.id;

        try {
          await startScanner();
        } catch (error) {
          msg.textContent = "Camera error: " + error;
          scanAgainBtn.hidden = false;
          scanAgainBtn.disabled = false;
        }
      })
      .catch((error) => {
        msg.textContent = "Camera error: " + error;
      });
  } else {
    msg.textContent = "QR library failed to load.";
  }

  // Let the employee pause scanning manually.
  stopBtn.onclick = async () => {
    if (busy) {
      return;
    }

    busy = true;

    try {
      await stopScanner();
      msg.textContent =
        "Scanning paused. Tap Scan again when ready.";
    } catch (error) {
      msg.textContent = "Could not stop camera: " + error;
    } finally {
      scanAgainBtn.hidden = false;
      scanAgainBtn.disabled = false;
      stopBtn.disabled = true;
    }
  };

  // Only this button unlocks the next scan.
  scanAgainBtn.onclick = async () => {
    if (busy || scanActive) {
      return;
    }

    scanAgainBtn.disabled = true;
    scanAgainBtn.hidden = true;
    busy = false;
    msg.textContent = "Starting scanner…";

    try {
      await startScanner();
    } catch (error) {
      busy = true;
      msg.textContent = "Camera error: " + error;
      scanAgainBtn.hidden = false;
      scanAgainBtn.disabled = false;
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
  if (localStorage.getItem("oams_role") !== "admin") {
    app.innerHTML = shell('<div class="card"><h2>Admin access required</h2><p class="muted">Your account does not have permission to manage employees.</p></div>', "/admin");
    bindLogout();
    return;
  }

  app.innerHTML = shell('<div class="card"><p class="muted">Loading admin dashboard…</p></div>', "/admin");
  bindLogout();

  let settings, kiosks, tokens, holidays, teams, users;
  try {
    [settings, kiosks, tokens, holidays, teams, users] = await Promise.all([
      api("/api/admin/settings"),
      api("/api/kiosks"),
      api("/api/display-tokens"),
      api("/api/admin/holidays"),
      api("/api/teams"),
      api("/api/users"),
    ]);
  } catch (error) {
    app.innerHTML = shell(`<div class="card"><h2>Could not load admin dashboard</h2><p class="error">${escapeHtml(fmtDetail(error))}</p><p class="muted">Check that your account has admin permissions and try again.</p></div>`, "/admin");
    bindLogout();
    return;
  }

  const now = new Date();
  const managers = users.filter((u) => u.role === "manager");
  const activeUsers = users.filter((u) => u.active);
  const employeeCount = users.filter((u) => u.role === "employee").length;
  const managerCount = managers.length;
  const teamOptions = (selectedId = "") =>
    `<option value="">No team</option>${teams.map((t) => `<option value="${t.id}" ${String(t.id) === String(selectedId) ? "selected" : ""}>${escapeHtml(t.name)}</option>`).join("")}`;
  const managerOptions = (selectedId = "") =>
    `<option value="">No manager assigned</option>${managers.map((u) => `<option value="${u.id}" ${String(u.id) === String(selectedId) ? "selected" : ""}>${escapeHtml(u.name)} (${escapeHtml(u.email)})</option>`).join("")}`;

  app.innerHTML = shell(
    `
    <div class="admin-heading">
      <div><p class="eyebrow">WORKSPACE MANAGEMENT</p><h1>Admin dashboard</h1><p class="muted">Manage employees, teams, office settings and attendance devices.</p></div>
    </div>
    <div class="grid stats admin-stats">
      <div class="stat"><div class="n">${users.length}</div><div class="l">Total accounts</div></div>
      <div class="stat"><div class="n">${activeUsers.length}</div><div class="l">Active accounts</div></div>
      <div class="stat"><div class="n">${employeeCount}</div><div class="l">Employees</div></div>
      <div class="stat"><div class="n">${managerCount}</div><div class="l">Managers</div></div>
      <div class="stat"><div class="n">${teams.length}</div><div class="l">Teams</div></div>
    </div>

    <div class="card">
      <div class="section-heading"><div><h2>Employees</h2><p class="muted">Search the directory and review each account's role and team.</p></div><span class="count-pill">${users.length} accounts</span></div>
      <div class="field"><label for="userSearch">Search by name, email, role or team</label><input id="userSearch" type="search" placeholder="Start typing to filter employees…" /></div>
      <div class="table-wrap"><table><thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Team</th><th>Status</th></tr></thead><tbody id="userRows"></tbody></table></div>
      <p id="userListMsg" class="muted"></p>
    </div>

    <div class="grid admin-two-col">
      <div class="card">
        <h2>Add employee or manager</h2>
        <p class="muted">Create an account with a temporary password. Share credentials securely with the employee.</p>
        <form id="createUserForm">
          <div class="field"><label for="newUserName">Full name</label><input id="newUserName" name="name" required maxlength="160" autocomplete="name" /></div>
          <div class="field"><label for="newUserEmail">Work email</label><input id="newUserEmail" name="email" type="email" required autocomplete="email" /></div>
          <div class="field"><label for="newUserPassword">Initial password</label><input id="newUserPassword" name="password" type="password" required minlength="8" autocomplete="new-password" /></div>
          <div class="field"><label for="newUserRole">Role</label><select id="newUserRole" name="role"><option value="employee">Employee</option><option value="manager">Manager</option><option value="admin">Admin</option></select></div>
          <div class="field"><label for="newUserTeam">Team</label><select id="newUserTeam" name="team_id">${teamOptions()}</select></div>
          <button id="createUserBtn" type="submit">Create account</button>
          <p id="createUserMsg" class="muted" role="status"></p>
        </form>
      </div>
      <div class="card">
        <h2>Create a team</h2>
        <p class="muted">Choose an existing manager to assign ownership when the team is created.</p>
        <form id="createTeamForm">
          <div class="field"><label for="newTeamName">Team name</label><input id="newTeamName" name="name" required maxlength="120" placeholder="e.g. Engineering" /></div>
          <div class="field"><label for="newTeamManager">Team manager</label><select id="newTeamManager" name="manager_id">${managerOptions()}</select></div>
          <button id="createTeamBtn" type="submit">Create team</button>
          <p id="createTeamMsg" class="muted" role="status"></p>
        </form>
        <h3>Current teams</h3>
        <div class="table-wrap"><table><thead><tr><th>Team</th><th>Assigned manager</th><th>Members</th><th>Action</th></tr></thead><tbody id="teamRows"></tbody></table></div>
        <p class="muted">Select a manager and choose Save to change the assignment. Select “No manager assigned” to clear it.</p>
      </div>
    </div>

    <div class="card">
      <h2>Import employees from CSV</h2>
      <p class="muted">CSV headers: <code>name,email,role,team,password</code>. Use a unique password per account and distribute credentials securely. Roles: employee, manager or admin.</p>
      <div class="field"><label for="csvFile">CSV file</label><input type="file" id="csvFile" accept=".csv,text/csv" /></div>
      <button id="importCsv" type="button">Import CSV</button>
      <p id="importMsg" class="muted" role="status"></p>
      <pre id="importOut" class="import-output" hidden></pre>
    </div>

    <div class="card">
      <h2>Office settings (IST)</h2>
      <div class="field"><label for="officeName">Office name</label><input id="officeName" value="${escapeHtml(settings.office_name)}" /></div>
      <div class="row">
        <div class="field" style="flex:1"><label for="shiftStart">Shift start</label><input id="shiftStart" type="time" value="${escapeHtml(settings.shift_start.slice(0, 5))}" /></div>
        <div class="field" style="flex:1"><label for="shiftEnd">Shift end</label><input id="shiftEnd" type="time" value="${escapeHtml(settings.shift_end.slice(0, 5))}" /></div>
        <div class="field" style="flex:1"><label for="grace">Grace (min)</label><input id="grace" type="number" min="0" value="${settings.grace_minutes}" /></div>
      </div>
      <button id="saveSettings">Save settings</button><p id="setMsg" class="muted" role="status"></p>
    </div>

    <div class="grid admin-two-col">
      <div class="card">
        <h2>Door kiosks</h2>
        <div class="row"><input id="kioskName" placeholder="Lobby tablet" style="max-width:240px" /><button id="createKiosk">Create kiosk</button></div>
        <div class="table-wrap"><table style="margin-top:1rem"><thead><tr><th>Name</th><th>Pair code</th><th>Paired</th></tr></thead><tbody>
        ${kiosks.map((k) => `<tr><td>${escapeHtml(k.name)}</td><td><code>${escapeHtml(k.pair_code || "—")}</code></td><td>${k.paired_at ? "Yes" : "No"}</td></tr>`).join("")}
        </tbody></table></div>
        <p class="muted">On the tablet open <a href="/kiosk/pair">/kiosk/pair</a> and enter the pair code.</p>
      </div>
      <div class="card">
        <h2>TV display tokens</h2>
        <div class="row"><input id="tvLabel" value="Reception TV" style="max-width:240px" /><button id="createTv">Create display URL</button></div>
        <p id="tvOut" class="success"></p>
        <div class="table-wrap"><table style="margin-top:1rem"><thead><tr><th>Label</th><th>Prefix</th><th>Revoked</th></tr></thead><tbody>
        ${tokens.map((t) => `<tr><td>${escapeHtml(t.label)}</td><td><code>${escapeHtml(t.token_prefix)}…</code></td><td>${t.revoked_at ? "Yes" : "No"}</td></tr>`).join("")}
        </tbody></table></div>
      </div>
    </div>

    <div class="grid admin-two-col">
      <div class="card">
        <h2>Holidays</h2>
        <div class="row"><input type="date" id="hDate" /><input id="hName" placeholder="Holiday name" /><button id="addHoliday">Add holiday</button></div>
        <ul>${holidays.map((h) => `<li>${escapeHtml(h.date)} — ${escapeHtml(h.name)}</li>`).join("")}</ul>
        <p id="holidayMsg" class="muted" role="status"></p>
      </div>
      <div class="card">
        <h2>Monthly attendance CSV</h2>
        <div class="row"><input type="number" id="y" value="${now.getFullYear()}" style="max-width:120px" /><input type="number" id="m" value="${now.getMonth() + 1}" min="1" max="12" style="max-width:90px" /><button id="dlCsv">Download report</button></div>
        <p id="reportMsg" class="muted" role="status"></p>
      </div>
    </div>`,
    "/admin"
  );
  bindLogout();

  function renderUserRows(query = "") {
    const q = query.trim().toLowerCase();
    const filtered = users.filter((u) =>
      [u.name, u.email, u.role, u.team_name || ""].some((v) => String(v).toLowerCase().includes(q))
    );
    const rows = document.getElementById("userRows");
    const msg = document.getElementById("userListMsg");
    if (!filtered.length) {
      rows.innerHTML = '<tr><td colspan="5" class="muted">No matching accounts.</td></tr>';
    } else {
      rows.innerHTML = filtered.map((u) => `<tr>
        <td>${escapeHtml(u.name)}</td><td>${escapeHtml(u.email)}</td>
        <td><span class="role-pill role-${escapeHtml(u.role)}">${escapeHtml(u.role)}</span></td>
        <td>${escapeHtml(u.team_name || "—")}</td>
        <td><span class="status-pill ${u.active ? "is-active" : "is-inactive"}">${u.active ? "Active" : "Inactive"}</span></td>
      </tr>`).join("");
    }
    msg.textContent = `Showing ${filtered.length} of ${users.length} accounts.`;
  }

  function renderTeamRows() {
    const rows = document.getElementById("teamRows");
    rows.innerHTML = teams.length ? teams.map((team) => {
      const count = users.filter((u) => u.team_id === team.id).length;
      return `<tr>
        <td>${escapeHtml(team.name)}</td>
        <td><select aria-label="Manager for ${escapeHtml(team.name)}" data-team-manager="${team.id}">${managerOptions(team.manager_id)}</select></td>
        <td>${count}</td>
        <td><button type="button" data-save-team="${team.id}">Save</button></td>
      </tr>`;
    }).join("") : '<tr><td colspan="4" class="muted">No teams created yet.</td></tr>';
  }

  renderUserRows();
  renderTeamRows();
  document.getElementById("userSearch").addEventListener("input", (event) => renderUserRows(event.target.value));

  document.getElementById("teamRows").addEventListener("click", async (event) => {
    const button = event.target.closest("[data-save-team]");
    if (!button) return;
    const teamId = Number(button.dataset.saveTeam);
    const select = document.querySelector(`[data-team-manager="${teamId}"]`);
    const message = document.getElementById("createTeamMsg");
    button.disabled = true;
    message.textContent = "Updating team manager…";
    message.className = "muted";
    try {
      const managerValue = select.value;
      const updated = await api(`/api/teams/${teamId}`, {
        method: "PATCH",
        body: JSON.stringify({ manager_id: managerValue ? Number(managerValue) : null }),
      });
      teams = teams.map((team) => team.id === updated.id ? updated : team);
      renderTeamRows();
      message.textContent = `Manager assignment saved for "${updated.name}".`;
      message.className = "success";
    } catch (error) {
      message.textContent = fmtDetail(error);
      message.className = "error";
    } finally {
      button.disabled = false;
    }
  });

  document.getElementById("createUserForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = document.getElementById("createUserBtn");
    const message = document.getElementById("createUserMsg");
    button.disabled = true;
    message.textContent = "Creating account…";
    try {
      const teamValue = document.getElementById("newUserTeam").value;
      const created = await api("/api/users", {
        method: "POST",
        body: JSON.stringify({
          name: document.getElementById("newUserName").value.trim(),
          email: document.getElementById("newUserEmail").value.trim(),
          password: document.getElementById("newUserPassword").value,
          role: document.getElementById("newUserRole").value,
          team_id: teamValue ? Number(teamValue) : null,
        }),
      });
      users.push(created);
      if (created.role === "manager") {
        const managerSelect = document.getElementById("newTeamManager");
        managerSelect.insertAdjacentHTML("beforeend", `<option value="${created.id}">${escapeHtml(created.name)} (${escapeHtml(created.email)})</option>`);
      }
      document.getElementById("createUserForm").reset();
      renderUserRows(document.getElementById("userSearch").value);
      renderTeamRows();
      document.getElementById("newUserTeam").value = "";
      message.textContent = `Account created for ${created.name}.`;
      message.className = "success";
    } catch (error) {
      message.textContent = fmtDetail(error);
      message.className = "error";
    } finally {
      button.disabled = false;
    }
  });

  document.getElementById("createTeamForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = document.getElementById("createTeamBtn");
    const message = document.getElementById("createTeamMsg");
    button.disabled = true;
    message.textContent = "Creating team…";
    try {
      const managerValue = document.getElementById("newTeamManager").value;
      const team = await api("/api/teams", {
        method: "POST",
        body: JSON.stringify({
          name: document.getElementById("newTeamName").value.trim(),
          manager_id: managerValue ? Number(managerValue) : null,
        }),
      });
      teams.push(team);
      document.getElementById("createTeamForm").reset();
      document.getElementById("newUserTeam").insertAdjacentHTML("beforeend", `<option value="${team.id}">${escapeHtml(team.name)}</option>`);
      renderTeamRows();
      message.textContent = `Team "${team.name}" created.`;
      message.className = "success";
    } catch (error) {
      message.textContent = fmtDetail(error);
      message.className = "error";
    } finally {
      button.disabled = false;
    }
  });

  document.getElementById("importCsv").onclick = async () => {
    const fileInput = document.getElementById("csvFile");
    const message = document.getElementById("importMsg");
    const output = document.getElementById("importOut");
    const file = fileInput.files[0];
    if (!file) {
      message.textContent = "Choose a CSV file first.";
      message.className = "error";
      return;
    }
    if (!file.name.toLowerCase().endsWith(".csv")) {
      message.textContent = "Please select a .csv file.";
      message.className = "error";
      return;
    }
    const formData = new FormData();
    formData.append("file", file);
    const button = document.getElementById("importCsv");
    button.disabled = true;
    message.textContent = "Importing accounts…";
    message.className = "muted";
    output.hidden = true;
    try {
      const result = await api("/api/users/import-csv", { method: "POST", body: formData });
      output.textContent = JSON.stringify(result, null, 2);
      output.hidden = false;
      const createdCount = Array.isArray(result.created) ? result.created.length : 0;
      const skippedCount = Array.isArray(result.skipped) ? result.skipped.length : 0;
      const errorCount = Array.isArray(result.errors) ? result.errors.length : 0;
      message.textContent = `Import finished: ${createdCount} created, ${skippedCount} skipped, ${errorCount} errors.`;
      message.className = errorCount ? "error" : "success";
      const refreshedUsers = await api("/api/users");
      users = refreshedUsers;
      const refreshedTeams = await api("/api/teams");
      teams = refreshedTeams;
      renderUserRows(document.getElementById("userSearch").value);
      renderTeamRows();
      document.getElementById("newUserTeam").innerHTML = teamOptions();
      document.getElementById("newTeamManager").innerHTML = managerOptions();
    } catch (error) {
      message.textContent = fmtDetail(error);
      message.className = "error";
    } finally {
      button.disabled = false;
    }
  };

  document.getElementById("saveSettings").onclick = async () => {
    const message = document.getElementById("setMsg");
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
      message.textContent = "Settings saved.";
      message.className = "success";
    } catch (error) {
      message.textContent = fmtDetail(error);
      message.className = "error";
    }
  };

  document.getElementById("createKiosk").onclick = async () => {
    try {
      await api("/api/kiosks", { method: "POST", body: JSON.stringify({ name: document.getElementById("kioskName").value || "Door Kiosk" }) });
      await renderAdmin(app);
    } catch (error) {
      alert(fmtDetail(error));
    }
  };

  document.getElementById("createTv").onclick = async () => {
    try {
      const data = await api("/api/display-tokens", { method: "POST", body: JSON.stringify({ label: document.getElementById("tvLabel").value || "Reception TV" }) });
      const url = location.origin + data.display_path;
      document.getElementById("tvOut").innerHTML = `Open on TV: <a href="${url}" target="_blank" rel="noopener noreferrer">${escapeHtml(url)}</a> (copy now — shown once)`;
    } catch (error) {
      document.getElementById("tvOut").textContent = fmtDetail(error);
      document.getElementById("tvOut").className = "error";
    }
  };

  document.getElementById("addHoliday").onclick = async () => {
    const message = document.getElementById("holidayMsg");
    try {
      await api("/api/admin/holidays", { method: "POST", body: JSON.stringify({ date: document.getElementById("hDate").value, name: document.getElementById("hName").value.trim() }) });
      message.textContent = "Holiday added.";
      message.className = "success";
      await renderAdmin(app);
    } catch (error) {
      message.textContent = fmtDetail(error);
      message.className = "error";
    }
  };

  document.getElementById("dlCsv").onclick = async () => {
    const year = document.getElementById("y").value;
    const month = document.getElementById("m").value;
    const message = document.getElementById("reportMsg");
    if (!year || Number(month) < 1 || Number(month) > 12) {
      message.textContent = "Enter a valid year and month.";
      message.className = "error";
      return;
    }
    try {
      const response = await fetch(`/api/reports/monthly.csv?year=${encodeURIComponent(year)}&month=${encodeURIComponent(month)}`, { headers: authHeaders(false) });
      if (!response.ok) throw new Error(await response.text());
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `attendance_${year}_${month}.csv`;
      link.click();
      URL.revokeObjectURL(url);
      message.textContent = "Report downloaded.";
      message.className = "success";
    } catch (error) {
      message.textContent = fmtDetail(error);
      message.className = "error";
    }
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
