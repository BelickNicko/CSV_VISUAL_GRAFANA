import os
import yaml
import pandas as pd
from clickhouse_driver import Client
from datetime import datetime

CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST")
CLICKHOUSE_PORT = int(os.getenv("CLICKHOUSE_PORT"))
CLICKHOUSE_USER = os.getenv("CLICKHOUSE_USER")
CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD")
CLICKHOUSE_DB = os.getenv("CLICKHOUSE_DB")

CSV_DIR = os.getenv("CSV_DIR")
YAML_FILE = "all_schemas.yaml"
client = Client(
    host=CLICKHOUSE_HOST,
    port=CLICKHOUSE_PORT,
    user=CLICKHOUSE_USER,
    password=CLICKHOUSE_PASSWORD,
    database=CLICKHOUSE_DB,
)

def load_yaml_config(file_path):
    """Загрузка конфигурации из YAML-файла."""
    with open(file_path, "r") as f:
        config = yaml.safe_load(f)
    return config

def create_table(table_name, columns, file_path):
    """Создание таблицы в ClickHouse."""
    df = pd.read_csv(file_path)

    columns_sql = ", ".join(
        [
            f"{column} {columns[column]}" if column in columns else f"position_{i} String"
            for i, column in enumerate(df.columns)
        ]
    )
    create_table_sql = (
        f"CREATE TABLE IF NOT EXISTS {CLICKHOUSE_DB}.{table_name} ({columns_sql}) "
        f"ENGINE = MergeTree() ORDER BY {list(columns)[0]};"
    )
    print(f"SQL-запрос для создания таблицы:\n{create_table_sql}")
    client.execute(create_table_sql)

def convert_to_clickhouse_type(value, column_type):
    """Преобразование значений в типы, совместимые с ClickHouse."""
    if pd.isna(value):  # Проверка на NaN или NaT
        return None

    if column_type == "DateTime":
        if isinstance(value, pd.Timestamp):
            return value.to_pydatetime()
        elif isinstance(value, str):
            try:
                return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                return None
    elif column_type == "Date":
        if isinstance(value, pd.Timestamp):
            return value.date()
        elif isinstance(value, str):
            try:
                return datetime.strptime(value, "%Y-%m-%d").date()
            except ValueError:
                return None
    elif column_type == "Int32":
        try:
            return int(value)
        except ValueError:
            return None
    elif column_type == "Float64":
        try:
            return float(value)
        except ValueError:
            return None
    elif column_type == "String":
        return str(value)

    return value


def process_csv(file_path, table_name, columns):
    """Обработка CSV-файла и загрузка данных в ClickHouse."""
    print(f"Обработка файла: {file_path}, таблица: {table_name}")

    df = pd.read_csv(file_path)
    data = []
    for row in df.itertuples(index=False, name=None):
        processed_row = [
            (
                convert_to_clickhouse_type(value, columns[df.columns[i]])
                if df.columns[i] in columns
                else convert_to_clickhouse_type(value, "String") 
            )
            for i, value in enumerate(row)
        ]
      
        data.append(tuple(processed_row))
    columns_sql = ", ".join(
        [
            f"{column}" if column in columns else f"position_{i}"
            for i, column in enumerate(df.columns)
        ]
    )
    insert_query = f"INSERT INTO {CLICKHOUSE_DB}.{table_name} ({columns_sql}) VALUES"

    client.execute(insert_query, data)

    print(f"Данные из файла {file_path} загружены в таблицу {table_name}")


def main():
    config = load_yaml_config(YAML_FILE)

    for file_name in os.listdir(CSV_DIR):
        if file_name.endswith(".csv"):
            table_name = os.path.splitext(file_name)[0]
            if table_name in config["tables"]:
                file_path = os.path.join(
                    CSV_DIR,
                    file_name,
                )
                create_table(table_name, config["tables"][table_name], file_path)
                process_csv(file_path, table_name, config["tables"][table_name])
            else:
                print(f"Таблица для файла {file_name} не найдена в YAML-конфигурации.")


if __name__ == "__main__":
    main()
