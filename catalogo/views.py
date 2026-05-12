from django.shortcuts import render, redirect
import pandas as pd
import os
import unicodedata
import re
import pickle

# Carga del "cerebro" de la IA al iniciar el servidor
INDICES_IA_PATH = 'catalogo/indices_ia.pkl'
indices_ia = {}
if os.path.exists(INDICES_IA_PATH):
    with open(INDICES_IA_PATH, 'rb') as f:
        indices_ia = pickle.load(f)

def normalizar_texto(texto):
    if not isinstance(texto, str): return ""
    texto = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('utf-8')
    return re.sub(r'[^a-zA-Z0-9]', '', texto).lower()

def login_view(request):
    if request.method == 'POST':
        request.session['user_id'] = request.POST.get('user_id')
        return redirect('buscador')
    return render(request, 'catalogo/login.html')

def logout_view(request):
    if 'user_id' in request.session: del request.session['user_id']
    return redirect('login')

def buscador_catalogo(request):
    query = request.GET.get('q', '')
    # Usamos los datos limpios de Jose Luis (Fase 4 del PMP)
    ruta_books = 'data/clean/books_clean.csv'
    user_active = request.session.get('user_id')
    recomendaciones = []
    
    # Dashboard: Top 5 libros (Datos del PMP)
    top_libros = [
        {'title': 'The Hunger Games', 'authors': 'Suzanne Collins', 'ratings': 22806, 'pct': 100},
        {'title': "Harry Potter and the Sorcerer's Stone", 'authors': 'J.K. Rowling', 'ratings': 21850, 'pct': 95},
        {'title': 'To Kill a Mockingbird', 'authors': 'Harper Lee', 'ratings': 19088, 'pct': 83}
    ]
    
    if os.path.exists(ruta_books):
        df = pd.read_csv(ruta_books)
        
        if query:
            q_norm = normalizar_texto(query)
            df['title_norm'] = df['title'].apply(normalizar_texto)
            df['authors_norm'] = df['authors'].apply(normalizar_texto)
            resultados = df[(df['title_norm'].str.contains(q_norm, na=False)) | (df['authors_norm'].str.contains(q_norm, na=False))].head(20)
            
            # IA REAL (RF-04): "Quien leyó X también disfrutó Y"
            if not resultados.empty and indices_ia:
                # Buscamos recomendaciones para el ID del primer libro encontrado
                book_id_buscado = resultados.iloc[0]['book_id']
                # Nota: El índice usa copy_id/book_id según el entrenamiento
                ids_recomendados = indices_ia.get(book_id_buscado, [])
                if ids_recomendados:
                    recomendaciones = df[df['book_id'].isin(ids_recomendados)].head(3).to_dict('records')
        else:
            resultados = df.head(10)
    else:
        resultados = pd.DataFrame()

    return render(request, 'catalogo/lista_libros.html', {
        'libros': resultados.to_dict('records'), 
        'top_libros': top_libros,
        'recomendaciones': recomendaciones,
        'query': query,
        'user_active': user_active
    })