from django.shortcuts import render
import pandas as pd
import os
import unicodedata
import re

def normalizar_texto(texto):
    if not isinstance(texto, str):
        return ""
    texto = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('utf-8')
    return re.sub(r'[^a-zA-Z0-9]', '', texto).lower()

def buscador_catalogo(request):
    query = request.GET.get('q', '')
    ruta_datos = 'data/raw/books.csv'
    
    # Datos extraídos del análisis exploratorio (eda_inicial.ipynb) para el Dashboard
    # Max valoraciones: 22806 (sirve para calcular el porcentaje de la barra en CSS)
    top_libros = [
        {'title': 'The Hunger Games', 'authors': 'Suzanne Collins', 'ratings': 22806, 'pct': 100},
        {'title': "Harry Potter and the Sorcerer's Stone", 'authors': 'J.K. Rowling', 'ratings': 21850, 'pct': 95},
        {'title': 'To Kill a Mockingbird', 'authors': 'Harper Lee', 'ratings': 19088, 'pct': 83},
        {'title': 'Twilight', 'authors': 'Stephenie Meyer', 'ratings': 16931, 'pct': 74},
        {'title': 'The Great Gatsby', 'authors': 'F. Scott Fitzgerald', 'ratings': 16604, 'pct': 72},
    ]
    
    if os.path.exists(ruta_datos):
        df = pd.read_csv(ruta_datos, sep=',', encoding='latin-1', on_bad_lines='skip', low_memory=False)
        if query:
            q_norm = normalizar_texto(query)
            df['title_norm'] = df['title'].apply(normalizar_texto)
            df['authors_norm'] = df['authors'].apply(normalizar_texto)
            
            resultados = df[
                (df['title_norm'].str.contains(q_norm, na=False)) | 
                (df['authors_norm'].str.contains(q_norm, na=False))
            ].head(20)
        else:
            resultados = df.head(10)
    else:
        resultados = pd.DataFrame()

    return render(request, 'catalogo/lista_libros.html', {
        'libros': resultados.to_dict('records'), 
        'top_libros': top_libros,
        'query': query
    })