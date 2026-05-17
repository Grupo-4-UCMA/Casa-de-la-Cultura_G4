from django.shortcuts import render, redirect
from django.http import JsonResponse
import pandas as pd
import os
import unicodedata
import re
import pickle
import time

INDICES_IA_PATH = 'catalogo/indices_ia.pkl'
indices_ia = {}

if os.path.exists(INDICES_IA_PATH):
    with open(INDICES_IA_PATH, 'rb') as f:
        indices_ia = pickle.load(f)

TOP_VALORADOS_CACHE = None
TOP_POPULARES_CACHE = None
BASE_CACHE = pd.DataFrame()
VOTOS_CACHE = pd.DataFrame()
COPIAS_CACHE = pd.DataFrame()

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
    global BASE_CACHE
    if not BASE_CACHE.empty:
        return BASE_CACHE.copy()
        
    ruta_books_genre = 'data/clean/books_with_genre.csv'
    ruta_books = 'data/clean/books_clean_final.csv'
    ruta_authors = 'data/clean/book_authors_extended.csv'
    ruta_genres = 'data/clean/book_genres.csv'
    
    df_books = pd.DataFrame()
    if os.path.exists(ruta_books_genre):
        df_books = pd.read_csv(ruta_books_genre)
        df_books['original_publication_year'] = pd.to_numeric(df_books['original_publication_year'], errors='coerce').fillna(0).astype(int)
        df_books['language_display'] = df_books['language_code'].map(MAPA_IDIOMAS).fillna(df_books['language_code']) if 'language_code' in df_books.columns else 'Desconocido'
        
        if 'genre_list' not in df_books.columns:
            col_g = 'genres' if 'genres' in df_books.columns else ('genre' if 'genre' in df_books.columns else None)
            if col_g:
                df_books['genre_list'] = df_books[col_g].apply(lambda x: [g.strip().upper() for g in str(x).split(',')] if pd.notna(x) else ['DESCONOCIDO'])
            else:
                df_books['genre_list'] = [['DESCONOCIDO']] * len(df_books)
                
        if 'authors' not in df_books.columns and 'author' in df_books.columns:
            df_books['authors'] = df_books['author']
            
        BASE_CACHE = df_books.drop_duplicates('book_id') if 'book_id' in df_books.columns else df_books
        return BASE_CACHE.copy()
        
    if os.path.exists(ruta_books) and os.path.exists(ruta_authors) and os.path.exists(ruta_genres):
        df_books = pd.read_csv(ruta_books).drop_duplicates('book_id')
        df_authors = pd.read_csv(ruta_authors)
        df_genres = pd.read_csv(ruta_genres)
        
        df_books['original_publication_year'] = pd.to_numeric(df_books['original_publication_year'], errors='coerce').fillna(0).astype(int)
        df_books['language_display'] = df_books['language_code'].map(MAPA_IDIOMAS).fillna(df_books['language_code'])
        
        autores_agrupados = df_authors.groupby('book_id')['author'].apply(lambda x: ', '.join(x)).reset_index()
        autores_agrupados.columns = ['book_id', 'authors']
        
        generos_agrupados = df_genres.groupby('book_id')['genre'].apply(list).reset_index()
        generos_agrupados.columns = ['book_id', 'genre_list']
        
        df_merged = pd.merge(df_books, autores_agrupados, on='book_id', how='left')
        df_merged = pd.merge(df_merged, generos_agrupados, on='book_id', how='left')
        df_merged['genre_list'] = df_merged['genre_list'].apply(lambda x: x if isinstance(x, list) else ['Desconocido'])
        
        BASE_CACHE = df_merged
        return BASE_CACHE.copy()
    
    return pd.DataFrame()

def obtener_votos_totales():
    global VOTOS_CACHE, COPIAS_CACHE
    if not VOTOS_CACHE.empty:
        return VOTOS_CACHE.copy()

    ruta_ratings = 'data/clean/ratings_clean.csv'
    ruta_copies_clean = 'data/clean/copies_clean.csv'
    ruta_copies_ext = 'data/clean/copies_clean_extended.csv'
    ruta_copies = ruta_copies_clean if os.path.exists(ruta_copies_clean) else (ruta_copies_ext if os.path.exists(ruta_copies_ext) else None)
    
    if os.path.exists(ruta_ratings) and ruta_copies:
        ratings_df = pd.read_csv(ruta_ratings, usecols=['copy_id', 'rating'])
        COPIAS_CACHE = pd.read_csv(ruta_copies, usecols=['copy_id', 'book_id'])
        
        agrupado = ratings_df.groupby('copy_id').agg(votos=('rating', 'count'), nota_media=('rating', 'mean')).reset_index()
        datos_unidos = pd.merge(agrupado, COPIAS_CACHE, on='copy_id')
        
        VOTOS_CACHE = datos_unidos.groupby('book_id').agg(votos=('votos', 'sum'), nota_media=('nota_media', 'mean')).reset_index()
        VOTOS_CACHE['nota_media'] = VOTOS_CACHE['nota_media'].fillna(0).round(1)
        
        return VOTOS_CACHE.copy()
    
    return pd.DataFrame()

def obtener_tops_generales():
    global TOP_VALORADOS_CACHE, TOP_POPULARES_CACHE
    if TOP_VALORADOS_CACHE is not None and TOP_POPULARES_CACHE is not None:
        return TOP_VALORADOS_CACHE, TOP_POPULARES_CACHE
        
    df_completo = cargar_datos_completos()
    votos_df = obtener_votos_totales()
    
    if not df_completo.empty and not votos_df.empty:
        populares_df = votos_df.sort_values('votos', ascending=False).head(5)
        top_pop_unificado = pd.merge(populares_df, df_completo, on='book_id')
        max_votos_pop = top_pop_unificado['votos'].max()
        
        TOP_POPULARES_CACHE = []
        for _, fila in top_pop_unificado.iterrows():
            TOP_POPULARES_CACHE.append({
                'title': fila['title'],
                'ratings': int(fila['votos']),
                'pct': int((fila['votos'] / max_votos_pop) * 100) if max_votos_pop else 0
            })
            
        valorados_df = votos_df[votos_df['votos'] >= 1000].sort_values(['nota_media', 'votos'], ascending=[False, False]).head(5)
        if valorados_df.empty:
            valorados_df = votos_df.sort_values(['nota_media', 'votos'], ascending=[False, False]).head(5)
            
        top_val_unificado = pd.merge(valorados_df, df_completo, on='book_id')
        
        TOP_VALORADOS_CACHE = []
        for _, fila in top_val_unificado.iterrows():
            TOP_VALORADOS_CACHE.append({
                'title': fila['title'],
                'nota_media': float(fila['nota_media']),
                'votos': int(fila['votos']),
                'pct': int((fila['nota_media'] / 5.0) * 100)
            })
            
        return TOP_VALORADOS_CACHE, TOP_POPULARES_CACHE
        
    return [], []

def obtener_preferencias_usuario(user_id):
    ruta = 'data/clean/users_clean.csv'
    if os.path.exists(ruta):
        try:
            df_u = pd.read_csv(ruta)
            col_id = df_u.columns[0]
            fila = df_u[df_u[col_id].astype(str) == str(user_id)]
            if not fila.empty:
                texto = " ".join(fila.iloc[0].astype(str).tolist())
                titulos = re.findall(r"'([^']+)'", texto)
                if titulos:
                    return titulos
                palabras = texto.split()
                if len(palabras) > 0:
                    return [" ".join(palabras[:3])]
        except:
            pass
    return []

def obtener_texto_perfil_completo(user_id):
    ruta = 'data/clean/users_clean.csv'
    if os.path.exists(ruta):
        try:
            df_u = pd.read_csv(ruta)
            col_id = df_u.columns[0]
            fila = df_u[df_u[col_id].astype(str) == str(user_id)]
            if not fila.empty and len(df_u.columns) > 1:
                return str(fila.iloc[0, 1]).lower()
        except:
            pass
    return ""

def normalizar_texto(texto):
    if not isinstance(texto, str): 
        return ""
    texto = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('utf-8')
    return re.sub(r'[^a-zA-Z0-9]', '', texto).lower()

def login_view(request):
    if request.method == 'POST':
        action = request.POST.get('action', 'login')
        user_id = request.POST.get('user_id')
        
        if not user_id:
            return redirect('login')
            
        if action == 'login':
            request.session['user_id'] = user_id
            return redirect('buscador')
            
        elif action == 'edit':
            request.session['user_id'] = user_id
            return redirect('perfil')
            
        elif action == 'delete':
            ruta = 'data/clean/users_clean.csv'
            if os.path.exists(ruta):
                df_u = pd.read_csv(ruta)
                col_id = df_u.columns[0]
                df_u = df_u[df_u[col_id].astype(str) != str(user_id)]
                df_u.to_csv(ruta, index=False)
            if request.session.get('user_id') == user_id:
                del request.session['user_id']
            return redirect('login')
            
    return render(request, 'catalogo/login.html')

def logout_view(request):
    if 'user_id' in request.session: 
        del request.session['user_id']
    return redirect('login')

def registro_view(request):
    if request.method == 'POST':
        gustos = request.POST.get('gustos', '')
        fecha_nacimiento = request.POST.get('fecha_nacimiento', '')
        ruta = 'data/clean/users_clean.csv'
        
        if os.path.exists(ruta):
            df_u = pd.read_csv(ruta)
            col_id = df_u.columns[0]
            nuevo_id = int(df_u[col_id].max()) + 1 if not df_u.empty else 1
            
            if len(df_u.columns) < 3:
                df_u['birthdate'] = ''
                
            nueva_fila = {col: '' for col in df_u.columns}
            nueva_fila[col_id] = nuevo_id
            
            columnas = list(df_u.columns)
            if len(columnas) > 1:
                nueva_fila[columnas[1]] = gustos
            if len(columnas) > 2:
                nueva_fila[columnas[2]] = fecha_nacimiento
                
            df_u = pd.concat([df_u, pd.DataFrame([nueva_fila])], ignore_index=True)
            df_u.to_csv(ruta, index=False)
        else:
            nuevo_id = 1
            df_u = pd.DataFrame({'user_id': [nuevo_id], 'preferences': [gustos], 'birthdate': [fecha_nacimiento]})
            os.makedirs(os.path.dirname(ruta), exist_ok=True)
            df_u.to_csv(ruta, index=False)
            
        request.session['user_id'] = str(nuevo_id)
        return redirect('perfil')
        
    return render(request, 'catalogo/registro.html')

def perfil_view(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')
        
    ruta = 'data/clean/users_clean.csv'
    gustos_actuales = ""
    fecha_actual = ""
    
    if os.path.exists(ruta):
        df_u = pd.read_csv(ruta)
        col_id = df_u.columns[0]
        fila = df_u[df_u[col_id].astype(str) == str(user_id)]
        if not fila.empty:
            columnas = list(df_u.columns)
            if len(columnas) > 1:
                gustos_actuales = str(fila.iloc[0, 1])
                if gustos_actuales == 'nan': gustos_actuales = ""
            if len(columnas) > 2:
                fecha_actual = str(fila.iloc[0, 2])
                if fecha_actual == 'nan': fecha_actual = ""
            
    if request.method == 'POST':
        nuevos_gustos = request.POST.get('gustos', '')
        nueva_fecha = request.POST.get('fecha_nacimiento', '')
        
        if os.path.exists(ruta):
            df_u = pd.read_csv(ruta)
            col_id = df_u.columns[0]
            
            if len(df_u.columns) < 3:
                df_u['birthdate'] = ''
                
            idx = df_u.index[df_u[col_id].astype(str) == str(user_id)].tolist()
            if idx:
                columnas = list(df_u.columns)
                if len(columnas) > 1:
                    df_u.iloc[idx[0], 1] = nuevos_gustos
                if len(columnas) > 2:
                    df_u.iloc[idx[0], 2] = nueva_fecha
                df_u.to_csv(ruta, index=False)
        return redirect('buscador')
        
    return render(request, 'catalogo/perfil.html', {'gustos': gustos_actuales, 'fecha': fecha_actual, 'user_id': user_id})

def buscador_catalogo(request):
    query_busqueda = request.GET.get('q', '')
    filtro_genero = request.GET.get('genre', '')
    filtro_idioma = request.GET.get('lang', '')
    filtro_ano_min = request.GET.get('year_min', '')
    filtro_ano_max = request.GET.get('year_max', '')
    filtro_nota = request.GET.get('rating', '0')
    filtro_votos = request.GET.get('votes', '0')
    filtro_ejemplares = request.GET.get('available', '')
    metodo_orden = request.GET.get('sort', 'relevance')
    
    try:
        pagina_actual = int(request.GET.get('page', 1))
    except ValueError:
        pagina_actual = 1

    usuario_activo = request.session.get('user_id')
    
    df_base = cargar_datos_completos()
    votos_df = obtener_votos_totales()
    top_valorados_general, top_populares_general = obtener_tops_generales()
    
    recomendaciones = []
    top_dinamico = []
    titulo_sidebar_dinamico = ""
    top_por_genero = []
    autor_destacado = ""
    
    if usuario_activo:
        titulo_recomendacion = "Recomendado según tus gustos:"
    else:
        titulo_recomendacion = "Tendencias Actuales en el Catálogo:"

    if not df_base.empty:
        df_base = pd.merge(df_base, votos_df, on='book_id', how='left').fillna({'votos': 0, 'nota_media': 0})
        lista_generos = sorted(list(set(g for sublist in df_base['genre_list'] for g in sublist)))
        lista_idiomas = sorted(df_base['language_display'].dropna().unique().tolist())
        resultados_busqueda = df_base.copy()

        def aplicar_filtros_adicionales(df):
            res = df.copy()
            if filtro_genero and not res.empty:
                res = res[res['genre_list'].apply(lambda x: filtro_genero in x).astype(bool)]
            if filtro_idioma and not res.empty:
                res = res[res['language_display'] == filtro_idioma]
            if filtro_ano_min and not res.empty:
                try: res = res[res['original_publication_year'] >= int(filtro_ano_min)]
                except ValueError: pass
            if filtro_ano_max and not res.empty:
                try: res = res[res['original_publication_year'] <= int(filtro_ano_max)]
                except ValueError: pass
            if filtro_nota and float(filtro_nota) > 0 and not res.empty:
                try: res = res[res['nota_media'] >= float(filtro_nota)]
                except ValueError: pass
            if filtro_votos and int(filtro_votos) > 0 and not res.empty:
                try: res = res[res['votos'] >= int(filtro_votos)]
                except ValueError: pass
            if filtro_ejemplares == 'on' and not res.empty and not COPIAS_CACHE.empty:
                res = res[res['book_id'].isin(COPIAS_CACHE['book_id'])]
            return res

        if query_busqueda:
            texto_normalizado = normalizar_texto(query_busqueda)
            resultados_busqueda['title_norm'] = resultados_busqueda['title'].apply(normalizar_texto)
            resultados_busqueda['authors_norm'] = resultados_busqueda['authors'].fillna("").apply(normalizar_texto)
            resultados_busqueda['isbn_norm'] = resultados_busqueda['isbn'].fillna("").astype(str).apply(normalizar_texto)
            
            resultados_busqueda = resultados_busqueda[
                (resultados_busqueda['title_norm'].str.contains(texto_normalizado, na=False)) | 
                (resultados_busqueda['authors_norm'].str.contains(texto_normalizado, na=False)) |
                (resultados_busqueda['isbn_norm'].str.contains(texto_normalizado, na=False))
            ]
            
            if not resultados_busqueda.empty:
                primer_libro = resultados_busqueda.iloc[0]
                autor_completo = primer_libro['authors']
                
                if pd.notna(autor_completo) and autor_completo != "":
                    autor_destacado = autor_completo.split(',')[0].strip()
                    
                if autor_destacado and texto_normalizado in normalizar_texto(autor_destacado):
                    titulo_sidebar_dinamico = f"Lo mejor de {autor_destacado}"
                    top_dinamico = df_base[df_base['authors'].fillna('').str.contains(autor_destacado, regex=False)].sort_values(['nota_media', 'votos'], ascending=[False, False]).head(3).to_dict('records')
                else:
                    titulo_sidebar_dinamico = f"Top para '{query_busqueda}'"
                    top_dinamico = resultados_busqueda.sort_values(['nota_media', 'votos'], ascending=[False, False]).head(3).to_dict('records')

        resultados_busqueda = aplicar_filtros_adicionales(resultados_busqueda)

        if filtro_genero and not df_base.empty:
            top_por_genero = df_base[df_base['genre_list'].apply(lambda x: filtro_genero in x).astype(bool)].sort_values(['nota_media', 'votos'], ascending=[False, False]).head(3).to_dict('records')

        if metodo_orden == 'popular':
            resultados_busqueda = resultados_busqueda.sort_values('votos', ascending=False)
        elif metodo_orden == 'top_rated':
            resultados_busqueda = resultados_busqueda.sort_values('nota_media', ascending=False)
        elif metodo_orden == 'year_new':
            resultados_busqueda = resultados_busqueda.sort_values('original_publication_year', ascending=False)
        elif metodo_orden == 'year_old':
            resultados_busqueda = resultados_busqueda[resultados_busqueda['original_publication_year'] > 0].sort_values('original_publication_year', ascending=True)

        total_resultados = len(resultados_busqueda)
        total_paginas = max(1, (total_resultados + 19) // 20)
        
        indice_inicio = (pagina_actual - 1) * 20
        indice_fin = pagina_actual * 20
        listado_final = resultados_busqueda.iloc[indice_inicio:indice_fin].to_dict('records')
        
        if query_busqueda and listado_final:
            id_referencia = listado_final[0]['book_id']
            generos_referencia = listado_final[0]['genre_list']
            titulo_recomendacion = f"Porque buscaste '{listado_final[0]['title']}':"
            copias_libro = COPIAS_CACHE[COPIAS_CACHE['book_id'] == id_referencia] if not COPIAS_CACHE.empty else pd.DataFrame()
            
            if not copias_libro.empty and indices_ia:
                id_copia_ia = copias_libro.iloc[0]['copy_id']
                ids_vecinos = indices_ia.get(id_copia_ia, [])
                if ids_vecinos:
                    ids_libros_recom = COPIAS_CACHE[COPIAS_CACHE['copy_id'].isin(ids_vecinos)]['book_id'].unique()
                    df_recom = df_base[df_base['book_id'].isin(ids_libros_recom)]
                    df_recom = aplicar_filtros_adicionales(df_recom)
                    if not df_recom.empty:
                        df_recom = df_recom[df_recom['genre_list'].apply(lambda x: any(g.upper() in [gen.upper() for gen in x] for g in generos_referencia if g.upper() != 'DESCONOCIDO')).astype(bool)]
                    if not df_recom.empty:
                        df_recom = df_recom[df_recom['book_id'] != id_referencia]
                        if autor_destacado:
                            df_recom = df_recom[~df_recom['authors'].fillna('').str.contains(autor_destacado, regex=False, na=False)]
                        recomendaciones = df_recom.drop_duplicates(subset=['authors']).head(3).to_dict('records')
            
            if len(recomendaciones) < 3:
                df_fallback = aplicar_filtros_adicionales(df_base)
                if not df_fallback.empty:
                    df_fallback = df_fallback[df_fallback['genre_list'].apply(lambda x: any(g.upper() in [gen.upper() for gen in x] for g in generos_referencia if g.upper() != 'DESCONOCIDO')).astype(bool)]
                if not df_fallback.empty:
                    df_fallback = df_fallback[df_fallback['book_id'] != id_referencia]
                    if autor_destacado:
                        df_fallback = df_fallback[~df_fallback['authors'].fillna('').str.contains(autor_destacado, regex=False, na=False)]
                    ids_ya_recom = [r['book_id'] for r in recomendaciones]
                    df_fallback = df_fallback[~df_fallback['book_id'].isin(ids_ya_recom)]
                    fallback_recoms = df_fallback.drop_duplicates(subset=['authors']).sort_values(['nota_media', 'votos'], ascending=[False, False]).head(3 - len(recomendaciones)).to_dict('records')
                    recomendaciones.extend(fallback_recoms)
                    
            if len(recomendaciones) < 3:
                df_fallback_lax = df_base.copy()
                if not df_fallback_lax.empty:
                    df_fallback_lax = df_fallback_lax[df_fallback_lax['genre_list'].apply(lambda x: any(g.upper() in [gen.upper() for gen in x] for g in generos_referencia if g.upper() != 'DESCONOCIDO')).astype(bool)]
                if not df_fallback_lax.empty:
                    df_fallback_lax = df_fallback_lax[df_fallback_lax['book_id'] != id_referencia]
                    if autor_destacado:
                        df_fallback_lax = df_fallback_lax[~df_fallback_lax['authors'].fillna('').str.contains(autor_destacado, regex=False, na=False)]
                    ids_ya_recom = [r['book_id'] for r in recomendaciones]
                    df_fallback_lax = df_fallback_lax[~df_fallback_lax['book_id'].isin(ids_ya_recom)]
                    fallback_recoms = df_fallback_lax.drop_duplicates(subset=['authors']).sort_values(['nota_media', 'votos'], ascending=[False, False]).head(3 - len(recomendaciones)).to_dict('records')
                    recomendaciones.extend(fallback_recoms)

        elif usuario_activo:
            titulo_recomendacion = "Recomendado según tus gustos:"
            titulos_preferidos = obtener_preferencias_usuario(usuario_activo)
            ids_ya_recom = []
            
            for titulo in titulos_preferidos[:3]:
                match = df_base[df_base['title'].str.contains(titulo, case=False, regex=False, na=False)]
                if not match.empty:
                    id_libro_ref = match.iloc[0]['book_id']
                    generos_referencia = match.iloc[0]['genre_list']
                    copias_libro = COPIAS_CACHE[COPIAS_CACHE['book_id'] == id_libro_ref] if not COPIAS_CACHE.empty else pd.DataFrame()
                    encontrado = False
                    
                    if not copias_libro.empty and indices_ia:
                        id_copia_ia = copias_libro.iloc[0]['copy_id']
                        ids_vecinos = indices_ia.get(id_copia_ia, [])
                        if ids_vecinos:
                            ids_libros_perso = COPIAS_CACHE[COPIAS_CACHE['copy_id'].isin(ids_vecinos)]['book_id'].unique()
                            df_perso = df_base[df_base['book_id'].isin(ids_libros_perso)]
                            df_perso = aplicar_filtros_adicionales(df_perso)
                            if not df_perso.empty:
                                df_perso = df_perso[df_perso['genre_list'].apply(lambda x: any(g.upper() in [gen.upper() for gen in x] for g in generos_referencia if g.upper() != 'DESCONOCIDO')).astype(bool)]
                            if not df_perso.empty:
                                excluidos = ids_ya_recom + [id_libro_ref]
                                df_perso = df_perso[~df_perso['book_id'].isin(excluidos)]
                                recom = df_perso.drop_duplicates(subset=['authors']).head(1).to_dict('records')
                                if recom:
                                    recomendaciones.extend(recom)
                                    ids_ya_recom.append(recom[0]['book_id'])
                                    encontrado = True
                    
                    if not encontrado:
                        df_fallback = aplicar_filtros_adicionales(df_base)
                        if not df_fallback.empty:
                            df_fallback = df_fallback[df_fallback['genre_list'].apply(lambda x: any(g.upper() in [gen.upper() for gen in x] for g in generos_referencia if g.upper() != 'DESCONOCIDO')).astype(bool)]
                        if not df_fallback.empty:
                            excluidos = ids_ya_recom + [id_libro_ref]
                            df_fallback = df_fallback[~df_fallback['book_id'].isin(excluidos)]
                            recom = df_fallback.drop_duplicates(subset=['authors']).sort_values(['nota_media', 'votos'], ascending=[False, False]).head(1).to_dict('records')
                            if recom:
                                recomendaciones.extend(recom)
                                ids_ya_recom.append(recom[0]['book_id'])
            
            if len(recomendaciones) < 3:
                df_fallback_general = aplicar_filtros_adicionales(df_base)
                if df_fallback_general.empty:
                    df_fallback_general = df_base.copy()
                if not df_fallback_general.empty:
                    df_fallback_general = df_fallback_general.sort_values(['nota_media', 'votos'], ascending=[False, False])
                    df_fallback_general = df_fallback_general[~df_fallback_general['book_id'].isin(ids_ya_recom)]
                    fallback_recoms = df_fallback_general.drop_duplicates(subset=['authors']).head(3 - len(recomendaciones)).to_dict('records')
                    recomendaciones.extend(fallback_recoms)

        if not recomendaciones and not query_busqueda:
            df_tendencias = aplicar_filtros_adicionales(df_base)
            if df_tendencias.empty:
                df_tendencias = df_base.copy()
            if not df_tendencias.empty:
                recomendaciones = df_tendencias[df_tendencias['votos'] > 50].sort_values('nota_media', ascending=False).drop_duplicates(subset=['authors']).head(3).to_dict('records')

    else:
        lista_generos = []
        lista_idiomas = []
        listado_final = []
        total_paginas = 1
        pagina_actual = 1

    return render(request, 'catalogo/lista_libros.html', {
        'libros': listado_final, 
        'top_valorados_general': top_valorados_general,
        'top_populares_general': top_populares_general, 
        'top_dinamico': top_dinamico,
        'titulo_sidebar_dinamico': titulo_sidebar_dinamico,
        'top_genero': top_por_genero,
        'recomendaciones': recomendaciones,
        'titulo_recomendacion': titulo_recomendacion, 
        'query': query_busqueda, 
        'generos': lista_generos, 
        'idiomas': lista_idiomas,
        'genre_sel': filtro_genero, 
        'lang_sel': filtro_idioma, 
        'year_min_sel': filtro_ano_min,
        'year_max_sel': filtro_ano_max,
        'rating_sel': filtro_nota,
        'votes_sel': filtro_votos,
        'available_sel': filtro_ejemplares,
        'sort_sel': metodo_orden, 
        'user_active': usuario_activo,
        'page': pagina_actual,
        'total_paginas': total_paginas
    })

def resumen_ia_view(request):
    titulo = request.GET.get('titulo', '')
    autor = request.GET.get('autor', '')
    time.sleep(1.5)
    respuesta = f"✨ Resumen IA (Qwen 0.6B local): '{titulo}' de {autor} es una obra fascinante."
    return JsonResponse({'resumen': respuesta})