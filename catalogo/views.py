from django.shortcuts import render, redirect
import pandas as pd
import os
import unicodedata
import re
import pickle

INDICES_IA_PATH = 'catalogo/indices_ia.pkl'
indices_ia = {}
if os.path.exists(INDICES_IA_PATH):
    with open(INDICES_IA_PATH, 'rb') as f:
        indices_ia = pickle.load(f)

TOP_LIBROS_CACHE = None

MAPA_IDIOMAS = {
    'en': 'Inglés', 'eng': 'Inglés', 'en-US': 'Inglés', 'en-GB': 'Inglés',
    'spa': 'Español', 'es': 'Español', 'fre': 'Francés', 'fr': 'Francés',
    'ger': 'Alemán', 'de': 'Alemán', 'ita': 'Italiano', 'it': 'Italiano',
    'jpn': 'Japonés', 'ara': 'Árabe', 'dan': 'Danés', 'fil': 'Filipino',
    'ind': 'Indonesio', 'mul': 'Múltiples idiomas', 'nl': 'Neerlandés',
    'nor': 'Noruego', 'per': 'Persa', 'pol': 'Polaco', 'por': 'Portugués',
    'rum': 'Rumano', 'rus': 'Ruso', 'swe': 'Sueco', 'tur': 'Turco',
    'vie': 'Vietnamita', 'nan': 'Desconocido'
}

def cargar_datos_completos():
    ruta_books = 'data/clean/books_with_genre.csv'
    ruta_authors = 'data/clean/book_authors_extended.csv'
    
    if os.path.exists(ruta_books) and os.path.exists(ruta_authors):
        df_books = pd.read_csv(ruta_books).drop_duplicates('book_id')
        df_authors = pd.read_csv(ruta_authors)
        
        df_books['genre'] = df_books['genre'].fillna('Desconocido')
        df_books['original_publication_year'] = pd.to_numeric(df_books['original_publication_year'], errors='coerce').fillna(0).astype(int)
        
        df_books['language_display'] = df_books['language_code'].map(MAPA_IDIOMAS).fillna(df_books['language_code'])
        
        sagas_fantasia = ['Harry Potter', 'Lord of the Rings', 'Chronicles of Narnia', 'Twilight', 'Hunger Games', 'A Song of Ice and Fire']
        for saga in sagas_fantasia:
            df_books.loc[df_books['title'].str.contains(saga, case=False, na=False), 'genre'] = 'Fantasía'
            
        autores_agrupados = df_authors.groupby('book_id')['author'].apply(lambda x: ', '.join(x)).reset_index()
        autores_agrupados.columns = ['book_id', 'authors']
        
        return pd.merge(df_books, autores_agrupados, on='book_id', how='left')
    return pd.DataFrame()

def obtener_votos_totales():
    ruta_ratings = 'data/clean/ratings_clean.csv'
    ruta_copies = 'data/clean/copies_clean.csv'
    
    if os.path.exists(ruta_ratings) and os.path.exists(ruta_copies):
        ratings_df = pd.read_csv(ruta_ratings, usecols=['copy_id'])
        copies_df = pd.read_csv(ruta_copies, usecols=['copy_id', 'book_id'])
        
        conteos = ratings_df['copy_id'].value_counts().reset_index()
        conteos.columns = ['copy_id', 'votos']
        
        datos_unidos = pd.merge(conteos, copies_df, on='copy_id')
        return datos_unidos.groupby('book_id')['votos'].sum().reset_index()
    return pd.DataFrame()

def obtener_top_libros():
    global TOP_LIBROS_CACHE
    if TOP_LIBROS_CACHE is not None:
        return TOP_LIBROS_CACHE
        
    df_completo = cargar_datos_completos()
    votos_df = obtener_votos_totales()
    
    if not df_completo.empty and not votos_df.empty:
        ids_populares = votos_df.sort_values('votos', ascending=False).head(5)
        top_unificado = pd.merge(ids_populares, df_completo, on='book_id')
        maximo_votos = top_unificado['votos'].max()
        
        TOP_LIBROS_CACHE = []
        for _, fila in top_unificado.iterrows():
            TOP_LIBROS_CACHE.append({
                'title': fila['title'],
                'authors': fila.get('authors', 'Anónimo'),
                'genre': fila.get('genre', 'Desconocido'),
                'ratings': int(fila['votos']),
                'pct': int((fila['votos'] / maximo_votos) * 100)
            })
        return TOP_LIBROS_CACHE
    return []

def normalizar_texto(texto):
    if not isinstance(texto, str): 
        return ""
    texto = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('utf-8')
    return re.sub(r'[^a-zA-Z0-9]', '', texto).lower()

def login_view(request):
    if request.method == 'POST':
        request.session['user_id'] = request.POST.get('user_id')
        return redirect('buscador')
    return render(request, 'catalogo/login.html')

def logout_view(request):
    if 'user_id' in request.session: 
        del request.session['user_id']
    return redirect('login')

def buscador_catalogo(request):
    query_busqueda = request.GET.get('q', '')
    filtro_genero = request.GET.get('genre', '')
    filtro_idioma = request.GET.get('lang', '')
    filtro_ano = request.GET.get('year', '')
    metodo_orden = request.GET.get('sort', 'relevance')
    usuario_activo = request.session.get('user_id')
    
    df_base = cargar_datos_completos()
    votos_df = obtener_votos_totales()
    top_general = obtener_top_libros()
    
    recomendaciones = []
    top_por_autor = []
    top_por_genero = []

    if not df_base.empty:
        df_base = pd.merge(df_base, votos_df, on='book_id', how='left').fillna({'votos': 0})
        lista_generos = sorted(df_base['genre'].unique().tolist())
        lista_idiomas = sorted(df_base['language_display'].dropna().unique().tolist())
        resultados_busqueda = df_base.copy()

        if query_busqueda:
            texto_normalizado = normalizar_texto(query_busqueda)
            resultados_busqueda['title_norm'] = resultados_busqueda['title'].apply(normalizar_texto)
            resultados_busqueda['authors_norm'] = resultados_busqueda['authors'].fillna("").apply(normalizar_texto)
            resultados_busqueda = resultados_busqueda[(resultados_busqueda['title_norm'].str.contains(texto_normalizado, na=False)) | 
                                                      (resultados_busqueda['authors_norm'].str.contains(texto_normalizado, na=False))]
            
            if not resultados_busqueda.empty:
                autor_encontrado = resultados_busqueda.iloc[0]['authors']
                if pd.notna(autor_encontrado) and autor_encontrado != "":
                    top_por_autor = df_base[df_base['authors'] == autor_encontrado].sort_values('votos', ascending=False).head(3).to_dict('records')

        if filtro_genero:
            resultados_busqueda = resultados_busqueda[resultados_busqueda['genre'] == filtro_genero]
            top_por_genero = df_base[df_base['genre'] == filtro_genero].sort_values('votos', ascending=False).head(3).to_dict('records')
        
        if filtro_idioma:
            resultados_busqueda = resultados_busqueda[resultados_busqueda['language_display'] == filtro_idioma]

        if filtro_ano:
            try:
                ano_entero = int(filtro_ano)
                resultados_busqueda = resultados_busqueda[resultados_busqueda['original_publication_year'] == ano_entero]
            except ValueError:
                pass

        if metodo_orden == 'popular':
            resultados_busqueda = resultados_busqueda.sort_values('votos', ascending=False)
        elif metodo_orden == 'year_new':
            resultados_busqueda = resultados_busqueda.sort_values('original_publication_year', ascending=False)
        elif metodo_orden == 'year_old':
            resultados_busqueda = resultados_busqueda[resultados_busqueda['original_publication_year'] > 0].sort_values('original_publication_year', ascending=True)

        listado_final = resultados_busqueda.head(20).to_dict('records')
        
        ruta_copies = 'data/clean/copies_clean.csv'
        if listado_final and indices_ia and os.path.exists(ruta_copies):
            df_copias = pd.read_csv(ruta_copies)
            id_referencia = listado_final[0]['book_id']
            genero_referencia = listado_final[0]['genre']
            copias_libro = df_copias[df_copias['book_id'] == id_referencia]
            
            if not copias_libro.empty:
                id_copia_ia = copias_libro.iloc[0]['copy_id']
                ids_vecinos = indices_ia.get(id_copia_ia, [])
                
                if ids_vecinos:
                    ids_libros_recom = df_copias[df_copias['copy_id'].isin(ids_vecinos)]['book_id'].unique()
                    afinidad_genero = df_base[(df_base['book_id'].isin(ids_libros_recom)) & (df_base['genre'] == genero_referencia)]
                    
                    if not afinidad_genero.empty:
                        recomendaciones = afinidad_genero.head(3).to_dict('records')
                    else:
                        recomendaciones = df_base[df_base['book_id'].isin(ids_libros_recom)].head(3).to_dict('records')
                        
        elif usuario_activo and not query_busqueda:
            ruta_ratings = 'data/clean/ratings_clean.csv'
            if os.path.exists(ruta_ratings) and os.path.exists(ruta_copies):
                try:
                    df_ratings = pd.read_csv(ruta_ratings)
                    df_copias = pd.read_csv(ruta_copies)
                    historial = df_ratings[df_ratings['user_id'] == int(usuario_activo)].sort_values('rating', ascending=False)
                    if not historial.empty and indices_ia:
                        ultima_copia = historial.iloc[0]['copy_id']
                        ids_personalizados = indices_ia.get(ultima_copia, [])
                        if ids_personalizados:
                            ids_libros_perso = df_copias[df_copias['copy_id'].isin(ids_personalizados)]['book_id'].unique()
                            recomendaciones = df_base[df_base['book_id'].isin(ids_libros_perso)].head(3).to_dict('records')
                except: 
                    pass
    else:
        lista_generos = []
        lista_idiomas = []
        listado_final = []

    return render(request, 'catalogo/lista_libros.html', {
        'libros': listado_final, 
        'top_libros': top_general, 
        'top_autor': top_por_autor, 
        'top_genero': top_por_genero,
        'recomendaciones': recomendaciones, 
        'query': query_busqueda, 
        'generos': lista_generos, 
        'idiomas': lista_idiomas,
        'genre_sel': filtro_genero, 
        'lang_sel': filtro_idioma, 
        'year_sel': filtro_ano,
        'sort_sel': metodo_orden, 
        'user_active': usuario_activo
    })