# 🏋️ Gym Management System

A **full-stack Gym Management System** developed as my **first complete web development project**, integrating frontend technologies with a database-driven backend to manage real-world gym operations efficiently.

This project demonstrates practical use of **HTML, CSS, JavaScript, Python (Flask), and SQLite** in a single cohesive application.

---

## 📌 Project Overview

The Gym Management System is a **local web application** designed for gym administrators to manage members, trainers, plans, billing, and membership expiry reminders from a single dashboard.

The system follows a **single-page application (SPA) approach**, ensuring smooth user interaction without page reloads.

---

## 🧰 Tech Stack

### Frontend
- **HTML5** – Structure of the dashboard and forms  
- **CSS3** – Styling, layout, and professional UI design  
- **JavaScript (Vanilla JS)** – Dynamic UI updates and API communication  

### Backend
- **Python (Flask)** – REST API, routing, and business logic  

### Database
- **SQLite** – Relational database for persistent data storage  

---

## ✨ Features

### 👤 Member Management
- Add, edit, and remove gym members  
- Automatically calculate membership end dates  
- Display members in a structured table  

### 📦 Plans & Packages
- Centralized membership plans  
- Plans reused across members and billing  
- Dynamic plan selection across the application  

### 🏋️ Trainer Management
- Add and remove trainers  
- Maintain specialization and salary details  

### 💳 Billing System
- Generate bills using **Member ID**  
- Auto-fetch **Member Name** to avoid ambiguity  
- Maintain billing history with payment dates  

### ⚡ Smart Expiry Reminder
- Identifies members whose plans expire within a defined period  
- One-click **“Mark Paid”** option renews membership and generates billing  

### 🔄 Single Page Dashboard
- Section-based navigation  
- No page reloads  
- Real-time updates using JavaScript and Fetch API  

---

## 🗄️ Database Structure

Tables used in the system:
- `plans` – Membership plans and pricing  
- `members` – Member details and plan mapping  
- `trainers` – Trainer information  
- `billing` – Payment records with member ID and name  

Key database concepts applied:
- Foreign keys  
- Normalized schema  
- Derived attributes (membership end date)  
- Server-side validation  

---

## ▶️ How to Run Locally

### 1️⃣ Clone the repository
```bash
git clone https://github.com/anshjw/gym.git
cd gym
