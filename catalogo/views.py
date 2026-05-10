from django.shortcuts import render
import pandas as pd
import os

def buscador_catalogo(request):
    query = request.GET.get('q', '')
    ruta_datos = 'data/raw/books.csv'
    
    if os.path.exists(ruta_datos):
        df = pd.read_csv(ruta_datos, sep=',', encoding='latin-1', on_bad_lines='skip', low_memory=False)
        if query:
            resultados = df[
                df['title'].str.contains(query, case=False, na=False) | 
                df['authors'].str.contains(query, case=False, na=False)
            ].head(20)
        else:
            resultados = df.head(10)
    else:
        resultados = pd.DataFrame()

    return render(request, 'catalogo/lista_libros.html', {'libros': resultados.to_dict('records'), 'query': query})