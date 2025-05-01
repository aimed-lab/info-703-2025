"""
Train and evaluate knowledge graph embedding models (ComplEx, TransE, RotatE)
using AmpliGraph on a CSV of triplets.

Functions:
- load_and_split(triples_csv, valid_size=500, test_size=1000, seed=0)
- train_and_evaluate(scoring_type, model_name, X, filter_positives, epochs=100)
- train_complex(), train_transe(), train_rotate()

save each model to '<ModelName>.pkl'.
"""
import numpy as np
import pandas as pd
import tensorflow as tf
from ampligraph.evaluation.protocol import train_test_split_no_unseen
from ampligraph.evaluation.metrics import mrr_score, hits_at_n_score
from ampligraph.latent_features import ScoringBasedEmbeddingModel
from ampligraph.latent_features.loss_functions import get as get_loss
from ampligraph.latent_features.regularizers import get as get_regularizer
from ampligraph.utils import save_model


def load_and_split(triples_csv, valid_size=500, test_size=1000, seed=0):
    """
    Load triplets and split into training, validation, and test sets.
    Returns X dict and filter_positives dict for evaluation.
    """
    df = pd.read_csv(triples_csv, index_col=False)
    # validation split
    test_train, X_valid = train_test_split_no_unseen(df.values, valid_size, seed=seed)
    # test split
    X_train, X_test = train_test_split_no_unseen(test_train, test_size, seed=seed)
    print(f"Total triples: {df.shape}")
    print(f"Size of train: {X_train.shape}")
    print(f"Size of valid: {X_valid.shape}")
    print(f"Size of test: {X_test.shape}")
    X = {'train': X_train, 'valid': X_valid, 'test': X_test}
    filter_positives = {'test': np.concatenate((X_train, X_valid, X_test))}
    return X, filter_positives


def train_and_evaluate(scoring_type, model_name, X, filter_positives,
                       epochs=100, batch_divisor=10):
    """
    Train and evaluate a ScoringBasedEmbeddingModel of given type.
    Saves the model to '<model_name>.pkl' and prints metrics.
    Returns a dict of metrics.
    """
    # instantiate model
    model = ScoringBasedEmbeddingModel(
        eta=1,
        k=250,
        scoring_type=scoring_type
    )
    # compile
    optim = tf.keras.optimizers.Adam(learning_rate=1e-3)
    loss = get_loss('pairwise', {'margin': 0.5})
    regularizer = get_regularizer('LP', {'p': 2, 'lambda': 1e-5})
    model.compile(optimizer=optim,
                  loss=loss,
                  entity_relation_regularizer=regularizer)
    # early stopping
    checkpoint = tf.keras.callbacks.EarlyStopping(
        monitor='val_hits10',
        min_delta=0,
        patience=5,
        verbose=1,
        mode='max',
        restore_best_weights=True
    )
    # training
    model.fit(
        X['train'],
        batch_size=int(X['train'].shape[0] / batch_divisor),
        epochs=epochs,
        validation_freq=20,
        validation_burn_in=100,
        validation_data=X['valid'],
        validation_filter=filter_positives,
        callbacks=[checkpoint],
        verbose=True
    )
    # evaluation
    ranks = model.evaluate(X['test'], use_filter=filter_positives, corrupt_side='s,o')
    mrr = mrr_score(ranks)
    hits1  = hits_at_n_score(ranks, n=1)
    hits10 = hits_at_n_score(ranks, n=10)
    hits50 = hits_at_n_score(ranks, n=50)
    hits100= hits_at_n_score(ranks, n=100)
    print(f"\n{scoring_type} performance:")
    print(f"  MRR    : {mrr}")
    print(f"  Hits@1 : {hits1}")
    print(f"  Hits@10: {hits10}")
    print(f"  Hits@50: {hits50}")
    print(f"  Hits@100: {hits100}")
    # save model
    filename = f"{model_name}.pkl"
    save_model(model, model_name_path=filename)
    print(f"Model saved to {filename}\n")
    return {'mrr': mrr,
            'hits1': hits1,
            'hits10': hits10,
            'hits50': hits50,
            'hits100': hits100}


def train_complex():
    X, filter_positives = load_and_split('all_triplets.csv')
    return train_and_evaluate('ComplEx', 'ComplEx', X, filter_positives)


def train_transe():
    X, filter_positives = load_and_split('all_triplets.csv')
    return train_and_evaluate('TransE', 'TransE', X, filter_positives)


def train_rotate():
    X, filter_positives = load_and_split('all_triplets.csv')
    return train_and_evaluate('RotatE', 'RotatE', X, filter_positives)


if __name__ == '__main__':
    print('Training ComplEx...')
    metrics_ce = train_complex()
    print('Training TransE...')
    metrics_tr = train_transe()
    print('Training RotatE...')
    metrics_rt = train_rotate()
    print('All trainings complete!')
    print('Metrics:')
    print('ComplEx:', metrics_ce)
    print('TransE:', metrics_tr)
    print('RotatE:', metrics_rt)
