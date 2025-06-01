import pandas as pd
import streamlit as st
from pyvis.network import Network
import networkx as nx
import ast
import re

# Кэшируем загрузку данных
@st.cache_data
def load_data():
    df = pd.read_json(r"C:\Users\User\Desktop\стримлит_граф_только_из_выборки\top_2000_dataset_starwars")
    
    
    # Агрегируем данные на уровне статей (document_id)
    aggregated = df.groupby('document_id').agg({
        'title': 'first',
        'outgoing_links': 'sum',
        'source': 'first'
    }).reset_index()
    
    # Преобразуем список ссылок в set для уникальности
    def flatten_links(links_list):
        flat_list = []
        for item in links_list:
            if isinstance(item, list):
                flat_list.extend(item)
            else:
                flat_list.append(item)
        return list(set(flat_list))
    
    aggregated['all_links'] = aggregated['outgoing_links'].apply(flatten_links)
    
    return aggregated

# Кэшируем создание графа
@st.cache_data(show_spinner="Building graph...")
def create_graph_data(df):
    # Создаем список всех уникальных страниц
    all_pages = df['document_id'].unique().tolist()
    
    # Создаем матрицу связей
    edges = []
    for _, row in df.iterrows():
        page = row['document_id']
        for link in row['all_links']:
            # Очищаем и нормализуем ссылку
            if isinstance(link, str):
                clean_link = re.sub(r'[^a-zA-Z0-9_]', '', link)
                if clean_link in all_pages: #вот ключевое отличие от другого графа, провекра на наличие в списке спарсенных страниц
                    edges.append((page, clean_link))
    
    # Считаем связи для каждого узла
    page_connections = {page: 0 for page in all_pages}
    for edge in edges:
        page_connections[edge[0]] += 1
        page_connections[edge[1]] += 1
    
    return all_pages, edges, page_connections

# Загрузка данных
df = load_data()

# Streamlit интерфейс
st.title("Граф связей Star Wars Wiki Fandom")
st.info("В качестве узлов используются только извлеченные сайты")

# Создаем данные для графа (кэшировано)
all_pages, edges, page_connections = create_graph_data(df)

# Фильтр для уменьшения количества узлов
min_connections = st.slider(
    "Минимальное количество связей для отображения узла", 
    min_value=0, 
    max_value=70, 
    value=10
)

# Дополнительный фильтр по максимальному количеству узлов
max_nodes = st.slider(
    "Максимальное количество узлов", 
    min_value=100, 
    max_value=900, 
    value=100
)

# Фильтруем узлы
filtered_pages = [p for p in all_pages if page_connections[p] >= min_connections]
filtered_pages = filtered_pages[:max_nodes]  # Ограничиваем количество
filtered_edges = [e for e in edges if e[0] in filtered_pages and e[1] in filtered_pages]

# Статистика
st.sidebar.header("📊 Статистика")
st.sidebar.metric("Всего статей", len(all_pages))
st.sidebar.metric("Всего связей", len(edges))
st.sidebar.metric("Отображаемых узлов", len(filtered_pages))
st.sidebar.metric("Отображаемых связей", len(filtered_edges))

# Кнопка для отображения графа (ленивая загрузка)
if st.button("Показать граф связей", type="primary"):
    if not filtered_pages or not filtered_edges:
        st.warning("Недостаточно данных для построения графа. Попробуйте уменьшить фильтры.")
    else:
        with st.spinner("Создание визуализации..."):
            # Создаем граф
            g = nx.DiGraph()
            
            # Добавляем узлы с размером, зависящим от количества связей
            for page in filtered_pages:
                size = min(50, 10 + page_connections[page] * 0.5)
                g.add_node(page, label=page, title=page, size=size)
            
            # Добавляем связи
            for edge in filtered_edges:
                g.add_edge(edge[0], edge[1])
            
            # Настраиваем визуализацию
            net = Network(
                height="700px", 
                width="100%", 
                bgcolor="#222222", 
                font_color="white",
                directed=True,
                notebook=False
            )
            
            # Оптимальные параметры для больших графов
            net.barnes_hut(
                gravity=-100000,
                central_gravity=0.5,
                spring_length=200,
                spring_strength=0.001,
                damping=0.2,
                overlap=0
            )
            
            net.from_nx(g)
            
            # Сохраняем и отображаем
            net.save_graph("graph.html")
            HtmlFile = open("graph.html", "r", encoding="utf-8")
            source_code = HtmlFile.read() 
            st.components.v1.html(source_code, height=720)

# Поиск конкретной статьи
st.sidebar.subheader("🔍 Поиск статьи")
search_term = st.sidebar.text_input("Введите название статьи")
if search_term:
    # Очищаем введенное значение
    clean_search = re.sub(r'[^a-zA-Z0-9_]', '', search_term)
    
    if clean_search in all_pages:
        # Входящие ссылки
        incoming = [e[0] for e in edges if e[1] == clean_search]
        # Исходящие ссылки
        outgoing = [e[1] for e in edges if e[0] == clean_search]
        
        st.subheader(f"Связи для: {clean_search}")
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**Входящие ссылки ({len(incoming)}):**")
            if incoming:
                # Группируем и сортируем по частоте
                incoming_df = pd.Series(incoming).value_counts().reset_index()
                incoming_df.columns = ['Статья', 'Количество']
                st.dataframe(incoming_df, height=300)
            else:
                st.write("Нет входящих ссылок")
        
        with col2:
            st.write(f"**Исходящие ссылки ({len(outgoing)}):**")
            if outgoing:
                # Группируем и сортируем по частоте
                outgoing_df = pd.Series(outgoing).value_counts().reset_index()
                outgoing_df.columns = ['Статья', 'Количество']
                st.dataframe(outgoing_df, height=300)
            else:
                st.write("Нет исходящих ссылок")
    else:
        st.sidebar.warning("Статья не найдена")

# Топ самых связанных статей
st.sidebar.subheader("🏆 Топ связанных статей")
top_pages = sorted(page_connections.items(), key=lambda x: x[1], reverse=True)[:10]

# Находим максимальное количество связей для нормализации прогресс-баров
max_connections = max(page_connections.values()) if page_connections else 1

for page, count in top_pages:
    progress_value = min(count / max_connections, 1.0)
    st.sidebar.progress(progress_value, text=f"{page}: {count} связей")