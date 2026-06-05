# 🛡️ Data Quality Auditor — Enterprise Edition

**A powerful, glassmorphic web application for automated data quality assessment, anomaly detection, and intelligent data remediation.**

---

## 📋 Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Technology Stack](#technology-stack)
- [Architecture](#architecture)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage Guide](#usage-guide)
- [Project Structure](#project-structure)
- [Authentication](#authentication)
- [Quality Scoring](#quality-scoring)
- [Advanced Features](#advanced-features)
- [Screenshots](#screenshots)
- [Demo Video](#demo-video)
- [Bug Fixes & Improvements](#bug-fixes--improvements)
- [Contributing](#contributing)
- [License](#license)

---

## 🎯 Overview

**Data Quality Auditor** is an enterprise-grade solution for assessing, monitoring, and improving data quality across your datasets. It combines advanced statistical analysis, intelligent anomaly detection, and automated remediation to deliver actionable insights in real-time.

Whether you're a data engineer validating pipelines, a data analyst ensuring dataset integrity, or a business stakeholder maintaining data governance — this tool provides the insights you need to maintain high-quality data standards.

**Core Value Proposition:**
- ✅ **Instant Quality Score** (0–100) for any CSV dataset
- ✅ **Automated Anomaly Detection** — identifies duplicates, outliers, type mismatches, nulls
- ✅ **One-Click Data Cleaning** — apply fixes with a single button
- ✅ **Enterprise UI** — glassmorphic neon theme with smooth animations
- ✅ **Role-Based Access** — secure login with credential management

---

## ✨ Key Features

### 1. **Comprehensive Data Profiling**
- Per-column statistical analysis (min, max, mean, std, unique count)
- Missing value detection and percentage calculation
- Data type inference and validation
- Top values frequency distribution

### 2. **Advanced Quality Scoring**
- **Weighted Algorithm** balances 4 dimensions:
  - Completeness (30%) — missing values
  - Uniqueness (20%) — cardinality analysis
  - Consistency (30%) — type mismatches & anomalies
  - Outlier Rate (20%) — statistical outliers via IQR method
- Real-time score computation with gradient scale (Critical → Excellent)
- Per-column quality breakdown for granular insights

### 3. **Intelligent Anomaly Detection**
- **IQR-based Outlier Detection** — identifies statistical anomalies in numeric columns
- **Duplicate Row Detection** — flags and counts duplicate records
- **Type Mismatch Detection** — finds structural inconsistencies
- **Null Column Detection** — identifies completely empty columns
- **All-Zero Column Detection** — flags constant-value columns
- **Email & Date Validation** — regex-based format checking

### 4. **Automated Data Cleaning**
- **Smart Fix Suggestions** — contextual recommendations per column
- **Intelligent Imputation** — median for numeric, mode for categorical
- **Date Normalization** — ISO-8601 standardization
- **Outlier Clamping** — boundary-based numeric smoothing
- **Deduplication** — remove exact duplicate rows
- **Change Log** — track mutations and rows dropped

### 5. **Enterprise UI with Glassmorphism**
- **Neon Cyberpunk Theme** — cyan/purple accents on deep navy
- **Glass Effect Cards** — frosted transparency with backdrop blur
- **Responsive Dashboard** — 4-column metric layout
- **Interactive Gauge Chart** — animated quality score visualization
- **Smooth Animations** — hover effects, transitions, scanline overlay
- **Dark Mode Native** — zero eye strain, 24/7 usability

### 6. **Secure Authentication**
- Role-based login system
- Single-user credential management
- Session-based access control
- Graceful logout with state reset

---

## 🛠️ Technology Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Streamlit 1.28+, Plotly, HTML/CSS |
| **Backend** | Python 3.11+, Pandas, NumPy |
| **Data Processing** | Polars (fast CSV parsing), DuckDB (SQL anomalies) |
| **Styling** | CSS Glassmorphism, JetBrains Mono font |
| **Authentication** | SHA-256 hashing, Session state management |
| **Deployment** | Streamlit Cloud / Docker |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Streamlit App (app.py)            │
│          [Auth → Dashboard → Analysis]              │
└──────────────────┬──────────────────────────────────┘
                   │
        ┌──────────┼──────────┬──────────┐
        ▼          ▼          ▼          ▼
   ┌────────┐ ┌────────┐ ┌─────────┐ ┌──────────┐
   │ Core   │ │   UI   │ │ Utils   │ │ Security │
   ├────────┤ ├────────┤ ├─────────┤ ├──────────┤
   │Profiler│ │Sidebar │ │Cleaner  │ │Credentials
   │Scorer  │ │Dashboard │ │ │ Login   │
   │Detect. │ │Charts  │ │ │         │
   └────────┘ └────────┘ └─────────┘ └──────────┘
        │          │          │          │
        └──────────┼──────────┼──────────┘
                   │
        ┌──────────▼──────────┐
        │  Data Layer (CSV)   │
        │  Pandas / Polars    │
        └─────────────────────┘
```

### Module Breakdown

**`core/`** — Data processing engine
- `profiler.py` — statistical analysis, anomaly detection
- `scorer.py` — quality scoring algorithm, issue ranking

**`ui/`** — User interface components
- `login.py` — glassmorphic authentication form
- `sidebar.py` — file upload, settings panel
- `dashboard.py` — metrics, gauge, column table
- `charts.py` — plotly visualizations
- `report_card.py` — per-column deep-dive cards

**`utils/`** — Helper functions
- `cleaner.py` — fix suggestions, data remediation, export

**`credentials.py`** — User authentication

---

## 📦 Installation

### Prerequisites
- Python 3.11+
- pip or conda
- 500MB free disk space

### Step 1: Clone Repository
```bash
git clone https://github.com/Ali-datasmith/Data-Quality-Auditor.git
cd Data-Quality-Auditor
```

### Step 2: Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate     # Windows
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Create Missing Directories
```bash
mkdir -p .streamlit data
```

---

## 🚀 Quick Start

### 1. **Login**
- Username: `Ali-datasmith`
- Password: `Qx9#mK2$vL7@nR4!`

### 2. **Load Data**
- **Option A:** Upload your CSV (max 200MB)
- **Option B:** Click "Load Bundled Sample" for demo

### 3. **View Analysis**
- See overall quality score (0–100)
- Review per-column metrics in table
- Explore detected issues by severity
- Expand column cards for deep dives

### 4. **Clean Data**
- Click "EXECUTE ALL FIXES"
- Download cleaned CSV

### 5. **Logout**
- Click 🚪 LOGOUT in sidebar

---

## 📊 Usage Guide

### Quality Score Interpretation

| Score | Status | Action |
|-------|--------|--------|
| **90–100** | 🟢 Excellent | Production-ready |
| **70–89** | 🔵 Good | Monitor closely |
| **50–69** | 🟡 Fair | Schedule cleanup |
| **30–49** | 🟠 Poor | Urgent remediation |
| **0–29** | 🔴 Critical | Immediate action |

### Scoring Formula

```
Quality Score = 
  (30% × Completeness) +
  (20% × Uniqueness) +
  (30% × Consistency) +
  (20% × Outlier Rate) -
  (Duplicate Penalty)
```

**Per-Dimension Calculation:**
- **Completeness:** `100 - (missing% × 1.0)`
- **Uniqueness:** Context-aware (ID vs categorical)
- **Consistency:** `100 - (type_mismatch% × 2.5)`
- **Outlier Rate:** `100 - (outlier% × 3.0)`

### Issue Severity

| Severity | Threshold | Color |
|----------|-----------|-------|
| **Critical** | Score impact > 10pts | 🔴 Red |
| **High** | Score impact 5–10pts | 🟠 Orange |
| **Medium** | Score impact < 5pts | 🟡 Yellow |

---

## 📁 Project Structure

```
Data-Quality-Auditor/
├── app.py                      # Main Streamlit app
├── credentials.py              # User authentication
├── config.toml                 # Configuration (weights, thresholds)
├── requirements.txt            # Python dependencies
├── .streamlit/config.toml      # Streamlit theme config
│
├── core/                       # Data processing
│   ├── __init__.py
│   ├── profiler.py             # Statistical profiling
│   └── scorer.py               # Quality scoring engine
│
├── ui/                         # User interface
│   ├── __init__.py
│   ├── login.py                # Login form (glassmorphic)
│   ├── sidebar.py              # Upload panel
│   ├── dashboard.py            # Main metrics view
│   ├── charts.py               # Plotly visualizations
│   └── report_card.py          # Column detail cards
│
├── utils/                      # Utilities
│   ├── __init__.py
│   └── cleaner.py              # Data remediation
│
├── data/                       # Sample datasets
│   └── sample_messy.csv        # Demo data
│
└── README.md                   # This file
```

---

## 🔐 Authentication

### Credentials
- **Username:** `Ali-datasmith`
- **Password:** `Qx9#mK2$vL7@nR4!` (16-char strong password)

### How It Works
1. Hash-based validation using SHA-256
2. Session state management via Streamlit
3. Auto-logout on app restart
4. User badge in sidebar shows logged-in user

### For Production
Replace `credentials.py` with:
- Database-backed user store (PostgreSQL/MongoDB)
- `bcrypt` password hashing (not SHA-256)
- OAuth 2.0 / SAML integration
- Role-based access control (RBAC)

---

## 📈 Quality Scoring Deep Dive

### Completeness (30%)
Measures missing values — the percentage of NULL/NaN fields.
```
Completeness = 100 - (missing_count / total_rows) × 100
```

### Uniqueness (20%)
Context-aware: high uniqueness is good for IDs, bad for categories.
```
If numeric:
  - < 5% unique → 20 pts (likely all same)
  - 5–20% unique → 60 pts
  - > 20% unique → 85 pts (good spread)

If string:
  - > 95% unique → 65 pts (likely ID column)
  - 60–95% unique → 80 pts
  - 5–60% unique → 90 pts (good categorical)
  - < 5% unique → 20 pts (nearly constant)
```

### Consistency (30%)
Detects type mismatches, malformed dates, invalid emails.
```
Consistency = 100 - (mismatch_count / total_rows) × 250
```

### Outlier Rate (20%)
IQR method: flags values > Q75 + 1.5×IQR or < Q25 - 1.5×IQR.
```
Outlier Rate = 100 - (outlier_count / total_rows) × 300
Skipped for non-numeric & boolean columns
```

### Duplicate Penalty
Each duplicate row reduces score by `min(20pts, duplicate% × 0.5)`.

---

## 🚨 Advanced Features

### Anomaly Detection Methods

**1. IQR Outliers (Numeric)**
```
Q1 = 25th percentile
Q3 = 75th percentile
IQR = Q3 - Q1
Lower Fence = Q1 - 1.5 × IQR
Upper Fence = Q3 + 1.5 × IQR
```

**2. DuckDB SQL Queries**
- Null column detection
- All-zero column detection
- Email regex validation
- Date format validation
- Mixed numeric/text patterns

**3. Duplicate Detection**
- Row-level exact matching
- Configurable column subset

### Data Cleaning Pipeline

**Fix Priority:**
1. Deduplication (highest impact)
2. Missing value imputation
3. Type normalization
4. Outlier clamping
5. Date standardization

**Imputation Strategies:**
- Numeric: `median(column)`
- Categorical: `mode(column)`
- Dates: `pd.to_datetime()` with coerce

---

## 🎨 UI/UX Features

### Glassmorphism Design
- **Backdrop Filter:** `blur(20px) saturate(180%)`
- **Transparent Base:** `rgba(255,255,255,0.04)`
- **Border Glow:** Cyan (`#00FFFF`) with `0 0 20px radius`
- **Scanline Overlay:** Animated subtle line sweep

### Color Palette
| Element | Color | Usage |
|---------|-------|-------|
| Primary Accent | `#00FFFF` | Cyan glow, titles |
| Secondary | `#E0F7FA` | Body text |
| Success | `#2ECC71` | Green badges |
| Warning | `#F1C40F` | Yellow flags |
| Error | `#E74C3C` | Red alerts |
| Background | `#0A0E1A` | Deep navy base |

### Responsive Grid
- **4-Column Metrics** → 2-column on tablet → 1-column mobile
- **Sidebar Collapse** → auto on screens < 768px
- **Chart Reflow** → responsive Plotly configurations

---

## 🐛 Bug Fixes & Improvements

### v1.0 Release Fixes

| Issue | Root Cause | Solution |
|-------|----------|----------|
| **Duplicate TOML Keys** | Config had 2 theme blocks | Merged into single block |
| **REGEXP_MATCHES Silent Fail** | Old DuckDB syntax | Version-aware regex function selection |
| **String Column Outlier Bonus** | `is_numeric_dtype()` returned True for booleans | Added `is_bool_dtype()` exclusion |
| **Duplicate Rows No Penalty** | Duplicate detection worked but score ignored it | Wired `duplicate_count` into score formula |
| **NORMALIZE_DATE on All Columns** | `"object" in dtype` matched every string | Added date-name heuristic + sample parse |
| **Deprecated `infer_datetime_format`** | Pandas 2.2+ removed parameter | Removed param, pandas auto-infers |
| **Text Truncation in Cards** | Long labels overflow fixed width | Shortened labels (16→8 chars) |
| **Logout Button Delayed** | Rendered after `render_sidebar()` | Moved to sidebar rendering start |
| **Boolean Arithmetic Crash** | IQR calculation on booleans | Added boolean type check in outlier detection |
| **Invalid Plotly Property** | `hoverlabel` not on Indicator traces | Removed unsupported property |

---

## 📸 Screenshots

### Login Page
[<img width="1365" height="719" alt="Screenshot 2026-06-05 11 05 31 AM" src="https://github.com/user-attachments/assets/95e5c2a2-ff89-4b99-9850-f043a71a40b4" />
]

*Enterprise authentication with glassmorphic design, neon cyan accents, and secure credential validation.*

### Main Dashboard
[<img width="1365" height="726" alt="Screenshot 2026-06-05 11 07 25 AM" src="https://github.com/user-attachments/assets/5829f48b-c09c-413a-9e36-f38f5bd4ae5b" />
]

*Real-time quality score gauge, metric cards, and per-column breakdown with issue flags.*

---

## 🎥 Demo Video

Watch the full walkthrough:

[https://youtu.be/kGrs0EO9OjE]

*Loom video showing: Login → Data Upload → Quality Analysis → Issue Detection → Data Cleaning → Export*

---

## 🤝 Contributing

### Bug Reports
Found an issue? Open a GitHub issue with:
- Steps to reproduce
- Expected vs actual behavior
- Screenshots/logs
- Python & Streamlit versions

### Feature Requests
Suggest improvements via:
- GitHub Discussions
- Email: `rjptmhmmd@gmail.com`

### Development Setup
```bash
git clone https://github.com/Ali-datasmith/Data-Quality-Auditor.git
cd Data-Quality-Auditor
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

---

## 📋 Requirements

```txt
streamlit==1.28.1
pandas==2.2.0
polars==0.19.16
duckdb==0.9.1
numpy==1.24.3
plotly==5.18.0
```

---

## 📄 License

MIT License — See LICENSE file for details.

---

## 👨‍💼 About the Developer

**Ali Datasmith** — Full-stack data engineer & UI specialist

- 🔧 Built enterprise data quality solutions
- 🎨 Specialist in glassmorphic UI/UX design
- 📊 Expert in statistical analysis & anomaly detection
- 🚀 Passionate about making complex tools simple

**Contact:**
- GitHub: [@Ali-datasmith](https://github.com/Ali-datasmith)
- Email: rjptmhmmd@example.com

---

## 🙏 Acknowledgments

- **Streamlit** — for reactive web framework
- **Plotly** — for interactive visualizations
- **Pandas & DuckDB** — for data wrangling
- **JetBrains Mono** — for monospace typography

---

**⭐ If you find this useful, please star the repo!**

**Made with ❤️ for data engineers & analysts worldwide.**
