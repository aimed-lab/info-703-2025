
"""
A Gradio UI that loads a triplets CSV, restores trained ComplEx, TransE, and RotatE models,
then allows interactive tail-prediction and rank inspection.
Prompts for:
  - Path to triplets CSV
  - Paths to each model .pkl file
"""
import numpy as np
import pandas as pd
import tensorflow as tf
from ampligraph.evaluation.protocol import train_test_split_no_unseen
from ampligraph.evaluation.metrics import mrr_score, hits_at_n_score
from ampligraph.utils import restore_model
import gradio as gr

triplets_csv   = input("Enter path to triplets CSV (e.g., all_triplets.csv): ")
complEx_path   = input("Enter path to ComplEx model .pkl: ")
rotate_path    = input("Enter path to RotatE model .pkl: ")
transe_path    = input("Enter path to TransE model .pkl: ")

df = pd.read_csv(triplets_csv, index_col=False)
test_train, X_valid = train_test_split_no_unseen(df.values, 500, seed=0)
X_train, X_test = train_test_split_no_unseen(test_train, 1000, seed=0)
X = {'train': X_train, 'valid': X_valid, 'test': X_test}
filter_dict = {'test': np.concatenate((X_train, X_valid, X_test))}

print(f"Loaded {df.shape[0]} triples. Train={X_train.shape[0]}, Valid={X_valid.shape[0]}, Test={X_test.shape[0]}")

print("Restoring models...")
model_ce = restore_model(model_name_path=complEx_path)
model_rt = restore_model(model_name_path=rotate_path)
model_tr = restore_model(model_name_path=transe_path)
models_dict = {"ComplEx": model_ce, "RotatE": model_rt, "TransE": model_tr}

entities = sorted(set(df['subject']) | set(df['object']))
# prepare "Head | Relation | True Tail" strings
test_choices = [f"{h} | {r} | {t}" for h, r, t in X['test']]

def get_tail_prediction_ranks_all_models(test_triples, models_dict, entities, filter_dict):
    results = []
    known = set(map(tuple, filter_dict['test']))
    for h, r, true_t in test_triples:
        row = {"Head": h, "Relation": r, "True Tail": true_t}
        for name, model in models_dict.items():
            cands = [(h, r, t) for t in entities if (h, r, t) not in known or t == true_t]
            scores = model.predict(cands)
            order  = np.argsort(scores)[::-1]
            ranked = [cands[i][2] for i in order]
            row[f"Rank ({name})"] = ranked.index(true_t) + 1 if true_t in ranked else None
        results.append(row)
    return pd.DataFrame(results)

def predict_tail_with_truth(model_name, triplet_str, top_k):
    try:
        h, r, true_t = triplet_str.split(" | ")
    except:
        return pd.DataFrame(), "Select a valid triplet"
    try:
        k = int(top_k)
    except:
        return pd.DataFrame(), "Top K must be an integer"

    model = models_dict[model_name]
    known = set(map(tuple, filter_dict['test']))
    cands = [(h, r, t) for t in entities if (h, r, t) not in known or t == true_t]
    if not cands:
        return pd.DataFrame(), "No candidates"

    scores = model.predict(cands)
    order  = np.argsort(scores)[::-1]
    k = max(1, min(k, len(cands)))
    top_idx = order[:k]
    df_out = pd.DataFrame({
        "Rank": range(1, k+1),
        "Tail":  [cands[i][2] for i in top_idx],
        "Score": [float(scores[i]) for i in top_idx]
    })

    full_ranked = [cands[i][2] for i in order]
    rank = full_ranked.index(true_t) + 1 if true_t in full_ranked else None
    msg = f"True tail '{true_t}' at position {rank} of {len(cands)}" if rank else f"'{true_t}' not found"
    return df_out, msg

def compute_true_tail_ranks(selected):
    if not selected:
        cols = ["Head","Relation","True Tail"] + [f"Rank ({m})" for m in models_dict]
        return pd.DataFrame(columns=cols)
    if isinstance(selected, str):
        selected = [selected]
    trips = [tuple(s.split(" | ")) for s in selected if len(s.split(" | "))==3]
    if not trips:
        cols = ["Head","Relation","True Tail"] + [f"Rank ({m})" for m in models_dict]
        return pd.DataFrame(columns=cols)
    return get_tail_prediction_ranks_all_models(trips, models_dict, entities, filter_dict)

with gr.Blocks(title="🔗 KG Link-Prediction Explorer") as app:
    gr.Markdown("## KG Link-Prediction Explorer")
    with gr.Tab("Predict Tail"):
        model_dd = gr.Dropdown(list(models_dict), label="Model")
        trip_dd  = gr.Dropdown(test_choices,    label="Test Triple")
        k_num    = gr.Number(value=10, precision=0, label="Top K")
        btn1     = gr.Button("Submit")
        out_tbl1 = gr.Dataframe(interactive=False, label="Top-K Predictions")
        out_txt1 = gr.Textbox(label="True-Tail Position")
        btn1.click(predict_tail_with_truth, [model_dd, trip_dd, k_num], [out_tbl1, out_txt1])

    with gr.Tab("True-Tail Ranks"):
        multi_dd = gr.Dropdown(test_choices, multiselect=True, label="Test Triples")
        btn2     = gr.Button("Compute Ranks")
        out_tbl2 = gr.Dataframe(interactive=True,  label="True-Tail Ranks")
        btn2.click(compute_true_tail_ranks, [multi_dd], [out_tbl2])

if __name__ == "__main__":
    app.launch()

