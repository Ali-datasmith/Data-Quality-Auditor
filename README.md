# 🛡️ Enterprise Data Quality Auditor

[![Build Status](https://github.com/Ali-datasmith/Data-Quality-Auditor/actions/workflows/ci.yml/badge.svg)](https://github.com/Ali-datasmith/Data-Quality-Auditor/actions/workflows/ci.yml)
[![CodeQL Security Analysis](https://github.com/Ali-datasmith/Data-Quality-Auditor/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Ali-datasmith/Data-Quality-Auditor/actions/workflows/ci.yml)
[![Python Version](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/)
[![Polars Engine](https://img.shields.io/badge/engine-Polars%20Lazy-FFD43B.svg)](https://pypolars.org/)
[![Streamlit Cloud](https://img.shields.io/badge/Streamlit%20Cloud-Live%20Demo-FF4B4B.svg)](https://streamlit.io/)

An enterprise-grade B2B Streamlit web application engineered for real-time automated data quality audits, anomaly detection, statistical profiling, and automated remediation pipelines. Powered by modern Python 3.12+ tooling, zero-copy Polars lazy execution, DuckDB SQL pattern checks, and Argon2 security authentication.

---

## 🌟 Key Architecture & Highlights

* **⚡ Zero-Copy High-Performance Engine:** Built entirely on **Polars Lazy Evaluation** (`pl.scan_csv`, `pl.LazyFrame`, `.lazy()`) to eliminate memory bottlenecks and support streaming pipeline execution.
* **🔐 Enterprise Argon2 Authentication:** Hashing and credential validation powered by `argon2-cffi` (`Argon2id`), featuring a dedicated **1-Click Recruiter Demo Bypass** for friction-free evaluation.
* **📊 Multi-Dimensional Quality Scoring (0–100):** Weighted algorithmic scoring model assessing:
  * **Completeness:** Null/missing ratio calculations.
  * **Uniqueness:** Categorical vs identifier cardinality analysis.
  * **Type Consistency:** DuckDB-powered pattern recognition (regex emails, timestamps, string/numeric mismatches).
  * **Outlier Rate:** IQR fence boundary statistical variance checks (excludes non-numeric/boolean types).
  * **Duplicate Penalties:** Multi-column index duplicity tracking.
* **🛠️ Automated Remediation Pipeline:** 1-Click execution of data cleaning routines (median/mode imputation, IQR outlier clamping, deduplication) with change-log tracking and streaming CSV exports (`sink_csv`).
* **🛡️ Zero-Defect Quality Gates:** Fully type-hinted under Python 3.12+ typing standards, verified with `mypy` strict modes, linted via `ruff`, and tested with `pytest`.

---

## 🏛️ System Architecture Workflow

```
┌─────────────────────────┐
│     User CSV Stream     │
└────────────┬────────────┘
             │ (pl.scan_csv / Lazy Processing)
             ▼
┌─────────────────────────┐      ┌──────────────────────────┐
│  Polars Profiling Engine │ ───► │ DuckDB SQL Anomaly Check │
└────────────┬────────────┘      └────────────┬─────────────┘
             │                                │
             └────────────────┬───────────────┘
                              │
                              ▼
               ┌─────────────────────────────┐
               │  Multi-Dimensional Scorer    │
               │ (0-100 Quality Index Model) │
               └──────────────┬──────────────┘
                              │
                              ▼
               ┌─────────────────────────────┐
               │ Streamlit Glassmorphic UI   │
               │  & Auto-Remediation Engine  │
               └─────────────────────────────┘
```

---

## 🚀 Quick Start & Local Setup

### Prerequisites
* Python 3.12 or higher
* Git

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Ali-datasmith/Data-Quality-Auditor.git
   cd Data-Quality-Auditor
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install production & development dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install ruff mypy pytest argon2-cffi
   ```

4. **Launch the Streamlit App:**
   ```bash
   streamlit run app.py
   ```

---

## 🧪 Testing & Quality Assurance

Run the automated test suite and static type analysis locally:

```bash
# Run pytest suite
python -m pytest

# Run Ruff linter
ruff check .

# Run Mypy static type checker
mypy --ignore-missing-imports app.py credentials.py core/ utils/ ui/ tests/
```

---

## ☁️ Streamlit Community Cloud Deployment

This repository is optimized for deployment on **Streamlit Community Cloud**:
1. Fork or push this repository to GitHub.
2. Connect your repository to Streamlit Community Cloud.
3. Set the main file path to `app.py`.
4. Deploy! All dependencies are specified in `requirements.txt`.

---

## 📄 License & Credits

Developed by **Ali Datasmith**. Enterprise B2B Streamlit Data Quality Architecture.
