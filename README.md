# 🇮🇳 National E-Voting Portal (Advanced Secure Voting System)

A state-of-the-art, secure electronic voting platform built to ensure the highest integrity of democratic elections. This system leverages advanced cryptographic techniques, AI-driven biometric verification, and real-time data streaming to provide a robust voting infrastructure.

---

## 🌟 Key Features (For Presentation)

### 1. 🔐 Cryptographic Blockchain Ledger
*   **Immutable Voting Records:** Every vote cast is secured using a **SHA-256 hashing algorithm**.
*   **Proof-of-Work (PoW):** A custom PoW mechanism guarantees that modifying a past vote requires recalculating the entire cryptographic chain, making the system virtually tamper-proof.
*   **Encrypted Payloads:** Voter choices and metadata are securely encrypted using **AES-256** before being attached to the blockchain.

### 2. 👁️ AI-Powered Biometric Authentication
*   **Face Recognition & Liveness Detection:** Utilizes deep learning to encode and verify the voter's facial structure in real-time, preventing spoofing attempts using photos or screens.
*   **Multi-Factor Authorization:** Combines traditional credentials (EPIC Number), Aadhaar verification, and live biometrics to ensure 100% voter authenticity.

### 3. 🛡️ Intelligent Fraud Detection Engine
*   **Behavioral Risk Scoring:** The `FraudEngine` calculates real-time risk scores based on multiple telemetry points:
    *   Geolocation anomalies
    *   Suspicious timing or rapid voting attempts
    *   Device fingerprinting and reuse
    *   Biometric mismatches
*   **Auto-Blocking Mechanism:** Any voter session that crosses the critical risk threshold (score $\ge$ 50) is automatically isolated, and an alert is dispatched to the Election Commission.

### 4. 📊 Real-Time Admin Dashboard
*   **Live Turnout Streaming:** Integrated **Flask-SocketIO** with WebSockets to push live analytics to the admin dashboard every 5 seconds.
*   **Centralized Security Logs:** Chief Electoral Officers can instantly monitor active fraud alerts, resolve issues, and view demographic voting metrics without ever refreshing the page.

---

## 🛠️ Technology Stack

*   **Backend Framework:** Python / Flask
*   **Database:** SQLite / SQLAlchemy ORM
*   **Real-time Communication:** WebSockets (Flask-SocketIO)
*   **Security & Encryption:** Cryptography (AES-256), Hashlib (SHA-256), Bcrypt (Password Hashing)
*   **Biometrics:** OpenCV / `face_recognition` library
*   **Frontend UI:** HTML5, Tailwind CSS, Jinja2 Templating, JavaScript

---

## 🚀 How to Run the Project Locally

1. **Install Dependencies:**
   Make sure you have Python installed, then install the required libraries:
   ```bash
   pip install flask flask-sqlalchemy flask-socketio flask-limiter flask-wtf cryptography bcrypt face_recognition opencv-python
   ```

2. **Launch the Portal:**
   Simply run the start script. This will automatically seed the database and launch the background web server on port 8080:
   ```bash
   python run.py
   ```

3. **Access the Application:**
   *   **Voter Portal:** [http://localhost:8080](http://localhost:8080)
   *   **Admin Dashboard:** [http://localhost:8080/admin/login](http://localhost:8080/admin/login)

### Demo Credentials
*   **Admin Access:** `admin` / `admin123`
*   **Sample Voter EPIC:** `ABC1234567` (Used for testing face registration and ballot access)

---

## 📈 System Architecture Workflow
1. **Registration:** Voter details + Face Encodings are saved.
2. **Authentication:** Voter logs in via EPIC -> Face Liveness Check -> Authorized.
3. **Ballot Access:** Voter selects a candidate.
4. **Blockchain Insertion:** Vote is AES encrypted $\rightarrow$ PoW Hash calculated $\rightarrow$ Chained to previous vote.
5. **Analytics Broadcast:** SocketIO detects the database change and updates the CEO dashboard instantly.