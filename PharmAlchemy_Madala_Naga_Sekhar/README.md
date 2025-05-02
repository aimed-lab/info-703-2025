This folder contains all scripts and documentation for the PharmAlchemy project by Madala Naga Sekhar.

# 🧪 PharmAlchemy: Metadata & Ontology Standardization for Enhanced Data Interoperability in PharmAlchemy
![image](https://github.com/user-attachments/assets/ac876802-4078-452d-aa3b-55f82a902b0a)


**Author**: Madala Naga Sekhar  
**Institution**: University of Alabama at Birmingham  
**Project Duration**: Spring 2025  
**Course**: INFO 703 – Biological Data Management

---

## 📌 Project Overview

**PharmAlchemy** is a data integration project focused on cleaning, standardizing, and linking biomedical data across four key public datasets:

- **DisGeNET** (gene–disease and drug–disease associations)
- **DrugBank** (drug–protein targets)
- **STRING** (gene–protein relationships)
- **SIDER** (drug side effects)

The goal is to enable **interoperable querying** across these datasets using a **unified ontology schema** to support **drug discovery and bioinformatics research**.

---


This repository contains the **cleaning, ontology mapping, and integration scripts** used for the *PharmAlchemy* project.

PharmAlchemy integrates biomedical datasets (DisGeNET, STRING, DrugBank, SIDER) into a standardized schema to enable unified gene–drug–disease–side effect exploration.

---

## 🧪 Scope of This Repository

- Python scripts for:
  - Cleaning DisGeNET disease and gene mappings
  - Mapping disease labels to DOID (using Human Disease Ontology)
  - Standardizing DrugBank drug-target relationships
  - Cleaning STRING gene-to-protein tables
  - Mapping side effects from SIDER
- All cleaned data outputs are available on [Zenodo](https://zenodo.org/) (DOI will be added after final upload)

---

## 🗂 Repository Structure
scripts/
├── clean_d2g_disgenet.py
├── clean_disgenet_diseases.py
├── clean_indications_disgenet.py
├── clean_drugbank_core.py
├── clean_drugbank_optional.py
├── clean_string_gene_table.py
├── map_doid_from_label.py



---

## 🛠 Technologies

- Python 3.10+
- Pandas
- Numpy
- CSV
- Local UMLS/MeSH/DOID mappings

---

## 🧾 License

This repository is shared under the [MIT License](LICENSE).

---

## 📦 Data Availability

Cleaned and standardized dataset outputs are available on Zenodo under DOI: **[pending Zenodo link]**

---



