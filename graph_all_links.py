import pandas as pd
import streamlit as st
from pyvis.network import Network
import networkx as nx
import re
import time

# Заголовок веб-приложения
st.title("Граф связей Star Wars Wiki Fandom")
st.info("Учитываются все статьи, даже которые не были спарсены")

# Кэшируем загрузку данных
@st.cache_data
def load_data():
    try:
        # Загрузка данных (с выводо результата успех\неуспех)
        df = pd.read_json(r"C:\Users\User\Desktop\стримлит_граф_все_линки\top_10_dataset_starwars")
        st.success("Данные успешно загружены!")
        return df
    except Exception as e:
        st.error(f"Ошибка загрузки данных: {str(e)}")
        return pd.DataFrame()

# Загрузка данных
df = load_data()

# Проверка на пустые данные
if df.empty:
    st.stop()

# Прогресс-бар для обработки данных
progress_bar = st.progress(0)
status_text = st.empty()

# Функция для нормализации идентификаторов (убираем все, кроме цифр, букв и нижних подчеркиваний)
def normalize_id(node_id):
    return re.sub(r'[^a-zA-Z0-9_]', '', str(node_id))

# Функция для обработки данных
def process_data(df):
    status_text.text("Обработка данных... 0%")
    
    # Нормализация document_id
    df['document_id'] = df['document_id'].apply(normalize_id)
    progress_bar.progress(10)
    status_text.text("Обработка данных... 10%")
    
    # Сбор всех уникальных узлов из document_id, это как раз будут первичные узлы
    all_nodes = set(df['document_id'].unique())
    progress_bar.progress(20)
    status_text.text("Обработка данных... 20%")
    
    # Сбор всех ссылок
    all_links = []
    for links in df['outgoing_links']:
        if isinstance(links, list):
            all_links.extend(links) #Используем extend, чтобы добавлялись именно slug'и из списков как отдельный элементы, а не сами списки
    
    # Нормализация ссылок и добавление в узлы
    normalized_links = [normalize_id(link) for link in all_links if isinstance(link, str)] #нормализуем внешние ссылки
    all_nodes.update(normalized_links) #дабавляем к основным узлам-статьям, которые были спарсены
    
    progress_bar.progress(50)
    status_text.text("Обработка данных... 50%")
    
    # Создание связей
    edges = []
    for _, row in df.iterrows():
        source = normalize_id(row['document_id'])
        if isinstance(row['outgoing_links'], list):
            for link in row['outgoing_links']:
                if isinstance(link, str):
                    target = normalize_id(link)
                    edges.append((source, target))
    
    progress_bar.progress(80)
    status_text.text("Обработка данных... 80%")
    
    #Подсчет связей
    node_connections = {}
    for node in all_nodes:
        # Исходящие + входящие связи
        out_count = sum(1 for s, t in edges if s == node)
        in_count = sum(1 for s, t in edges if t == node)
        node_connections[node] = out_count + in_count
    
    progress_bar.progress(100)
    status_text.text("Обработка данных завершена!")
    time.sleep(0.5)
    status_text.empty()
    progress_bar.empty()
    
    return list(all_nodes), edges, node_connections

# Обработка данных
all_nodes, edges, node_connections = process_data(df)

# Фильтрация
st.sidebar.header("🔧 Фильтры")

# Фильтр по связям
min_connections = st.sidebar.slider(
    "Минимальное количество связей", 
    min_value=0, 
    max_value=70, 
    value=10
)

# Фильтр по количеству узлов
max_nodes = st.sidebar.slider(
    "Максимальное количество узлов", 
    min_value=100, 
    max_value=1000, 
    value=100
)

# Применение фильтров
filtered_nodes = [n for n in all_nodes if node_connections.get(n, 0) >= min_connections]
filtered_nodes = filtered_nodes[:max_nodes]
filtered_edges = [(s, t) for s, t in edges if s in filtered_nodes and t in filtered_nodes]

# Статистика
st.sidebar.header("📊 Статистика")
st.sidebar.metric("Всего узлов", len(all_nodes))
st.sidebar.metric("Всего связей", len(edges))
st.sidebar.metric("Отображаемых узлов", len(filtered_nodes))
st.sidebar.metric("Отображаемых связей", len(filtered_edges))

# Кнопка для построения графа
if st.button("Построить граф", type="primary", use_container_width=True):
    if not filtered_nodes or not filtered_edges:
        st.warning("Недостаточно данных для построения графа. Уменьшите фильтры.")
    else:
        with st.spinner("Построение графа..."):
            # Создаем граф
            g = nx.DiGraph()
            
            # Добавляем узлы
            for node in filtered_nodes:
                connections = node_connections.get(node, 0)
                size = max(5, min(30, connections / 5))  # Динамический размер
                g.add_node(node, label=node, title=f"{node}\nСвязей: {connections}", size=size)
            
            # Добавляем связи
            for source, target in filtered_edges:
                g.add_edge(source, target)
            
            # Настраиваем визуализацию
            net = Network(
                height="600px", 
                width="100%", 
                bgcolor="#222222", 
                font_color="white",
                directed=True,
                notebook=False
            )
            
            # Оптимальные параметры
            net.barnes_hut(
                gravity=-30000,
                central_gravity=0.1,
                spring_length=100,
                spring_strength=0.002,
                damping=0.2,
                overlap=0.1
            )
            
            # Конвертируем и сохраняем
            net.from_nx(g)
            net.save_graph("graph.html")
            
            # Отображаем
            HtmlFile = open("graph.html", "r", encoding="utf-8")
            source_code = HtmlFile.read()
            st.components.v1.html(source_code, height=650)
            
            st.success("Граф успешно построен!")

# Поисковая система
st.sidebar.header("🔍 Поиск по графу")
search_term = st.sidebar.text_input("Введите название узла")

if search_term:
    clean_search = normalize_id(search_term)
    
    if clean_search in all_nodes:
        # Входящие ссылки
        incoming = [s for s, t in edges if t == clean_search]
        # Исходящие ссылки
        outgoing = [t for s, t in edges if s == clean_search]
        
        st.subheader(f"🔗 Связи узла: {clean_search}")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Входящие связи", len(incoming))
            if incoming:
                st.dataframe(pd.DataFrame(incoming, columns=["Источник"]), height=200)
        
        with col2:
            st.metric("Исходящие связи", len(outgoing))
            if outgoing:
                st.dataframe(pd.DataFrame(outgoing, columns=["Цель"]), height=200)
    else:
        st.sidebar.warning("Узел не найден")

# Топ узлов
st.sidebar.header("🏆 Топ узлов по связям")
if node_connections:
    top_nodes = sorted(node_connections.items(), key=lambda x: x[1], reverse=True)[:10]
    
    for node, count in top_nodes:
        st.sidebar.caption(f"• {node[:20]}{'...' if len(node) > 20 else ''}: {count} связей")