/* =========================================================
   FoodLink — script.js  (Phase 2: Python/Flask backend)
   All data now comes from the Flask JSON API (app.py) via
   fetch(). Session auth uses a cookie, so every fetch call
   below includes credentials: 'same-origin'.
   ========================================================= */

const API_BASE = ''; // same-origin, so relative paths like /api/... work

document.addEventListener('DOMContentLoaded', function () {
  highlightActiveNav();
  initLogoutButtons();
});

/* ---------------------------------------------------------
   0. LOW-LEVEL FETCH HELPER
--------------------------------------------------------- */
async function apiFetch(url, options = {}) {
  const opts = Object.assign({ credentials: 'same-origin' }, options);
  if (opts.body && !(opts.headers && opts.headers['Content-Type'])) {
    opts.headers = Object.assign({ 'Content-Type': 'application/json' }, opts.headers || {});
  }
  const response = await fetch(API_BASE + url, opts);
  let data = null;
  try { data = await response.json(); } catch (e) { /* no body */ }
  if (!response.ok) {
    const message = (data && data.error) ? data.error : 'Something went wrong. Please try again.';
    throw new Error(message);
  }
  return data;
}

/* ---------------------------------------------------------
   1. NAV — highlight current page link
--------------------------------------------------------- */
function highlightActiveNav() {
  const current = window.location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('.fl-navbar .nav-link').forEach(link => {
    const href = link.getAttribute('href');
    if (href === current) {
      link.classList.add('active');
    }
  });
}

/* ---------------------------------------------------------
   2. FORM VALIDATION HELPERS
--------------------------------------------------------- */
function showFieldError(input, message) {
  input.classList.add('is-invalid');
  const feedback = input.parentElement.querySelector('.invalid-feedback');
  if (feedback) feedback.textContent = message;
}

function clearFieldError(input) {
  input.classList.remove('is-invalid');
}

function validateRequired(form) {
  let valid = true;
  form.querySelectorAll('[required]').forEach(input => {
    clearFieldError(input);
    if (!input.value || input.value.trim() === '') {
      showFieldError(input, 'This field is required.');
      valid = false;
    }
  });
  return valid;
}

function validateEmail(input) {
  const pattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  clearFieldError(input);
  if (!pattern.test(input.value)) {
    showFieldError(input, 'Please enter a valid email address.');
    return false;
  }
  return true;
}

function validatePhone(input) {
  const pattern = /^[0-9]{10}$/;
  clearFieldError(input);
  if (!pattern.test(input.value)) {
    showFieldError(input, 'Please enter a valid 10-digit phone number.');
    return false;
  }
  return true;
}

function validatePasswordMatch(passInput, confirmInput) {
  clearFieldError(confirmInput);
  if (passInput.value.length < 6) {
    showFieldError(passInput, 'Password must be at least 6 characters.');
    return false;
  }
  if (passInput.value !== confirmInput.value) {
    showFieldError(confirmInput, 'Passwords do not match.');
    return false;
  }
  return true;
}

function showSuccessBox(message) {
  const box = document.getElementById('successBox');
  if (!box) return;
  if (message) box.textContent = message;
  box.classList.add('show');
  box.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function showErrorBox(message) {
  const box = document.getElementById('errorBox');
  if (!box) return;
  if (message) box.textContent = message;
  box.style.display = 'block';
  box.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function hideBoxes() {
  const s = document.getElementById('successBox');
  const e = document.getElementById('errorBox');
  if (s) s.classList.remove('show');
  if (e) e.style.display = 'none';
}

/* ---------------------------------------------------------
   3. AUTH GUARD — used at the top of every protected page
--------------------------------------------------------- */
async function requireAuth(role, loginUrl) {
  try {
    const data = await apiFetch('/api/session');
    if (!data.loggedIn || data.role !== role) {
      window.location.href = loginUrl;
      return null;
    }
    return data; // { loggedIn: true, role, name }
  } catch (e) {
    window.location.href = loginUrl;
    return null;
  }
}

/* ---------------------------------------------------------
   4. LOGIN / REGISTER / LOGOUT
--------------------------------------------------------- */
async function handleLogin(event, role, redirectUrl) {
  event.preventDefault();
  hideBoxes();
  const form = event.target;
  if (!validateRequired(form)) return;

  const emailInput = form.querySelector('input[type="email"]');
  if (emailInput && !validateEmail(emailInput)) return;

  const payload = {
    email: form.email.value,
    password: form.password.value
  };

  try {
    await apiFetch('/api/' + role + '/login', { method: 'POST', body: JSON.stringify(payload) });
    window.location.href = redirectUrl;
  } catch (err) {
    showErrorBox(err.message);
  }
}

async function handleRegister(event, role, redirectUrl) {
  event.preventDefault();
  hideBoxes();
  const form = event.target;
  if (!validateRequired(form)) return;

  const emailInput = form.querySelector('input[type="email"]');
  if (emailInput && !validateEmail(emailInput)) return;

  const phoneInput = form.querySelector('input[name="phone"]');
  if (phoneInput && !validatePhone(phoneInput)) return;

  const passInput = form.querySelector('input[name="password"]');
  const confirmInput = form.querySelector('input[name="confirm_password"]');
  if (passInput && confirmInput && !validatePasswordMatch(passInput, confirmInput)) return;

  const payload = {};
  new FormData(form).forEach((value, key) => { payload[key] = value; });

  try {
    await apiFetch('/api/' + role + '/register', { method: 'POST', body: JSON.stringify(payload) });
    sessionStorage.setItem('fl_just_registered', role);
    window.location.href = redirectUrl;
  } catch (err) {
    showErrorBox(err.message);
  }
}

function initLogoutButtons() {
  document.querySelectorAll('.btn-logout').forEach(btn => {
    btn.addEventListener('click', async function (e) {
      e.preventDefault();
      try {
        await apiFetch('/api/logout', { method: 'POST' });
      } catch (err) { /* ignore */ }
      window.location.href = 'index.html';
    });
  });
}

/* ---------------------------------------------------------
   5. DONOR: stats, donate form, history
--------------------------------------------------------- */
async function loadDonorStats() {
  try {
    const stats = await apiFetch('/api/donor/stats');
    setText('statTotal', stats.total);
    setText('statPending', stats.pending);
    setText('statCompleted', stats.completed);
    setText('statFoodDonated', stats.foodDonated + ' units');
    setText('statPeopleFed', stats.peopleFed);
  } catch (err) { /* ignore */ }
}

async function submitDonation(event) {
  event.preventDefault();
  hideBoxes();
  const form = event.target;
  if (!validateRequired(form)) return;

  const payload = {};
  new FormData(form).forEach((value, key) => { payload[key] = value; });

  try {
    const result = await apiFetch('/api/donations', { method: 'POST', body: JSON.stringify(payload) });
    const peopleFedNote = result.estimatedPeopleFed
      ? ` Our AI model estimates this can feed ~${result.estimatedPeopleFed} people.`
      : '';
    showSuccessBox('Your food donation has been successfully submitted.' + peopleFedNote);
    form.reset();
  } catch (err) {
    showErrorBox(err.message);
  }
}

async function loadDonationHistory() {
  const tbody = document.getElementById('donationHistoryBody');
  if (!tbody) return;
  try {
    const donations = await apiFetch('/api/donor/donations');
    if (donations.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">You haven\'t submitted any donations yet.</td></tr>';
      return;
    }
    tbody.innerHTML = donations.map(d => `
      <tr>
        <td>${escapeHtml(d.food_name)}</td>
        <td>${escapeHtml(d.category)}</td>
        <td>${escapeHtml(String(d.quantity))} ${escapeHtml(d.unit)}</td>
        <td>${escapeHtml(d.best_before)}</td>
        <td>${d.estimated_people_fed ? '~' + escapeHtml(String(d.estimated_people_fed)) : '—'}</td>
        <td><span class="status-badge status-${d.status}">${capitalize(d.status)}</span></td>
      </tr>
    `).join('');
  } catch (err) { /* ignore */ }
}

/* ---------------------------------------------------------
   6. RECEIVER: stats, available food, history
--------------------------------------------------------- */
async function loadReceiverStats() {
  try {
    const stats = await apiFetch('/api/receiver/stats');
    setText('statAvailable', stats.available);
    setText('statRequested', stats.requested);
    setText('statReceived', stats.received);
  } catch (err) { /* ignore */ }
}

async function loadAvailableFood() {
  const container = document.getElementById('foodCardsContainer');
  if (!container) return;
  try {
    const donations = await apiFetch('/api/donations/available');
    if (donations.length === 0) {
      container.innerHTML = '<p class="text-center text-muted">No food donations available right now. Please check back later.</p>';
      return;
    }
    container.innerHTML = donations.map(d => `
      <div class="col-md-6 col-lg-4 mb-4">
        <div class="food-card">
          <div class="food-card-header">
            <strong>${escapeHtml(d.food_name)}</strong>
            <span class="${d.food_type === 'veg' ? 'badge-veg' : 'badge-nonveg'}">${d.food_type === 'veg' ? 'Veg' : 'Non-Veg'}</span>
          </div>
          <div class="food-card-body">
            <ul>
              <li><strong>Donor:</strong> ${escapeHtml(d.donor)}</li>
              <li><strong>Quantity:</strong> ${escapeHtml(String(d.quantity))} ${escapeHtml(d.unit)}</li>
              <li><strong>Best Before:</strong> ${escapeHtml(d.best_before)}</li>
              <li><strong>Pickup:</strong> ${escapeHtml(d.pickup_address)}</li>
              ${d.estimated_people_fed ? `<li><strong>🍽️ AI Estimate:</strong> feeds ~${escapeHtml(String(d.estimated_people_fed))} people</li>` : ''}
            </ul>
            <p class="small mb-3">${escapeHtml(d.description || '')}</p>
            <button class="btn btn-maroon w-100" onclick="requestFood(${d.id})">Request Food</button>
          </div>
        </div>
      </div>
    `).join('');
  } catch (err) { /* ignore */ }
}

async function requestFood(donationId) {
  hideBoxes();
  try {
    await apiFetch('/api/donations/' + donationId + '/request', { method: 'POST' });
    showSuccessBox('Your request has been sent to the donor. You will be notified once it is accepted.');
    loadAvailableFood();
  } catch (err) {
    showErrorBox(err.message);
  }
}

async function loadReceiverHistory() {
  const tbody = document.getElementById('receiverHistoryBody');
  if (!tbody) return;
  try {
    const requests = await apiFetch('/api/receiver/requests');
    if (requests.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No requests yet.</td></tr>';
      return;
    }
    tbody.innerHTML = requests.map(r => `
      <tr>
        <td>${escapeHtml(r.food_name)}</td>
        <td>${escapeHtml(r.donor)}</td>
        <td>${escapeHtml(String(r.quantity))} ${escapeHtml(r.unit)}</td>
        <td>${escapeHtml(r.pickup_address)}</td>
        <td>${r.estimated_people_fed ? '~' + escapeHtml(String(r.estimated_people_fed)) : '—'}</td>
        <td><span class="status-badge status-${r.status}">${capitalize(r.status)}</span></td>
      </tr>
    `).join('');
  } catch (err) { /* ignore */ }
}

/* ---------------------------------------------------------
   7. VOLUNTEER: stats, available deliveries, history
--------------------------------------------------------- */
async function loadVolunteerStats() {
  try {
    const stats = await apiFetch('/api/volunteer/stats');
    setText('statAvailableDel', stats.available);
    setText('statActiveDel', stats.active);
    setText('statCompletedDel', stats.completed);
  } catch (err) { /* ignore */ }
}

async function loadAvailableDeliveries() {
  const container = document.getElementById('deliveryCardsContainer');
  if (!container) return;
  try {
    const deliveries = await apiFetch('/api/deliveries/available');
    if (deliveries.length === 0) {
      container.innerHTML = '<p class="text-center text-muted">No deliveries available right now. Please check back later.</p>';
      return;
    }
    container.innerHTML = deliveries.map(d => `
      <div class="col-md-6 col-lg-4 mb-4">
        <div class="food-card">
          <div class="food-card-header">
            <strong>${escapeHtml(d.food_name)}</strong>
            <span class="status-badge status-available">Available</span>
          </div>
          <div class="food-card-body">
            <ul>
              <li><strong>Pickup From:</strong> ${escapeHtml(d.pickup_location)}</li>
              <li><strong>Deliver To:</strong> ${escapeHtml(d.delivery_location)}</li>
              <li><strong>Quantity:</strong> ${escapeHtml(String(d.quantity))} ${escapeHtml(d.unit)}</li>
              <li><strong>Pickup Time:</strong> ${escapeHtml(d.pickup_time)}</li>
            </ul>
            <button class="btn btn-maroon w-100" onclick="acceptDelivery(${d.id})">Accept Delivery</button>
          </div>
        </div>
      </div>
    `).join('');
  } catch (err) { /* ignore */ }
}

async function acceptDelivery(deliveryId) {
  hideBoxes();
  try {
    await apiFetch('/api/deliveries/' + deliveryId + '/accept', { method: 'POST' });
    showSuccessBox('Delivery accepted successfully.');
    loadAvailableDeliveries();
  } catch (err) {
    showErrorBox(err.message);
  }
}

async function loadDeliveryHistory() {
  const tbody = document.getElementById('deliveryHistoryBody');
  if (!tbody) return;
  try {
    const deliveries = await apiFetch('/api/volunteer/deliveries');
    if (deliveries.length === 0) {
      tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">No deliveries yet.</td></tr>';
      return;
    }
    tbody.innerHTML = deliveries.map(d => `
      <tr>
        <td>${escapeHtml(d.food_name)}</td>
        <td>${escapeHtml(d.pickup_location)}</td>
        <td>${escapeHtml(d.delivery_location)}</td>
        <td>${escapeHtml(d.pickup_time)}</td>
        <td><span class="status-badge status-${d.status}">${capitalize(d.status)}</span></td>
      </tr>
    `).join('');
  } catch (err) { /* ignore */ }
}

/* ---------------------------------------------------------
   8. CONTACT FORM
--------------------------------------------------------- */
async function submitContactForm(event) {
  event.preventDefault();
  hideBoxes();
  const form = event.target;
  if (!validateRequired(form)) return;
  const emailInput = form.querySelector('input[type="email"]');
  if (emailInput && !validateEmail(emailInput)) return;

  const payload = {};
  new FormData(form).forEach((value, key) => { payload[key] = value; });

  try {
    await apiFetch('/api/contact', { method: 'POST', body: JSON.stringify(payload) });
    showSuccessBox();
    form.reset();
  } catch (err) {
    showErrorBox(err.message);
  }
}

/* ---------------------------------------------------------
   9. SMALL HELPERS
--------------------------------------------------------- */
function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

function capitalize(str) {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str == null ? '' : str;
  return div.innerHTML;
}
