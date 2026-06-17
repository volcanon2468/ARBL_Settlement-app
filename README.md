# APSPDCL Open-Access Management Platform

An enterprise-grade, full-stack application designed to automatically process, calculate, and manage massive time-series energy block data. The platform aggregates raw interval data (15-minute slots), applies dynamic mathematical loss factors, constraints, and capacity limits, and ultimately produces precise financial and physical energy settlement reports across multiple consumers.

## 🚀 Key Features

* **Multi-Consumer Dynamic Allocation:** Natively calculates and splits generator output across multiple consumers (e.g., TPT145, CTR2005) using user-defined share percentages.
* **15-Minute Block Resolution:** Ingests and processes data precisely down to the individual 15-minute slot, handling up to 2,976 slots per 31-day month seamlessly.
* **Dynamic Energy Banking (FIFO):** Features a robust historical chronological bank ledger. Unused generator capacity is "Banked", while excess consumption triggers automated withdrawals from past unexpired banks using strict FIFO (First-In, First-Out) logic.
* **Custom Loss & Shutdown Engine:** 
  * **Shutdown Windows:** Users can input periods where the generator is offline.
  * **Custom Loss Windows:** Pure-date bounded logic automatically stretches the end-date to `23:59:59.999999` to natively calculate dynamic percentage energy losses without the user having to specify complex time inputs.
* **ISO vs Main Calculation Separation:** Implements the official Discom formula layer, calculating energy loss, bank injection, and accountability separately at the independent ISO point versus the Main grid point.
* **Automated Excel Verification:** Allows users to upload a finalized APSPDCL `check.xlsx` macro file to instantly diff and prove the platform's calculation accuracy to 0.00 margins against the standard.
* **Security & Resource Management:** Deep path-traversal sanitization during file uploads, and atomic `shutil.rmtree` garbage collection ensures zero disk bloat when re-calculating or deleting timeframes.
* **Advanced Recharts Visualizations:** A fully responsive Next.js frontend utilizing Recharts to dynamically overlay generation and consumption metrics for multiple consumers in real-time.

---

## 🏗️ Architecture & Tech Stack

The platform is strictly decoupled into a high-performance RESTful Backend and a modern React Frontend.

### Backend (Python 3.11)
* **Framework:** FastAPI (Asynchronous execution).
* **Database / ORM:** Microsoft SQL Server powered by SQLAlchemy 2.0 Asyncio engine (via `aioodbc`).
* **Data Processing:** Pandas (Used extensively for `.cdf` / `.xlsx` high-speed ingestion and vectorized manipulation).
* **Validation & Security:** Pydantic V2 for strict payload validation, and PyJWT with Passlib (Bcrypt) for stateless edge authentication.
* **Excel Generation:** Openpyxl dynamically writes and formats the final downloadable `.xlsx` settlement reports.
* **Strict Minimalist Codebase:** Following deployment requirements, the application source code is completely devoid of inline comments and docstrings.

### Frontend (TypeScript)
* **Framework:** Next.js 14 (App Router) with React 18.
* **Security:** Edge-Level Authentication via Next.js Middleware to intercept and decode JWT cookies natively at the edge.
* **UI & Styling:** TailwindCSS combined with `shadcn/ui` (Radix Primitives) and Lucide React icons.
* **Data Visualization:** Recharts (`LineChart` components with distinct solid and dashed stroke logic for multi-consumer mapping).
* **State & Notifications:** React Hooks and `sonner` for gorgeous, non-blocking asynchronous state toasts.

---

## ⚙️ The Settlement Mathematical Engine

At the core of the backend lies `SettlementEngine` (inside `backend/app/domain/settlement_engine.py`), a volatile memory processor that crunches over 3,000 blocks per execution in milliseconds.

### 1. Data Ingestion & Sanitization
The platform securely uploads and parses:
* **Generator Files (`.cdf`):** Extracts `Active_KW` per slot.
* **Consumer/IEX Files (`.cdf` & `.xlsx`):** Extracts `Apparent_KVA`, `Active_KW_Raw`, and `IEX_KW` per slot.

### 2. Block Logic Execution
For every 15-minute slot (1 to 96) for every day in the month:
1. **Shutdown Check:** If the slot falls inside a `ShutdownWindow`, Generation is instantly hard-forced to `0.0`.
2. **Cap Generation:** Generator output is hard-capped to the Contracted Capacity constraint.
3. **Loss Deduction:** The slot is checked against `CustomLossWindows` to apply dynamic `Loss_Pct`.
4. **Share Split:** The remaining Generation is mathematically divided between Consumer 1 and Consumer 2 based on `Share_Cons1` and `Share_Cons2`.
5. **Gross-Up Banking:** Excess generator power is mathematically injected into the Bank and grossed-up using a reverse-loss algorithm to perfectly represent the accountable KWH entry value.

### 3. Chronological Bank Processing
When the monthly total Generation exceeds Consumption, the remainder is pushed to the SQL `Banked_Added_KWH`. 
Conversely, if Consumption exceeds Generation, the Engine queries the database for all available past banks. It dynamically sorts them chronologically (`Year * 12 + Month`), gracefully iterating and deducting units across multiple historical timeframes until the deficit is filled or the banks are depleted.

---

## 📁 Directory Structure

```text
settlement-app2/
├── backend/
│   ├── alembic/              # Database migration logic
│   ├── app/
│   │   ├── adapters/         # API Routes and CDF/XLSX Parsers
│   │   ├── api/              # Authentication Routes
│   │   ├── core/             # Security Configurations
│   │   ├── domain/           # The core SettlementEngine Python logic
│   │   ├── infrastructure/   # SQLAlchemy Database and Models
│   │   └── use_cases/        # File Uploading and Calculation Scripts
│   ├── uploads/              # Local storage for .cdf and .xlsx files (garbage collected)
│   └── requirements.txt      # Python dependencies
└── frontend/
    ├── src/
    │   ├── app/              # Next.js 14 App Router pages (layout, settlement, etc)
    │   ├── components/       # shadcn UI components (buttons, cards, inputs)
    │   └── lib/              # Tailwind utility functions
    ├── tailwind.config.ts    # CSS Configuration
    └── package.json          # Node.js dependencies
```

---

## 🛠️ Installation & Setup

### 1. Database Setup
The application connects natively to a local Microsoft SQL Server instance (`.\SQLEXPRESS`). Ensure the **ODBC Driver 17 for SQL Server** is installed, and execute `CREATE DATABASE energy_settlement2;` via SSMS.

### 2. Backend Setup (FastAPI)
Open a terminal in the `backend` folder:
```bash
# 1. Create a virtual environment
python -m venv venv

# 2. Activate the virtual environment
# Windows:
.\venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Boot the server
uvicorn app.main:app --reload
```
The API will run locally at `http://localhost:8000`.

### 3. Frontend Setup (Next.js)
Open a new terminal in the `frontend` folder:
```bash
# 1. Install Node dependencies
npm install

# 2. Start the development server
npm run dev
```
The User Interface will run locally at `http://localhost:3000`.

**Default System Access:**
* Username: `admin`
* Password: `admin123`

---

## 📖 Usage Workflow

1. **Create Timeframe:** Navigate to the Settlement dashboard and click "Create New Month". Enter the exact Month and Year.
2. **Upload Raw Data:** Click "Inputs". Upload your `.cdf` generation file and consumption files. Wait for the green "COMPLETED" checkmarks.
3. **Configure Variables:** Enter the Share percentages (e.g., 60% / 40%), Cap Limits, Bank Loss parameters, and any specific Generator Shutdowns or Custom Loss Dates. Click Save.
4. **Run Calculation:** Click the "Run Final Calculation" button. The engine will read the DB, process the 96 slots, apply the bank ledger FIFO, and save the results.
5. **View Report:** The system will immediately redirect you to the Report Page. Here you can view the final `Discom_KVAH` billing, visualize both consumers on the Recharts line graph, Verify against the Official Excel File, and download the full Excel Workbook containing every single calculated block.
