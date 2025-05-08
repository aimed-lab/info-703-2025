import csv
import tkinter as tk
from tkinter import ttk
import threading
from difflib import SequenceMatcher

# ----------------------------
# Loader for Gene Data (g_final.csv)
# ----------------------------
def load_candidates_from_csv(csv_filename):
    candidate_data = []
    indexes = {}
    gene_index = {}
    synonym_index = {}
    with open(csv_filename, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            gene_symbol = row.get('GENE_SYMBOL', '').strip()
            if not gene_symbol:
                continue
            synonyms_raw = row.get('GENE_SYNONYMS', '').strip()
            synonyms = [s.strip() for s in synonyms_raw.split("|")] if synonyms_raw else []
            entry = {
                'Canonical Gene Name': gene_symbol,
                'GENE_NAME': row.get('GENE_NAME', '').strip(),
                'Gene Synonyms': synonyms,
                'UNIPROT_ID': row.get('UNIPROT_ID', '').strip(),
            }
            candidate_data.append(entry)
            gene_index[gene_symbol.lower()] = entry
            for synonym in synonyms:
                synonym_index[synonym.lower()] = entry
    indexes["Canonical Gene Name"] = gene_index
    indexes["Gene Synonyms"] = synonym_index
    uniprot_index = {}
    for entry in candidate_data:
        uniprot = entry.get("UNIPROT_ID", "").strip().lower()
        if uniprot:
            uniprot_index[uniprot] = entry
    indexes["UNIPROT_ID"] = uniprot_index
    return candidate_data, indexes

# ----------------------------
# Loader for Drug Data (DrugBank Structure Links.csv)
# ----------------------------
def load_drug_data(csv_filename):
    candidate_data = []
    indexes = {}
    name_index = {}
    het_index = {}
    formula_index = {}
    with open(csv_filename, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            entry = {
                "DrugBank ID": row.get("DrugBank ID", "").strip(),
                "Name": row.get("Name", "").strip(),
                "CAS Number": row.get("CAS Number", "").strip(),
                "Drug Groups": row.get("Drug Groups", "").strip(),
                "InChIKey": row.get("InChIKey", "").strip(),
                "InChI": row.get("InChI", "").strip(),
                "SMILES": row.get("SMILES", "").strip(),
                "Formula": row.get("Formula", "").strip(),
                "KEGG Compound ID": row.get("KEGG Compound ID", "").strip(),
                "KEGG Drug ID": row.get("KEGG Drug ID", "").strip(),
                "PubChem Compound ID": row.get("PubChem Compound ID", "").strip(),
                "PubChem Substance ID": row.get("PubChem Substance ID", "").strip(),
                "ChEBI ID": row.get("ChEBI ID", "").strip(),
                "ChEMBL ID": row.get("ChEMBL ID", "").strip(),
                "HET ID": row.get("HET ID", "").strip(),
                "ChemSpider ID": row.get("ChemSpider ID", "").strip(),
                "BindingDB ID": row.get("BindingDB ID", "").strip()
            }
            candidate_data.append(entry)
            name_val = entry["Name"].lower()
            if name_val:
                name_index[name_val] = entry
            het_val = entry["HET ID"].lower()
            if het_val:
                het_index[het_val] = entry
            formula_val = entry["Formula"].lower()
            if formula_val:
                formula_index[formula_val] = entry
    indexes["Name"] = name_index
    indexes["HET ID"] = het_index
    indexes["Formula"] = formula_index
    return candidate_data, indexes

# ----------------------------
# Loader for Disease Data (HSDN-Symptoms-DO.tsv)
# ----------------------------
def load_disease_data(tsv_filename):
    candidate_data = []
    indexes = {}
    symptom_index = {}
    disease_index = {}
    doid_index = {}
    with open(tsv_filename, newline='', encoding='utf-8') as tsvfile:
        reader = csv.DictReader(tsvfile, delimiter='\t')
        for row in reader:
            symptom = row.get('symptom_name', '').strip()
            disease = row.get('disease_name', '').strip()
            doid = row.get('doid_name', '').strip()
            if not (symptom or disease or doid):
                continue
            entry = {
                'symptom_name': symptom,
                'disease_name': disease,
                'doid_name': doid
            }
            candidate_data.append(entry)
            if symptom:
                symptom_index[symptom.lower()] = entry
            if disease:
                disease_index[disease.lower()] = entry
            if doid:
                doid_index[doid.lower()] = entry
    indexes['symptom_name'] = symptom_index
    indexes['disease_name'] = disease_index
    indexes['doid_name'] = doid_index
    return candidate_data, indexes

# ----------------------------
# Similarity Function
# ----------------------------
def get_similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()

# ----------------------------
# Generic Search Function with Adaptive Threshold
# ----------------------------
def get_suggestions_adjusted(query, column, indexes):
    query = query.lower()
    # Set threshold lower for disease searches
    threshold = 0.25 if column in ['symptom_name', 'disease_name', 'doid_name'] else 0.5
    results = []
    dataset = indexes.get(column, {})
    matches = [(key, get_similarity(query, key)) for key in dataset.keys()]
    matches.sort(key=lambda x: x[1], reverse=True)
    for match, score in matches[:10]:
        if score >= threshold:
            entry = dataset[match]
            # Gene entries
            if 'Canonical Gene Name' in entry:
                results.append((entry['Canonical Gene Name'], entry.get('GENE_NAME',''), match, score))
            # Drug entries
            elif 'Name' in entry:
                main_val = entry['Name']
                secondary_val = entry.get('HET ID', '') if column == 'Name' else entry.get(column, '')
                results.append((main_val, secondary_val, match, score))
            # Disease entries
            else:
                if column == 'symptom_name':
                    main_val = entry['symptom_name']
                    secondary_val = entry['disease_name']
                elif column == 'disease_name':
                    main_val = entry['disease_name']
                    secondary_val = entry['symptom_name']
                else:
                    main_val = entry['doid_name']
                    secondary_val = entry['disease_name']
                results.append((main_val, secondary_val, match, score))
    return results

# ----------------------------
# Global State & Dataset Management
# ----------------------------
current_dataset = 'Genes'
# Datasets configuration include loading functions and search options.
datasets = {
    'Genes': {
        'csv_filename': 'g_final.csv',
        'search_options': ['Canonical Gene Name','Gene Synonyms','UNIPROT_ID'],
        'load_function': load_candidates_from_csv
    },
    'Drugs': {
        'csv_filename': 'DrugBank Structure Links.csv',
        'search_options': ['Name','HET ID','Formula'],
        'load_function': load_drug_data
    },
    'Disease': {
        'csv_filename': 'HSDN-Symptoms-DO.tsv',
        'search_options': ['symptom_name','disease_name','doid_name'],
        'search_labels': ['Symptoms','Disease Diagnosis','Common Disease Name'],
        'load_function': load_disease_data
    },
}

candidate_data = []
indexes = {}

def load_current_dataset():
    global candidate_data,indexes
    ds = datasets[current_dataset]
    if ds.get('under_construction',False):
        candidate_data,indexes = [],{}
    else:
        candidate_data,indexes = ds['load_function'](ds['csv_filename'])

# ----------------------------
# GUI Update & Search Functions
# ----------------------------
def update_suggestions(event=None):
    if search_entry.cget('state')=='disabled': return
    query = search_entry.get().strip()
    for row in result_tree.get_children():
        result_tree.delete(row)
    if query:
        threading.Thread(target=async_search,args=(query,selected_column.get())).start()

def async_search(query,column):
    suggestions = get_suggestions_adjusted(query,column,indexes)
    suggestions.sort(key=lambda x: x[3],reverse=True)
    root.after(0,lambda: update_treeview(suggestions))

def update_treeview(suggestions):
    for row in result_tree.get_children():
        result_tree.delete(row)
    for main_val,secondary_val,match,score in suggestions:
        result_tree.insert('',tk.END,values=(main_val,secondary_val,match,f"{score:.2f}"))

def on_tree_select(event):
    sel = result_tree.focus()
    if sel:
        vals = result_tree.item(sel,'values')
        search_entry.delete(0,tk.END)
        search_entry.insert(0,vals[0])

def on_enter(event):
    new_tab=tk.Toplevel(root)
    new_tab.title('Redirected')
    new_tab.geometry('400x200')
    label=tk.Label(new_tab,text='You have been redirected.',font=('Inter',14),fg='white',bg='#2C2F33')
    label.pack(expand=True)

# ----------------------------
# Dataset Selection Function
# ----------------------------
def select_dataset(event):
    global current_dataset
    selected = dataset_choice.get()
    current_dataset = selected
    ds = datasets[current_dataset]
    # Clear previous buttons and entry
    for widget in frame_buttons.winfo_children():
        widget.destroy()
    search_entry.delete(0, tk.END)
    if ds.get('under_construction', False):
        search_entry.config(state='disabled')
        result_tree.pack_forget()
        under_construction_label.config(text='Feature Under Construction: Check Back Soon!')
        under_construction_label.pack(expand=True)
    else:
        search_entry.config(state='normal')
        under_construction_label.pack_forget()
        result_tree.pack(side='left', fill='both', expand=True)
        load_current_dataset()
        opts = ds['search_options']
        labels = ds.get('search_labels', opts)
        for opt, lbl in zip(opts, labels):
            rb = tk.Radiobutton(
                frame_buttons,
                text=lbl,
                variable=selected_column,
                value=opt,
                command=update_suggestions,
                fg='white',
                bg='#2C2F33',
                selectcolor='#E74C3C',
                font=('Inter', 12),
                borderwidth=2,
                relief='ridge'
            )
            rb.pack(side=tk.LEFT, padx=5, pady=2)
        for row in result_tree.get_children():
            result_tree.delete(row)
    root.title(f"Search Tool - {current_dataset}")

# ----------------------------
# Initialize Dataset and GUI
# ----------------------------
load_current_dataset()

root = tk.Tk()
root.title('Search Tool - Genes')
root.geometry('750x600')
root.configure(bg='#2C2F33')

style = ttk.Style()
style.theme_use('clam')
style.configure('TButton', font=('Inter', 12))
style.configure('TCombobox', font=('Inter', 12))

# Header Frame
header_frame = tk.Frame(root, bg='#2C2F33')
header_frame.pack(pady=15)
header_label = tk.Label(
    header_frame,
    text='Search Tool',
    font=('Inter', 24, 'bold'),
    fg='#E74C3C',
    bg='#2C2F33'
)
header_label.pack()

# Descriptive Text
# (You can adjust descriptive text per dataset if needed)

# Input Frame
input_frame = tk.Frame(root, bg='#2C2F33')
input_frame.pack(pady=10)

query_label = tk.Label(
    input_frame,
    text='Enter search query:',
    font=('Inter', 14),
    fg='white',
    bg='#2C2F33'
)
query_label.grid(row=0, column=0, padx=5, pady=5, sticky='w')

search_entry = tk.Entry(
    input_frame,
    width=40,
    font=('Inter', 14),
    bg='#23272A',
    fg='white',
    insertbackground='white',
    relief='ridge',
    borderwidth=5
)
search_entry.grid(row=1, column=0, padx=5, pady=5)
search_entry.bind('<KeyRelease>', update_suggestions)
search_entry.bind('<Return>', on_enter)

# Dataset Combobox
dataset_label = tk.Label(
    input_frame,
    text='Select dataset:',
    font=('Inter', 14),
    fg='white',
    bg='#2C2F33'
)
dataset_label.grid(row=0, column=1, padx=10, pady=5, sticky='w')

dataset_choice = ttk.Combobox(
    input_frame,
    values=list(datasets.keys()),
    state='readonly'
)
dataset_choice.set(current_dataset)
dataset_choice.grid(row=1, column=1, padx=10, pady=5)
dataset_choice.bind('<<ComboboxSelected>>', select_dataset)

# Frame for radio buttons
frame_buttons = tk.Frame(root, bg='#2C2F33', bd=2, relief='ridge')
frame_buttons.pack(pady=10, padx=10, fill='x')
selected_column = tk.StringVar(value=datasets[current_dataset].get('search_options', [''])[0])
for opt, lbl in zip(datasets[current_dataset].get('search_options', []),
                    datasets[current_dataset].get('search_labels', datasets[current_dataset].get('search_options', []))):
    rb = tk.Radiobutton(
        frame_buttons,
        text=lbl,
        variable=selected_column,
        value=opt,
        command=update_suggestions,
        fg='white',
        bg='#2C2F33',
        selectcolor='#E74C3C',
        font=('Inter', 12),
        borderwidth=2,
        relief='ridge'
    )
    rb.pack(side=tk.LEFT, padx=5, pady=2)

# Results Frame
result_frame = tk.Frame(root, bg='#2C2F33')
result_frame.pack(pady=10, padx=10, fill='both', expand=True)
columns = ('Main Value', 'Secondary Value', 'Matched', 'Confidence')
result_tree = ttk.Treeview(
    result_frame,
    columns=columns,
    show='headings',
    height=10
)
for col in columns:
    result_tree.heading(col, text=col)
    result_tree.column(col, anchor='center')
result_tree.pack(side='left', fill='both', expand=True)
result_tree.bind('<ButtonRelease-1>', on_tree_select)

# Under Construction Label
under_construction_label = tk.Label(
    result_frame,
    text='Feature Under Construction: Check Back Soon!',
    font=('Inter', 16),
    fg='white',
    bg='#2C2F33'
)
under_construction_label.pack_forget()

# Scrollbar
scrollbar = ttk.Scrollbar(result_frame, orient='vertical', command=result_tree.yview)
result_tree.configure(yscroll=scrollbar.set)
scrollbar.pack(side='right', fill='y')

# Start main loop
root.mainloop()
