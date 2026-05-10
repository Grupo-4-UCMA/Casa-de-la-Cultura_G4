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
        'query': query
    })