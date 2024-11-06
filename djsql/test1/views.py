from django.shortcuts import render
from django.http import JsonResponse
import pyodbc
import pandas as pd
from io import BytesIO

# Function to establish a database connection
def get_connection(driver, server, database, trusted_connection, username=None, password=None):
    try:
        if trusted_connection:
            conn = pyodbc.connect(
                f"Driver={{{driver}}};"
                f"Server={server};"
                f"Database={database};"
                "Trusted_Connection=yes;"
            )
        else:
            conn = pyodbc.connect(
                f"Driver={{{driver}}};"
                f"Server={server};"
                f"Database={database};"
                f"UID={username};"
                f"PWD={password};"
            )
        return conn
    except Exception as e:
        return str(e)

# Function to get databases
def get_databases(conn):
    query = "SELECT name FROM sys.databases"
    return pd.read_sql(query, conn)['name'].tolist()

# Function to get tables
def get_tables(conn, database):
    conn.execute(f"USE {database}")
    query = "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'"
    return pd.read_sql(query, conn)['TABLE_NAME'].tolist()

# Function to get table data with pagination
def get_table_data(conn, database, table_name, start, limit):
    conn.execute(f"USE {database}")
    query = f"SELECT * FROM {table_name} ORDER BY (SELECT NULL) OFFSET {start} ROWS FETCH NEXT {limit} ROWS ONLY"
    return pd.read_sql(query, conn)

def connect_to_sql(request):
    # Display connection form
    if request.method == 'POST':
        driver = request.POST.get('driver')
        server = request.POST.get('server')
        database = request.POST.get('database')
        trusted_connection = request.POST.get('trusted_connection') == 'on'
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Attempt connection
        conn = get_connection(driver, server, database, trusted_connection, username, password)
        if isinstance(conn, str):
            return render(request, 'connection_form.html', {'error': conn})
        else:
            # Save connection in session and redirect to explorer
            request.session['connection'] = driver, server, database, trusted_connection, username, password
            return render(request, 'explorer.html', {'databases': get_databases(conn)})

    return render(request, './templates/connection_form.html')

def load_tables(request):
    # Load tables for a selected database via AJAX
    if request.is_ajax():
        database = request.GET.get('database')
        driver, server, _, trusted_connection, username, password = request.session['connection']
        conn = get_connection(driver, server, database, trusted_connection, username, password)
        tables = get_tables(conn, database)
        return JsonResponse({'tables': tables})

def view_table_data(request):
    # Load table data for selected table via AJAX with pagination
    if request.is_ajax():
        database = request.GET.get('database')
        table = request.GET.get('table')
        page = int(request.GET.get('page', 1))
        page_size = 10
        start = (page - 1) * page_size

        driver, server, _, trusted_connection, username, password = request.session['connection']
        conn = get_connection(driver, server, database, trusted_connection, username, password)
        data = get_table_data(conn, database, table, start, page_size)
        
        return JsonResponse(data.to_dict(orient='records'), safe=False)
