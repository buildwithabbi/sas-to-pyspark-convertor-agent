# ⚡ SAS to PySpark Converter AI Agent

A production-grade, modular AI Agent and toolkit designed to automatically parse, translate, and convert **SAS scripts (`.sas`)** and **SAS Enterprise Guide projects (`.egp`)** into clean, executable, and idiomatic **PySpark** code (Python scripts & Jupyter Notebooks).

---

## 🌟 Key Features

1. **Dual SAS & EGP Project Parsing**:
   - Parses `.sas` scripts into logical code blocks (DATA steps, `PROC SQL`, `PROC SORT`, `PROC TRANSPOSE`, `PROC FREQ`, `PROC SUMMARY`, `PROC MEANS`, `PROC IMPORT`, `PROC EXPORT`, `%LET`, Macros).
   - Unpacks `.egp` zip archives or unzipped project folders, parses `project.xml` process flows, extracts task nodes, resolves dependencies, and builds an execution DAG.

2. **Deterministic Rule Engine + AST Transpiler**:
   - Converts `PROC SQL` to PySpark SQL (`spark.sql(...)`) with dialect translations.
   - Maps SAS DATA Step logic (`WHERE`, `KEEP`, `DROP`, `IF-THEN`, variable assignments) to PySpark DataFrame transformations (`.filter()`, `.select()`, `.withColumn()`).
   - Converts `FIRST.var`, `LAST.var`, and `RETAIN` to PySpark `Window.partitionBy()` specifications.
   - Maps 20+ SAS functions (`SUBSTR`, `UPCASE`, `LOWCASE`, `STRIP`, `TODAY`, `COALESCE`, `ROUND`, `YEAR`, `MONTH`) to `pyspark.sql.functions as F`.

3. **Hybrid AI Agent (Gemini Powered)**:
   - Evaluates transpilation confidence scores.
   - Uses Google Gemini API (`gemini-2.5-flash`) as an intelligent fallback agent for complex, non-standard SAS DATA steps, intricate macros, or unsupported PROCs.
   - Runs `ast.parse()` python code validation on all generated output.

4. **Multi-Format Pipeline Output**:
   - Generates standalone, production-ready `.py` PySpark scripts formatted with `black`.
   - Generates interactive `.ipynb` Jupyter Notebooks with markdown step-by-step descriptions, original SAS references, and code cells.

5. **Rich CLI & DAG Inspector**:
   - Typer & Rich powered CLI tool with dashboard summary tables and colorized tree graphs of EGP process flows.

---

## 🚀 Quick Start

### 1. Setup Environment & Install Dependencies
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

### 2. Configure Gemini API Key (Optional for AI Fallback)
```bash
cp .env.example .env
# Edit .env and set your GEMINI_API_KEY
```

---

## 🛠️ Usage & Commands

### Convert a SAS script or EGP project file
```bash
# Convert a SAS script to both PySpark script and Jupyter Notebook
sas2pyspark convert path/to/script.sas --out ./output

# Convert an EGP project file (.egp)
sas2pyspark convert path/to/NetflixHistory43.egp --out ./output

# Convert only to PySpark script (.py) or Notebook (.ipynb)
sas2pyspark convert script.sas --format script
sas2pyspark convert project.egp --format notebook
```

### Inspect an EGP Project Flow DAG
```bash
sas2pyspark inspect path/to/NetflixHistory43.egp
```

---

## 📐 Architecture Overview

```
sas2pyspark/
├── cli.py                     # Typer & Rich CLI Commands
├── config.py                  # Pydantic Settings & API Config
├── models.py                  # Pydantic AST, DAG, Task Node models
├── parsers/
│   ├── egp_parser.py          # EGP (Zip/XML) flow extractor & DAG builder
│   ├── sas_parser.py          # SAS script parser & block tokenizer
│   └── sql_parser.py          # PROC SQL translator using sqlglot & Spark SQL
├── transpiler/
│   ├── data_step.py           # DATA step -> PySpark DataFrame transpiler
│   ├── procs.py               # PROC SORT, TRANSPOSE, FREQ, SUMMARY transpiler
│   ├── functions.py           # SAS function -> PySpark F.* mapper
│   └── macros.py              # Macro variable (%LET) resolution engine
├── agent/
│   ├── llm_agent.py           # Gemini AI Agent for complex logic & fallback
│   ├── prompts.py             # Transpilation system prompts
│   └── validator.py           # Python AST syntax validator
└── generator/
    ├── script_builder.py      # Assembles executable .py scripts
    └── notebook_builder.py    # Assembles interactive .ipynb notebooks
```

---

## 🧪 Testing

Run unit & integration test suite:
```bash
pytest -v
```
