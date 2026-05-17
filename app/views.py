from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.db.models import Count, Avg
import pandas as pd
import os
import unicodedata
import re
import ast
from app.models import Book, Author, Copy, LibraryUser, Rating

BASE_CACHE = pd.DataFrame()
VOTOS_CACHE = pd.DataFrame()
TOP_VALORADOS_CACHE = None
TOP_POPULARES_CACHE = None
RECS_USER_CACHE = {}
RECS_BOOK_CACHE = {}

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

def parsear_generos(val):
    if pd.isna(val):
        return ['Desconocido']
    val_str = str(val).strip()
    if val_str.startswith('[') and val_str.endswith(']'):
        try:
            parsed = ast.literal_eval(val_str)
            if isinstance(parsed, list):
                return [str(g).strip().title() for g in parsed if g.strip()]
        except:
            pass
    return [g.strip().title() for g in val_str.split(',') if g.strip()]

def cargar_recomendaciones():
    global RECS_USER_CACHE, RECS_BOOK_CACHE
    if not RECS_USER_CACHE and os.path.exists('data/recs_usuarios.csv'):
        try:
            df_u = pd.read_csv('data/recs_usuarios.csv')
            RECS_USER_CACHE = df_u.set_index('user_id')[['rec_1', 'rec_2', 'rec_3']].apply(list, axis=1).to_dict()
        except: pass
    
    if not RECS_BOOK_CACHE and os.path.exists('data/recs_libros.csv'):
        try:
            df_b = pd.read_csv('data/recs_libros.csv')
            RECS_BOOK_CACHE = df_b.set_index('book_id')[['rec_1', 'rec_2', 'rec_3']].apply(list, axis=1).to_dict()
        except: pass

def cargar_datos_completos():
    global BASE_CACHE
    if not BASE_CACHE.empty:
        return BASE_CACHE.copy()

    try:
        books_qs = list(Book.objects.values('id', 'book_id', 'title', 'isbn', 'language_code', 'publication_year'))
        if books_qs:
            df_books = pd.DataFrame(books_qs)
            df_books['book_id'] = pd.to_numeric(df_books['book_id'], errors='coerce').fillna(0).astype(int)
            df_books.rename(columns={'publication_year': 'original_publication_year'}, inplace=True)

            try:
                m2m_qs = list(Book.authors.through.objects.values('book_id', 'author_id'))
                a_qs = list(Author.objects.values('id', 'name'))
                if m2m_qs and a_qs:
                    df_m2m = pd.DataFrame(m2m_qs).rename(columns={'book_id': 'book_pk'})
                    df_a = pd.DataFrame(a_qs).rename(columns={'id': 'author_id'})
                    df_merged = pd.merge(df_m2m, df_a, on='author_id')
                    pk_map = df_books[['id', 'book_id']].rename(columns={'id': 'book_pk'})
                    df_merged = pd.merge(df_merged, pk_map, on='book_pk')
                    autores = df_merged.groupby('book_id')['name'].apply(lambda x: ', '.join([str(i) for i in x if pd.notna(i)])).reset_index()
                    autores.rename(columns={'name': 'authors'}, inplace=True)
                    df_books = pd.merge(df_books, autores, on='book_id', how='left')
            except: pass

            df_books['authors'] = df_books.get('authors', pd.Series(['Desconocido']*len(df_books))).fillna('Desconocido')

            ruta_csv = 'data/books_with_genre.csv'
            if os.path.exists(ruta_csv):
                df_csv = pd.read_csv(ruta_csv, encoding='utf-8-sig')
                csv_pk = 'book_id' if 'book_id' in df_csv.columns else 'id'
                df_csv['book_id'] = pd.to_numeric(df_csv[csv_pk], errors='coerce').fillna(0).astype(int)
                missing_cols = [c for c in df_csv.columns if c not in df_books.columns and c != 'id']
                if missing_cols:
                    df_books = pd.merge(df_books, df_csv[['book_id'] + missing_cols], on='book_id', how='left')

            try:
                ruta_genres = 'data/book_genres.csv'
                if os.path.exists(ruta_genres):
                    df_g = pd.read_csv(ruta_genres, encoding='utf-8-sig')
                    g_pk = 'book_id' if 'book_id' in df_g.columns else 'id'
                    df_g[g_pk] = pd.to_numeric(df_g[g_pk], errors='coerce').fillna(0).astype(int)
                    generos_agrupados = df_g.groupby(g_pk)['genre'].apply(lambda x: [str(i).strip().title() for i in x if pd.notna(i)]).reset_index()
                    generos_agrupados.rename(columns={g_pk: 'book_id', 'genre': 'genre_list_multi'}, inplace=True)
                    df_books = pd.merge(df_books, generos_agrupados, on='book_id', how='left')
                    df_books['genre_list'] = df_books['genre_list_multi']
            except: pass

            if 'genre_list' not in df_books.columns:
                col_g = next((c for c in ['genres', 'genre'] if c in df_books.columns), None)
                if col_g:
                    df_books['genre_list'] = df_books[col_g].apply(parsear_generos)
                else:
                    df_books['genre_list'] = [['Desconocido']] * len(df_books)
                    
            df_books['genre_list'] = df_books['genre_list'].apply(lambda x: x if isinstance(x, list) else ['Desconocido'])

            df_books['original_publication_year'] = pd.to_numeric(df_books.get('original_publication_year', pd.Series([0]*len(df_books))), errors='coerce').fillna(0).astype(int)
            
            if 'language_code' in df_books.columns:
                df_books['language_display'] = df_books['language_code'].map(MAPA_IDIOMAS).fillna(df_books['language_code'])
            else:
                df_books['language_display'] = 'Desconocido'

            df_books['isbn'] = df_books.get('isbn', pd.Series(['N/A']*len(df_books))).fillna('N/A')
            df_books['title'] = df_books.get('title', pd.Series(['Sin título']*len(df_books))).fillna('Sin título')
            
            BASE_CACHE = df_books.drop_duplicates('book_id')
            return BASE_CACHE.copy()
    except: pass
    return pd.DataFrame()

def obtener_votos_totales():
    global VOTOS_CACHE
    if not VOTOS_CACHE.empty:
        return VOTOS_CACHE.copy()

    ruta_precalc = 'data/votos_precalculados.csv'
    if os.path.exists(ruta_precalc):
        try:
            df_votos = pd.read_csv(ruta_precalc, encoding='utf-8-sig')
            df_votos['book_id'] = pd.to_numeric(df_votos['book_id'], errors='coerce').fillna(0).astype(int)
            VOTOS_CACHE = df_votos
            return VOTOS_CACHE.copy()
        except: pass
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
            try: LibraryUser.objects.filter(user_id=user_id).delete()
            except: pass
            if request.session.get('user_id') == str(user_id):
                del request.session['user_id']
            return redirect('login')
            
    return render(request, 'login.html')

def logout_view(request):
    if 'user_id' in request.session: 
        del request.session['user_id']
    return redirect('login')

def registro_view(request):
    if request.method == 'POST':
        gustos = request.POST.get('gustos', '')
        fecha_nacimiento = request.POST.get('fecha_nacimiento', '')
        
        nuevo_id = 1
        try:
            max_user = LibraryUser.objects.order_by('-user_id').first()
            if max_user: nuevo_id = max_user.user_id + 1
            
            user = LibraryUser(user_id=nuevo_id)
            if hasattr(user, 'comment'): user.comment = gustos
            elif hasattr(user, 'preferences'): user.preferences = gustos
            
            if hasattr(user, 'birth_date'): user.birth_date = fecha_nacimiento
            elif hasattr(user, 'birthdate'): user.birthdate = fecha_nacimiento
            
            user.save()
        except: pass
            
        request.session['user_id'] = str(nuevo_id)
        return redirect('perfil')
        
    return render(request, 'registro.html')

def perfil_view(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')
        
    gustos_actuales = ""
    fecha_actual = ""
    
    try:
        user = LibraryUser.objects.filter(user_id=user_id).first()
        if user:
            gustos_actuales = str(getattr(user, 'comment', getattr(user, 'preferences', getattr(user, 'gustos', '')))).strip()
            fecha_actual = str(getattr(user, 'birth_date', getattr(user, 'birthdate', getattr(user, 'fecha_nacimiento', '')))).strip()
    except: pass

    if gustos_actuales in ['nan', 'None']: gustos_actuales = ""
    if fecha_actual in ['nan', 'None']: fecha_actual = ""
        
    if request.method == 'POST':
        nuevos_gustos = request.POST.get('gustos', '')
        nueva_fecha = request.POST.get('fecha_nacimiento', '')
        
        try:
            user = LibraryUser.objects.filter(user_id=user_id).first()
            if user:
                if hasattr(user, 'comment'): user.comment = nuevos_gustos
                elif hasattr(user, 'preferences'): user.preferences = nuevos_gustos
                if hasattr(user, 'birth_date'): user.birth_date = nueva_fecha
                elif hasattr(user, 'birthdate'): user.birthdate = nueva_fecha
                user.save()
        except: pass
        return redirect('buscador')
        
    return render(request, 'perfil.html', {'gustos': gustos_actuales, 'fecha': fecha_actual, 'user_id': user_id})

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
    
    try: pagina_actual = int(request.GET.get('page', 1))
    except ValueError: pagina_actual = 1

    usuario_activo = request.session.get('user_id')
    
    df_base = cargar_datos_completos()
    votos_df = obtener_votos_totales()
    top_valorados_general, top_populares_general = obtener_tops_generales()
    cargar_recomendaciones()
    
    recomendaciones = []
    top_dinamico = []
    titulo_sidebar_dinamico = ""
    top_por_genero = []
    autor_destacado = ""

    filtros_activos = False
    if query_busqueda.strip(): filtros_activos = True
    if filtro_genero.strip(): filtros_activos = True
    if filtro_idioma.strip(): filtros_activos = True
    if filtro_ano_min.strip(): filtros_activos = True
    if filtro_ano_max.strip(): filtros_activos = True
    if filtro_nota and str(filtro_nota) != '0': filtros_activos = True
    if filtro_votos and str(filtro_votos) != '0': filtros_activos = True
    if filtro_ejemplares == 'on': filtros_activos = True

    if filtros_activos:
        titulo_recomendacion = "Recomendado según tu búsqueda:"
    elif usuario_activo:
        titulo_recomendacion = "Recomendado según tus gustos:"
    else:
        titulo_recomendacion = "Tendencias Actuales en el Catálogo:"

    if not df_base.empty:
        if not votos_df.empty and 'book_id' in votos_df.columns:
            df_base = pd.merge(df_base, votos_df, on='book_id', how='left').fillna({'votos': 0, 'nota_media': 0})
        else:
            if 'votos' not in df_base.columns: df_base['votos'] = 0
            if 'nota_media' not in df_base.columns: df_base['nota_media'] = 0

        lista_generos = sorted(list(set(g for sublist in df_base['genre_list'] for g in sublist)))
        lista_idiomas = sorted(df_base['language_display'].dropna().unique().tolist())
        resultados_busqueda = df_base.copy()

        def aplicar_filtros_adicionales(df):
            res = df.copy()
            if filtro_genero and not res.empty:
                res = res[res['genre_list'].apply(lambda x: filtro_genero.lower() in [g.lower() for g in x]).astype(bool)]
            if filtro_idioma and not res.empty:
                res = res[res['language_display'] == filtro_idioma]
            if filtro_ano_min and not res.empty:
                try: res = res[res['original_publication_year'] >= int(filtro_ano_min)]
                except ValueError: pass
            if filtro_ano_max and not res.empty:
                try: res = res[res['original_publication_year'] <= int(filtro_ano_max)]
                except ValueError: pass
            if filtro_nota and str(filtro_nota) != '0' and not res.empty:
                try: res = res[res['nota_media'] >= float(filtro_nota)]
                except ValueError: pass
            if filtro_votos and str(filtro_votos) != '0' and not res.empty:
                try: res = res[res['votos'] >= int(filtro_votos)]
                except ValueError: pass
            
            if filtro_ejemplares == 'on' and not res.empty:
                try:
                    qs = list(Copy.objects.values_list('book__book_id', flat=True).distinct())
                    valid_books = [int(x) for x in qs if x is not None]
                    res = res[res['book_id'].isin(valid_books)]
                except: pass
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
            top_por_genero = df_base[df_base['genre_list'].apply(lambda x: filtro_genero.lower() in [g.lower() for g in x]).astype(bool)].sort_values(['nota_media', 'votos'], ascending=[False, False]).head(3).to_dict('records')

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

        if filtros_activos:
            if listado_final:
                id_referencia = listado_final[0]['book_id']
                recs_ids = RECS_BOOK_CACHE.get(id_referencia, [])
                
                if recs_ids:
                    df_recom = df_base[df_base['book_id'].isin(recs_ids)]
                    recomendaciones = df_recom.drop_duplicates(subset=['authors']).head(3).to_dict('records')
                
                if len(recomendaciones) < 3:
                    df_alternativa = df_base[~df_base['book_id'].isin([r['book_id'] for r in recomendaciones] + [id_referencia])]
                    new_recs = df_alternativa.sort_values(['nota_media', 'votos'], ascending=[False, False]).drop_duplicates(subset=['authors']).head(3 - len(recomendaciones)).to_dict('records')
                    recomendaciones.extend(new_recs)

        elif usuario_activo:
            texto_perfil = ""
            try:
                user = LibraryUser.objects.filter(user_id=usuario_activo).first()
                if user:
                    texto_perfil = str(getattr(user, 'comment', getattr(user, 'preferences', getattr(user, 'gustos', '')))).strip()
            except: pass
            
            ids_favoritos = []
            
            if texto_perfil and texto_perfil not in ['nan', 'None']:
                texto_perfil_lower = texto_perfil.lower()
                chunks = [c.strip() for c in re.split(r'\by\b|\bcomo\b|,|\.', texto_perfil_lower) if len(c.strip()) > 3]
                
                titles_series = df_base[df_base['title'].str.len() > 4]
                
                for chunk in chunks:
                    matches = df_base[df_base['title'].str.lower().str.contains(chunk, regex=False, na=False)]
                    if not matches.empty:
                        ids_favoritos.extend(matches['book_id'].tolist())
                        
                    mask = titles_series['title'].str.lower().apply(lambda x: x in chunk)
                    if mask.any():
                        ids_favoritos.extend(titles_series.loc[mask, 'book_id'].tolist())
                        
                ids_favoritos = list(set(ids_favoritos))

            for fid in ids_favoritos:
                recs_ids = RECS_BOOK_CACHE.get(fid, [])
                if recs_ids:
                    df_recom = df_base[df_base['book_id'].isin(recs_ids)]
                    df_recom = df_recom[~df_recom['book_id'].isin([r['book_id'] for r in recomendaciones] + ids_favoritos)]
                    new_recs = df_recom.drop_duplicates(subset=['authors']).head(3).to_dict('records')
                    recomendaciones.extend(new_recs)
                    if len(recomendaciones) >= 3: break
                    
            if len(recomendaciones) < 3:
                try:
                    uid = int(usuario_activo)
                    recs_ids = RECS_USER_CACHE.get(uid, [])
                    if recs_ids:
                        df_recom = df_base[df_base['book_id'].isin(recs_ids)]
                        df_recom = df_recom[~df_recom['book_id'].isin([r['book_id'] for r in recomendaciones] + ids_favoritos)]
                        new_recs = df_recom.drop_duplicates(subset=['authors']).head(3 - len(recomendaciones)).to_dict('records')
                        recomendaciones.extend(new_recs)
                except: pass
                
            if len(recomendaciones) < 3 and texto_perfil and texto_perfil not in ['nan', 'None']:
                generos_map = {
                    'ciencia ficcion': ['CIENCIA FICCIÓN', 'SCI-FI', 'SCIENCE FICTION'],
                    'terror': ['TERROR', 'HORROR', 'THRILLER'],
                    'fantasia': ['FANTASÍA', 'FANTASY'],
                    'romance': ['ROMÁNTICA', 'ROMANCE'],
                    'aventura': ['AVENTURA', 'ADVENTURE'],
                    'misterio': ['MISTERIO', 'MYSTERY'],
                    'thriller': ['THRILLER', 'SUSPENSE']
                }
                matched_genres = []
                txt_norm = normalizar_texto(texto_perfil)
                for k, v in generos_map.items():
                    if normalizar_texto(k) in txt_norm:
                        matched_genres.extend(v)
                        
                if matched_genres:
                    df_match = df_base[df_base['genre_list'].apply(lambda x: any(g.upper() in matched_genres for g in x)).astype(bool)]
                    df_match = df_match[~df_match['book_id'].isin([r['book_id'] for r in recomendaciones])]
                    new_recs = df_match.sort_values(['nota_media', 'votos'], ascending=[False, False]).drop_duplicates(subset=['authors']).head(3 - len(recomendaciones)).to_dict('records')
                    recomendaciones.extend(new_recs)

        if not recomendaciones:
            df_tendencias = aplicar_filtros_adicionales(df_base) if filtros_activos else df_base.copy()
            if not df_tendencias.empty:
                recomendaciones = df_tendencias[df_tendencias['votos'] > 50].sort_values('nota_media', ascending=False).drop_duplicates(subset=['authors']).head(3).to_dict('records')

    else:
        lista_generos = []
        lista_idiomas = []
        listado_final = []
        total_paginas = 1
        pagina_actual = 1

    return render(request, 'lista_libros.html', {
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
    
    ruta_sinopsis = 'data/sinopsis.csv'
    if os.path.exists(ruta_sinopsis):
        try:
            df_sinopsis = pd.read_csv(ruta_sinopsis)
            match = df_sinopsis[df_sinopsis['title'].str.lower() == titulo.lower()]
            if not match.empty:
                texto = match.iloc[0]['sinopsis']
                return JsonResponse({'resumen': f"Resumen extraido: {texto}"})
        except: pass

    respuesta_offline = f"El libro '{titulo}', escrito por {autor}, es una obra destacada en su género. Explora temas profundos con una narrativa envolvente, lo que lo convierte en una lectura recomendada en el catálogo."
    return JsonResponse({'resumen': f"Resumen IA: {respuesta_offline}"})