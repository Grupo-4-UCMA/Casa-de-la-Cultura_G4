import pandas as pd
import numpy as np
from scipy.sparse import csr_matrix
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import normalize
import pickle
import os

def generar_matriz_recomendaciones():
    # USAMOS LAS RUTAS DE DATOS LIMPIOS DE JOSE LUIS
    ruta_ratings = 'data/clean/ratings_clean.csv'
    ruta_salida = 'catalogo/indices_ia.pkl'

    if not os.path.exists(ruta_ratings):
        print(f"Error: No se encuentra {ruta_ratings}. ¿Jose Luis ha ejecutado el ETL?")
        return

    print("Cargando ratings limpios...")
    # Optimizamos memoria con float32 (RNF-04)
    ratings = pd.read_csv(ruta_ratings, dtype={'user_id': 'int32', 'copy_id': 'int32', 'rating': 'float32'})
    
    # Filtro de calidad (OB-01): Usuarios con al menos 10 valoraciones
    user_counts = ratings['user_id'].value_counts()
    ratings = ratings[ratings['user_id'].isin(user_counts[user_counts >= 10].index)]

    print("Creando matriz dispersa de ejemplares...")
    copy_u = list(ratings.copy_id.unique())
    user_u = list(ratings.user_id.unique())
    
    row = ratings.user_id.astype('category').cat.codes
    col = ratings.copy_id.astype('category').cat.codes
    data_sparse = csr_matrix((ratings['rating'], (col, row)), shape=(len(copy_u), len(user_u)))
    
    # Normalización para cálculo por bloques (evita ArrayMemoryError)
    data_normalized = normalize(data_sparse, axis=1)

    print(f"Entrenando IA para {len(copy_u)} ejemplares...")
    dict_recomendaciones = {}
    chunk_size = 500 

    for i in range(0, len(copy_u), chunk_size):
        fin = min(i + chunk_size, len(copy_u))
        chunk = data_normalized[i:fin]
        # Producto punto = Similitud de coseno (gracias a la normalización previa)
        sim_chunk = chunk.dot(data_normalized.T).toarray() 
        
        for idx_in_chunk, global_idx in enumerate(range(i, fin)):
            sim_scores = sim_chunk[idx_in_chunk]
            # Cogemos los 11 más parecidos y quitamos el primero (él mismo)
            similar_indices = sim_scores.argsort()[-11:-1][::-1]
            
            copy_id = copy_u[global_idx]
            dict_recomendaciones[copy_id] = [copy_u[idx] for idx in similar_indices]
        
        if i % 5000 == 0:
            print(f"Progreso: {fin}/{len(copy_u)} ejemplares procesados...")

    print("Guardando 'cerebro' de la IA...")
    with open(ruta_salida, 'wb') as f:
        pickle.dump(dict_recomendaciones, f)
    
    print(f"Éxito: Archivo {ruta_salida} generado correctamente.")

if __name__ == "__main__":
    generar_matriz_recomendaciones()