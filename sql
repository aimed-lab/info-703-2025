PharmAlchemy Queries Ran in Oracle APEX to identify potential drug repurposing candidates

Step 1: query description: finding the genes that are linked to rett syndrome
select DS_ID, GENE_SYMBOL, DSI, DPI, UMLS, DISEASE_NAME, DISEASE_TYPE, DISEASE_CLASS, DISEASE_SEMANTIC_TYPE, SCORE, EI, YEAR_INITIAL, YEAR_FINAL, NUM_OF_PMIDS, NUM_OF_SNPS, SOURCE_DATABASE from "D2G_FINAL" a
WHERE UPPER (DISEASE_NAME) LIKE ‘%RETT%’

query description: finding genes linked to MECP2
select DS_ID, UNIPROT_ID_1, UNIPROT_ID_2, GENE_NAMES_1, GENE_NAMES_2, COMBINED_SCORE from "G2G_FINAL" a
WHERE UPPER (GENE_NAMES_2) LIKE ‘%MECP2%’

Step 2: query description: we found the genes that are similar to rett. now, let’s run a query with those linked genes to get the diseases that are also linked to those genes.
select DS_ID, GENE_SYMBOL, DSI, DPI, UMLS, DISEASE_NAME, DISEASE_TYPE, DISEASE_CLASS, DISEASE_SEMANTIC_TYPE, SCORE, EI, YEAR_INITIAL, YEAR_FINAL, NUM_OF_PMIDS, NUM_OF_SNPS, SOURCE_DATABASE from "D2G_FINAL" a
where upper(gene_symbol) in (upper('MECP2'), UPPER('FOXG1'), UPPER('EGR2'), UPPER('PTPN1'), UPPER('CDKL5'), UPPER('STXBP1'), UPPER('NTNG1'), UPPER('GABBR2'))

Step 3: After obtaining the relevant genes to Rett syndrome, I used queries to find the diseases linked to those genes in PharmAlchemy. Then, I made another query to find what drugs treated those diseases.
this query identified memantine and baclofen
select DRUGBANK_ID, DRUG_NAME, CID, UMLS, PHENOTYPE_NAME, MEDDRA_TYPE, UMLS_MEDDRA, MEDDRA_NAME, DRUGBANK_NAME_SIDER, SIDE_EFFECT, PHENOTYPE from "R2D_FINAL" a
WHERE UPPER(MEDDRA_NAME) IN (UPPER(’ANXIETY’), UPPER(’DEPRESSION’), UPPER(’EPILEPSY’), UPPER(’INFLAMMATION’), UPPER(’OBESITY’), UPPER(’SCHIZOPHRENIA’), UPPER(’MYOCLONUS’), UPPER(’B-CELL LYMPHOMA’), UPPER(’INSULIN RESISTANCE’), UPPER(’PULMONARY FIBROSIS’), UPPER(’HYPERINSULINISM’))

Step 4: genes linked to drugs:
select ID, GENE_SYMBOL, INTERACTION_TYPE, SCORE, DRUG_NAME from "DGIDB" a
where upper(gene_symbol) in (upper('FOXG1'), upper('EGR2'), upper('MECP2'), upper('PTPN1'), upper('CDKL5'), upper('STXBP1'), upper('NTNG1'), upper(‘GABBR2'))

Step 5: finding the drugs that are linked to those genes, for what diseases they treat
select DRUGBANK_ID, DRUG_NAME, CID, UMLS, PHENOTYPE_NAME, MEDDRA_TYPE, UMLS_MEDDRA, MEDDRA_NAME, DRUGBANK_NAME_SIDER, SIDE_EFFECT, PHENOTYPE from "R2D_FINAL" a WHERE UPPER(DRUG_NAME) IN (UPPER('ALLOPURINOL'), UPPER('ISOBAVACHALCONE'), UPPER('LICOAGRODIN'), UPPER('BACLOFEN'), UPPER('CALCIUM OXYBATE'), UPPER('1,2- DIHYDROXYNAPHTHALENE'), UPPER('TROFINETIDE'), UPPER('TILUDRONIC ACID'), UPPER('URSOLIC ACID'), UPPER('LIPIDYL PSEUDOPTERANE A'), UPPER('LESOGABERAN'), UPPER('GANAXOLONE'), UPPER('ISIS 113715'), UPPER('DITHIOLETHIONE'), UPPER('FLUOROURACIL'), UPPER('TRETINOIN'), UPPER('POTASSIUM OXYBATE'), UPPER('ANETHOLE TRITHIONE'), UPPER('TRODUSQUEMINE'), UPPER('LOBARIC ACID'), UPPER('ALDISIN'), UPPER('GLISOFLAVONE'), UPPER('FLUORESCEIN DIPHOSPHATE'), UPPER('LESOGABERAN'), UPPER('LICOAGRONE'), UPPER('INSULIN'), UPPER('TRODUSQUEMINE'), UPPER('MITOXANTRONE'), UPPER('CISPLATIN'), UPPER('ARBACLOFEN'), UPPER('LIPIDYL PSEUDOPTERANE D'), UPPER('MOROLIC ACID'), UPPER('OLEANOLIC ACID'), UPPER('MAGNESIUM OXYBATE'), UPPER('OLTIPRAZ'), UPPER('MORONIC ACID'), UPPER('SODIUM OXYBATE'), UPPER('TILUDRONIC ACID'), UPPER('ARBACLOFEN PLACARBIL'), UPPER('ALLYL ISOTHIOCYANATE'))

Step 6: query description: we are finding if there are any trials related to rett syndrome and what drugs are being used.
select NCT_NUMBER, DS_ID, TITLE, CONDITION, INTERVENTIONS, SPONSORS, GENDER, AGE, ENROLLMENT, PHASE, URL, STUDY_RESULTS, PHENOTYPE_ID, UMLS from "TRIAL_FINAL_NEW" a
WHERE CONDITION = ‘RETT SYNDROME’

Step 7: searching the drugs for FDA approval query:
select * from ttd_drug_disease where drugname in ( 'Fluvoxamine', 'Baclofen', 'Cyclosporine', 'Alpha-Linolenic Acid', 'Folic Acid', 'Icosapent', 'Citalopram', 'Glimepiride', 'Pregabalin', 'Lorazepam', 'Phentermine', 'Reserpine', 'Reboxetine', 'Mesalazine', 'Topiramate', 'Venlafaxine', 'Ziprasidone', 'Phenytoin', 'Valproic Acid', 'Conjugated Estrogens', 'Atomoxetine', 'Chlorambucil', 'Morphine', 'Fluorometholone', 'Levonorgestrel', 'Mirtazapine', 'Meprobamate', 'Indomethacin', 'Metformin', 'Protriptyline', 'Clobazam', 'Loxapine', 'Rosiglitazone', 'Treprostinil', 'Phenylephrine', 'Progesterone', 'Alprazolam', 'Methocarbamol', 'Entecavir', 'Betamethasone', 'Prochlorperazine', 'Allopurinol', 'Duloxetine', 'Chlorpromazine', 'Celecoxib', 'Droperidol', 'Imipramine', 'Ketorolac', 'Fluoxetine', 'Buspirone', 'Alitretinoin', 'Haloperidol', 'Carbamazepine', 'Cyclophosphamide', 'Amoxapine', 'Lamotrigine', 'Hydroxyzine', 'Doxapram', 'Ethosuximide', 'Medroxyprogesterone Acetate', 'Diclofenac', 'Trazodone', 'Clorazepate', 'Prednisone', 'Lamivudine', 'Flurbiprofen', 'Paroxetine', 'Epinephrine', 'Midazolam', 'Hydrocortisone', 'Adefovir Dipivoxil', 'Risperidone',
'Tranylcypromine', 'Tretinoin', 'Oxcarbazepine', 'Phenelzine', 'Estradiol', 'Primidone', 'Trifluoperazine', 'Oxazepam', 'Perphenazine', 'Penicillamine', 'Ribavirin', 'Meloxicam', 'Acetazolamide', 'Diazepam', 'Bromazepam', 'Methamphetamine', 'Phendimetrazine', 'Cyproterone acetate', 'Lurasidone', 'Iloperidone', 'Ezogabine', 'Deoxythymidine', 'Estriol', 'Telbivudine', 'Paliperidone', 'Varenicline', 'Bismuth Subsalicylate', 'Fosphenytoin', 'Ursodeoxycholic acid', 'Nitrazepam', 'Propericiazine', 'Molindone', 'Thiothixene', 'Zuclopenthixol', 'Methacholine', 'Chenodeoxycholic acid', 'Difluprednate', 'Nepafenac', 'Salicylate-sodium', 'Methotrimeprazine', 'Rimonabant', 'Rufinamide', 'Asenapine', 'Lacosamide', 'Amisulpride', 'Methylprednisolone', 'Nefazodone', 'Desipramine', 'Bupropion', 'Ibuprofen', 'Budesonide', 'Quetiapine', 'Dexamethasone', 'Fenofibrate', 'Amoxicillin', 'Aripiprazole', 'Memantine', 'Abacavir', 'Glipizide', 'Clonazepam', 'Clomipramine', 'Isocarboxazid', 'Prednisolone', 'Promethazine', 'Ranitidine', 'Atorvastatin', 'Bromfenac', 'Benzphetamine', 'Vigabatrin', 'Orlistat', 'Ethinyl Estradiol', 'Pimozide', 'Phenobarbital', 'Isotretinoin', 'Rimexolone', 'Sertraline', 'Escitalopram', 'Tiagabine', 'Zonisamide', 'Repaglinide', 'Sibutramine', 'Gabapentin', 'Ciclopirox', 'Ketotifen', 'Amiodarone', 'Diazoxide', 'Tolbutamide', 'Oxymorphone', 'Hydrochlorothiazide', 'Salbutamol', 'Pioglitazone', 'Maprotiline', 'Salicylic acid', 'Diethylpropion', 'Ketoprofen', 'Acetylsalicylic acid', 'Doxepin', 'Levetiracetam', 'Nadolol', 'Glyburide', 'Felbamate', 'Vemurafenib' );
