import os
import django
import pandas as pd
import numpy as np
from scipy.sparse import csr_matrix
from sklearn.metrics.pairwise import cosine_similarity

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "casa_cultura.settings")
django.setup()

from app.models import Rating

print("1. Cargando millones de valoraciones desde SQLite...")
qs = Rating.objects.values_list('user__user_id', 'copy__book__book_id', 'rating')
df = pd.DataFrame(list(qs), columns=['user_id', 'book_id', 'rating'])

print("2. Construyendo Matriz Dispersa (Ahorro extremo de RAM para PC de 6GB)...")
users = df['user_id'].unique()
books = df['book_id'].unique()

user_map = {u: i for i, u in enumerate(users)}
book_map = {b: i for i, b in enumerate(books)}
rev_book_map = {i: b for i, b in enumerate(books)}

row = df['user_id'].map(user_map)
col = df['book_id'].map(book_map)
data = df['rating']

sparse_matrix = csr_matrix((data, (row, col)), shape=(len(users), len(books)))

print("3. Entrenando Modelo (Similitud del Coseno Item-Item)...")
item_sim = cosine_similarity(sparse_matrix.T, dense_output=True)

print("4. Pre-calculando 'Si te gustó este libro, te gustará...'")
book_recs = []
for i in range(len(books)):
    similar_indices = np.argsort(item_sim[i])[::-1]
    top_indices = [idx for idx in similar_indices if idx != i][:3]
    book_recs.append({
        'book_id': rev_book_map[i],
        'rec_1': rev_book_map[top_indices[0]] if len(top_indices) > 0 else 0,
        'rec_2': rev_book_map[top_indices[1]] if len(top_indices) > 1 else 0,
        'rec_3': rev_book_map[top_indices[2]] if len(top_indices) > 2 else 0,
    })
pd.DataFrame(book_recs).to_csv('data/recs_libros.csv', index=False)

print("5. Pre-calculando Recomendaciones Personalizadas por Usuario...")
user_recs = []
for start in range(0, len(users), 2000):
    end = min(start + 2000, len(users))
    chunk_sparse = sparse_matrix[start:end]
    chunk_scores = chunk_sparse.dot(item_sim)
    chunk_scores[chunk_sparse.nonzero()] = 0
    
    top_3_idx = np.argsort(-chunk_scores, axis=1)[:, :3]
    for idx_in_chunk, top_idx in enumerate(top_3_idx):
        user_idx = start + idx_in_chunk
        user_recs.append({
            'user_id': users[user_idx],
            'rec_1': rev_book_map[top_idx[0]],
            'rec_2': rev_book_map[top_idx[1]],
            'rec_3': rev_book_map[top_idx[2]],
        })
pd.DataFrame(user_recs).to_csv('data/recs_usuarios.csv', index=False)

print("Entrenamiento finalizado. El backend web ahora es instantaneo.")