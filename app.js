
const API_BASE = window.location.origin + "/api";

document.addEventListener("DOMContentLoaded", () => {
    setupEmployeeForm();
    setupShiftForm();
    setupWeekLoader();
    loadEmployees().then(() => {
        const today = new Date().toISOString().slice(0, 10);
        document.getElementById("week-date").value = today;
        loadWeekSchedule(today);
    });
});

async function loadEmployees() {
    try {
        const res = await fetch(API_BASE + "/employees/");
        if (!res.ok) throw new Error("Çalışan listesi alınamadı");
        const data = await res.json();
        renderEmployeeList(data);
        fillEmployeeSelect(data);
    } catch (err) {
        alert(err.message);
    }
}

function renderEmployeeList(employees) {
    const ul = document.getElementById("employee-list");
    ul.innerHTML = "";
    employees.forEach(emp => {
        const li = document.createElement("li");
        li.textContent = emp.full_name + " – " + emp.role;
        ul.appendChild(li);
    });
}

function fillEmployeeSelect(employees) {
    const select = document.getElementById("shift-employee");
    select.innerHTML = '<option value="">- Seçilmedi -</option>';
    employees.forEach(emp => {
        const opt = document.createElement("option");
        opt.value = emp.id;
        opt.textContent = emp.full_name + " (" + emp.role + ")";
        select.appendChild(opt);
    });
}

function setupEmployeeForm() {
    const form = document.getElementById("employee-form");
    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const payload = {
            full_name: document.getElementById("emp-name").value.trim(),
            role: document.getElementById("emp-role").value.trim(),
            phone: document.getElementById("emp-phone").value.trim() || null,
            hourly_rate: document.getElementById("emp-rate").value ? Number(document.getElementById("emp-rate").value) : null,
            is_active: true
        };
        if (!payload.full_name || !payload.role) {
            alert("Ad soyad ve rol zorunludur.");
            return;
        }
        try {
            const res = await fetch(API_BASE + "/employees/", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            if (!res.ok) throw new Error("Çalışan eklenemedi");
            form.reset();
            await loadEmployees();
        } catch (err) {
            alert(err.message);
        }
    });
}

function setupShiftForm() {
    const form = document.getElementById("shift-form");
    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const dateVal = document.getElementById("shift-date").value;
        const start = document.getElementById("shift-start").value;
        const end = document.getElementById("shift-end").value;
        const position = document.getElementById("shift-position").value.trim();
        const empId = document.getElementById("shift-employee").value;

        if (!dateVal || !start || !end || !position) {
            alert("Tarih, saatler ve pozisyon zorunludur.");
            return;
        }

        const payload = {
            date: dateVal,
            start_time: start,
            end_time: end,
            position,
            employee_id: empId ? Number(empId) : null
        };

        try {
            const res = await fetch(API_BASE + "/shifts/", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            if (!res.ok) throw new Error("Vardiya kaydedilemedi");
            form.reset();
            const weekDate = document.getElementById("week-date").value || dateVal;
            document.getElementById("week-date").value = weekDate;
            await loadWeekSchedule(weekDate);
        } catch (err) {
            alert(err.message);
        }
    });
}

function setupWeekLoader() {
    const btn = document.getElementById("load-week-btn");
    btn.addEventListener("click", async () => {
        const val = document.getElementById("week-date").value;
        if (!val) {
            alert("Lütfen bir tarih seç.");
            return;
        }
        await loadWeekSchedule(val);
    });
}

async function loadWeekSchedule(anyDate) {
    try {
        const res = await fetch(API_BASE + "/schedule/week/?any_date_in_week=" + anyDate);
        if (!res.ok) throw new Error("Haftalık program alınamadı");
        const shifts = await res.json();
        renderWeekTable(shifts);
    } catch (err) {
        alert(err.message);
    }
}

function renderWeekTable(shifts) {
    const container = document.getElementById("schedule-table-container");
    container.innerHTML = "";

    if (!shifts.length) {
        container.textContent = "Bu hafta için kayıtlı vardiya yok.";
        return;
    }

    const byEmployee = {};
    const datesSet = new Set();

    shifts.forEach(s => {
        const empName = s.employee ? s.employee.full_name : "(Açık shift)";
        if (!byEmployee[empName]) byEmployee[empName] = {};
        byEmployee[empName][s.date] = byEmployee[empName][s.date] || [];
        byEmployee[empName][s.date].push(s);
        datesSet.add(s.date);
    });

    const dates = Array.from(datesSet).sort();

    const table = document.createElement("table");
    table.className = "schedule";

    const thead = document.createElement("thead");
    const headRow = document.createElement("tr");
    const thEmp = document.createElement("th");
    thEmp.textContent = "Çalışan";
    headRow.appendChild(thEmp);

    dates.forEach(d => {
        const th = document.createElement("th");
        th.textContent = d;
        headRow.appendChild(th);
    });
    thead.appendChild(headRow);
    table.appendChild(thead);

    const tbody = document.createElement("tbody");
    Object.entries(byEmployee).forEach(([empName, shiftsByDate]) => {
        const tr = document.createElement("tr");
        const tdEmp = document.createElement("td");
        tdEmp.textContent = empName;
        tr.appendChild(tdEmp);

        dates.forEach(d => {
            const td = document.createElement("td");
            const list = shiftsByDate[d] || [];
            list.forEach(s => {
                const span = document.createElement("span");
                span.className = "shift";
                span.textContent = `${s.start_time} - ${s.end_time} (${s.position})`;
                td.appendChild(span);
            });
            tr.appendChild(td);
        });

        tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    container.appendChild(table);
}
