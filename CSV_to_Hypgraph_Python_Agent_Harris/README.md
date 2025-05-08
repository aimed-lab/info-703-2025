# HypernestedX Streamlit Interface

A universal, interactive Streamlit app for building and exploring hypergraphs (and related network structures) using the **HypernestedX** Python library.

---

## 📋 Features

- **Dataset Upload & Preview**  
  – CSV, XLSX, XLS support  
  – Quick data summary (rows, columns, dtypes)

- **Flexible Node Definition**  
  – Pick one or more columns as node IDs  
  – Automatically collects every unique ID to prevent KeyErrors

- **Hyperedge Construction**  
  – **SimpleHyperedge**, **DirectedHyperedge**, **NodeDirectedHyperedge**, **NestingHyperedges**  
  – Pick any columns to define relationships  
  – Live preview of added edges

- **Dynamic Code Generator**  
  – Select from every public class/function in `hypernestedx`  
  – Generates ready-to-run Python snippet  
  – Downloadable `.py` file

- **In-App Hypergraph Preview**  
  – Builds the graph in memory  
  – Shows node & edge counts  
  – Displays small incidence/adjacency matrices (if ≤50×50)

- **Debugging Assistant**  
  – Paste your traceback  
  – Automatic suggestions for common errors (KeyError, ImportError, etc.)

---

## 🚀 Installation

1. **Clone or copy** this repository into your local folder.  
2. **Ensure** you have Python 3.7+ installed.  
3. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

   > **requirements.txt** should include:
   > ```text
   > streamlit>=1.0
   > pandas>=1.0
   > numpy>=1.18
   > openpyxl
   > ```

---

## 🏃‍♂️ Running the App

From your project root directory:

```bash
streamlit run app.py
```

This will open your default browser at `http://localhost:8501`, where you can:

1. Upload your dataset (CSV/Excel).  
2. Preview data & select columns for nodes and edges.  
3. Configure hyperedge type and features.  
4. Generate and download Python code snippet.  
5. Build & inspect your hypergraph on the fly.  
6. Paste any traceback into the Debugging Assistant for tailored tips.

---

## 🔧 Usage Tips

- **Multiple Node ID Columns**  
  You can combine several columns (e.g. “gene”, “drug_name”, “interaction_type”) so every unique value becomes a node.

- **Preventing KeyErrors**  
  The app collects all unique IDs before adding edges—no more “missing node” crashes.

- **Extending the Snippet**  
  The generated code includes placeholders for any other `hypernestedx` members you select. Simply fill in the “TODO” lines.

- **Large Graphs**  
  For very large incidence or adjacency matrices (>50×50), preview is disabled to keep UI responsive; you can still download and run the snippet locally.

---

## 🛠️ Troubleshooting

- **“KeyError: …”**  
  Ensure you selected all the columns that supply IDs to edges.  
  Tip: use “Select one or more columns to use as node identifiers” to include edge columns too.

- **Import Errors**  
  Verify that `hypernestedx.py` (or the `hypernestedx/` package) lives alongside `app.py`, and your `requirements.txt` is up to date.

- **Streamlit Port Conflicts**  
  If `localhost:8501` is in use, specify another port:
  ```bash
  streamlit run app.py --server.port 8502
  ```

---

## 📚 Further Reading

- **HypernestedX Documentation**: _link to your GitHub wiki or docs_  
- **Streamlit Guide**: https://docs.streamlit.io  
- **Pandas Tutorial**: https://pandas.pydata.org/docs/

---

## 🤝 Contributing

1. Fork the repo  
2. Create your feature branch (`git checkout -b feature/…`)  
3. Commit your changes (`git commit -m "…"`); keep your code style consistent  
4. Push to the branch (`git push origin feature/…`)  
5. Open a Pull Request—discuss your improvements!

---

> _Built with ❤️ using HypernestedX & Streamlit_