// Simple SPA section toggle
function showSection(id) {
  document.querySelectorAll('main section').forEach(sec => sec.style.display = 'none');
  const el = document.getElementById(id);
  if (el) el.style.display = 'block';
}
let currentEditingMember = null;
let plansCache = [];

function openEditModal(member) {
  currentEditingMember = member;
  document.getElementById('editName').value = member.name;
  document.getElementById('editJoinDate').value = member.join_date;
  populateEditPlans(member.plan_code);
  document.getElementById('editModal').classList.remove('hidden');
}
function closeEditModal() {
  currentEditingMember = null;
  document.getElementById('editModal').classList.add('hidden');
}
async function populateEditPlans(selectedCode) {
  const plans = await (await fetch('/api/plans')).json();
  const sel = document.getElementById('editPlan');
  sel.innerHTML = '';
  plans.forEach(p => {
    const opt = document.createElement('option');
    opt.value = p.code;
    opt.textContent = `${p.label} - ₹${p.price}`;
    if (p.code === (selectedCode || '')) opt.selected = true;
    sel.appendChild(opt);
  });
}
function showToast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.remove('hidden');
  setTimeout(() => t.classList.add('hidden'), 1800);
}

document.addEventListener('DOMContentLoaded', async () => {
  // Nav clicks
  document.querySelectorAll('nav button[data-section]').forEach(btn => {
    btn.addEventListener('click', () => showSection(btn.dataset.section));
  });

  // Modal buttons
  document.getElementById('btnCancelEdit').addEventListener('click', closeEditModal);
  document.getElementById('btnCloseEdit').addEventListener('click', closeEditModal);
  document.getElementById('btnSaveEdit').addEventListener('click', async () => {
    if (!currentEditingMember) return;
    const name = document.getElementById('editName').value.trim();
    const join_date = document.getElementById('editJoinDate').value;
    const plan_code = document.getElementById('editPlan').value;
    if (!name || !join_date || !plan_code) { showToast('Please fill all fields'); return; }
    const res = await fetch(`/api/members/${currentEditingMember.id}`, {
      method: 'PATCH', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ name, join_date, plan_code })
    });
    const data = await res.json();
    if (!data.ok) { showToast(data.error || 'Update failed'); return; }
    closeEditModal();
    await refreshMembers();
    await refreshSmart();
    showToast('Member updated');
  });

  // Auto-fill billing amount when a plan is selected
  const billPlanSel = document.getElementById('billPlan');
  if (billPlanSel) {
    billPlanSel.addEventListener('change', () => {
      const code = billPlanSel.value;
      const amtInput = document.getElementById('billAmount');
      if (!code) return;
      const plan = plansCache.find(p => p.code === code);
      if (plan) amtInput.value = plan.price;
    });
  }

  // Initial loads
  await refreshPlansSelect();
  await refreshPlansTable();
  await refreshMembers();
  await refreshTrainers();
  await refreshBilling();
  await refreshSmart();

  // Members: add/remove
  document.getElementById('btnAddMember').addEventListener('click', async () => {
    const name = document.getElementById('memberName').value.trim();
    const joinDate = document.getElementById('memberJoinDate').value;
    const planCode = document.getElementById('memberPlan').value;
    if (!name || !joinDate || !planCode) return alert('Please fill all member fields.');
    const res = await fetch('/api/members', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ name, join_date: joinDate, plan_code: planCode })
    });
    const data = await res.json();
    if (!data.ok) return alert(data.error || 'Failed to add member');
    document.getElementById('memberName').value = '';
    document.getElementById('memberJoinDate').value = '';
    document.getElementById('memberPlan').selectedIndex = 0;
    await refreshMembers();
    await refreshSmart();
  });

  document.getElementById('btnRemoveMember').addEventListener('click', async () => {
    const id = prompt('Enter Member ID to remove:');
    if (!id) return;
    await fetch(`/api/members/${id}`, { method: 'DELETE' });
    await refreshMembers();
    await refreshSmart();
  });

  // Trainers: add/remove
  document.getElementById('btnAddTrainer').addEventListener('click', async () => {
    const name = document.getElementById('trainerName').value.trim();
    const specialization = document.getElementById('trainerSpec').value.trim();
    const salary = document.getElementById('trainerSalary').value;
    if (!name) return alert('Trainer name is required');
    const res = await fetch('/api/trainers', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ name, specialization, salary: Number(salary || 0) })
    });
    const data = await res.json();
    if (!data.ok) return alert(data.error || 'Failed to add trainer');
    document.getElementById('trainerName').value = '';
    document.getElementById('trainerSpec').value = '';
    document.getElementById('trainerSalary').value = '';
    await refreshTrainers();
  });

  document.getElementById('btnRemoveTrainer').addEventListener('click', async () => {
    const id = prompt('Enter Trainer ID to remove:');
    if (!id) return;
    await fetch(`/api/trainers/${id}`, { method: 'DELETE' });
    await refreshTrainers();
  });

  // Billing: add
  document.getElementById('btnGenerateBill').addEventListener('click', async () => {
    const memberName = document.getElementById('billMemberName').value.trim();
    const datePaid = document.getElementById('billDate').value;
    const planCode = document.getElementById('billPlan').value;
    let amount = document.getElementById('billAmount').value;

    if (!memberName || !datePaid) { alert('Please fill member name and payment date'); return; }

    const members = await (await fetch('/api/members')).json();
    const found = members.find(m => m.name.toLowerCase() === memberName.toLowerCase());
    if (!found) { alert('Member not found'); return; }

    if ((!amount || Number(amount) <= 0) && planCode) {
      const plan = plansCache.find(p => p.code === planCode);
      if (plan) amount = plan.price;
    }
    if (!amount || Number(amount) <= 0) { alert('Please provide a valid amount or select a plan'); return; }

    const res = await fetch('/api/billing', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ member_id: found.id, amount: Number(amount), date_paid: datePaid })
    });
    const data = await res.json();
    if (!data.ok) { alert(data.error || 'Failed to create bill'); return; }

    document.getElementById('billMemberName').value = '';
    document.getElementById('billDate').value = '';
    document.getElementById('billPlan').selectedIndex = 0;
    document.getElementById('billAmount').value = '';
    await refreshBilling();
  });
});

// --------- Helpers ---------
async function refreshPlansSelect() {
  const plans = await (await fetch('/api/plans')).json();
  plansCache = plans;

  const memberSel = document.getElementById('memberPlan');
  if (memberSel) {
    memberSel.innerHTML = '';
    plans.forEach(p => {
      const opt = document.createElement('option');
      opt.value = p.code;
      opt.textContent = `${p.label} - ₹${p.price}`;
      memberSel.appendChild(opt);
    });
  }
  const editSel = document.getElementById('editPlan');
  if (editSel) {
    editSel.innerHTML = '';
    plans.forEach(p => {
      const opt = document.createElement('option');
      opt.value = p.code;
      opt.textContent = `${p.label} - ₹${p.price}`;
      editSel.appendChild(opt);
    });
  }
  const billSel = document.getElementById('billPlan');
  if (billSel) {
    billSel.innerHTML = '';
    const blank = document.createElement('option');
    blank.value = '';
    blank.textContent = 'Select a plan (optional)';
    billSel.appendChild(blank);
    plans.forEach(p => {
      const opt = document.createElement('option');
      opt.value = p.code;
      opt.textContent = `${p.label} - ₹${p.price}`;
      billSel.appendChild(opt);
    });
  }
}

async function refreshMembers() {
  const tbody = document.querySelector('#memberTable tbody');
  tbody.innerHTML = '';
  const members = await (await fetch('/api/members')).json();
  members.forEach(m => {
    const tr = document.createElement('tr');
    const editBtn = document.createElement('button');
    editBtn.className = 'action-btn';
    editBtn.textContent = 'Edit';
    editBtn.addEventListener('click', () => openEditModal(m));
    tr.innerHTML = `
      <td>${m.id}</td>
      <td>${m.name}</td>
      <td>${m.plan_label}</td>
      <td>${formatDate(m.join_date)}</td>
      <td>${formatDate(m.end_date)}</td>
    `;
    const actionTd = document.createElement('td');
    actionTd.appendChild(editBtn);
    tr.appendChild(actionTd);
    tbody.appendChild(tr);
  });
}

async function refreshTrainers() {
  const tbody = document.querySelector('#trainerTable tbody');
  tbody.innerHTML = '';
  const trainers = await (await fetch('/api/trainers')).json();
  trainers.forEach(t => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${t.id}</td>
      <td>${t.name}</td>
      <td>${t.specialization || '-'}</td>
      <td>₹${t.salary || 0}</td>
    `;
    tbody.appendChild(tr);
  });
}

async function refreshBilling() {
  const tbody = document.querySelector('#billingTable tbody');
  tbody.innerHTML = '';
  const bills = await (await fetch('/api/billing')).json();
  bills.forEach(b => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${b.id}</td>
      <td>${b.member_name}</td>
      <td>₹${b.amount}</td>
      <td>${formatDate(b.date_paid)}</td>
    `;
    tbody.appendChild(tr);
  });
}

async function refreshSmart() {
  const tbody = document.querySelector('#smartTable tbody');
  tbody.innerHTML = '';
  const expiring = await (await fetch('/api/smart-expiring?days=5')).json();
  expiring.forEach(e => {
    const tr = document.createElement('tr');
    const btn = document.createElement('button');
    btn.className = 'action-btn';
    btn.textContent = 'Mark Paid';
    btn.addEventListener('click', async () => {
      const res = await fetch(`/api/members/${e.id}/renew`, {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ create_bill: true })
      });
      const data = await res.json();
      if (!data.ok) return alert(data.error || 'Failed to mark paid');
      await refreshBilling();
      await refreshMembers();
      await refreshSmart();
      alert(`Renewed. New end date: ${formatDate(data.new_end_date)}`);
    });
    const tdAction = document.createElement('td'); tdAction.appendChild(btn);
    tr.innerHTML = `
      <td>${e.id}</td>
      <td>${e.name}</td>
      <td>${formatDate(e.end_date)}</td>
      <td>Pending Payment</td>
    `;
    tr.appendChild(tdAction);
    tbody.appendChild(tr);
  });
}

function formatDate(iso) {
  if (!iso) return '-';
  const d = new Date(iso);
  const day = d.getDate().toString().padStart(2, '0');
  const mon = d.toLocaleString('en-GB', { month: 'short' });
  const yr = d.getFullYear();
  return `${day}-${mon}-${yr}`;
}

// Plans table (read-only)
async function refreshPlansTable() {
  const tbody = document.querySelector('#plansTable tbody');
  if (!tbody) return;
  tbody.innerHTML = '';
  const plans = await (await fetch('/api/plans')).json();
  plans.sort((a, b) => (a.duration_months - b.duration_months) || a.label.localeCompare(b.label));
  plans.forEach(p => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${p.label}</td>
      <td>${p.duration_months} Month${p.duration_months > 1 ? 's' : ''}</td>
      <td>${p.price}</td>
    `;
    tbody.appendChild(tr);
  });
}
