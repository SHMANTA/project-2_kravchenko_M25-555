from typing import Any, Dict, List, Tuple

from ..decorators import confirm_action, create_cacher, handle_db_errors, log_time

VALID_TYPES = {"int", "str", "bool"}
select_cache = create_cacher()


def _cast_value(token: Any, dtype: str):
    if dtype == "int":
        if isinstance(token, int):
            return token
        if (
            isinstance(token, str) and 
            token.isdigit() or
            (isinstance(token, str) and token.lstrip("-").isdigit())):
            return int(token)
        raise ValueError(f"Ожидалось int, получили: {token!r}")
    if dtype == "bool":
        if isinstance(token, bool):
            return token
        if isinstance(token, str):
            v = token.lower()
            if v in ("true", "false"):
                return v == "true"
        raise ValueError(f"Ожидалось bool (true/false), получили: {token!r}")
    if dtype == "str":
        if isinstance(token, str):
            return token
        return str(token)
    raise ValueError(f"Неизвестный тип {dtype}")


def create_table(metadata: dict, table_name: str, columns_raw: List[str]) -> dict:
    if table_name in metadata:
        print(f'Ошибка: Таблица "{table_name}" уже существует.')
        return metadata

    columns: List[Tuple[str, str]] = []
    columns.append(("ID", "int"))

    for col in columns_raw:
        if ":" not in col:
            print(f"Некорректное значение: {col}. Попробуйте снова.")
            return metadata
        name, dtype = col.split(":", 1)
        name = name.strip()
        dtype = dtype.strip()
        if not name:
            print(f"Некорректное имя столбца: {col}.")
            return metadata
        if dtype not in VALID_TYPES:
            print(f"Некорректный тип {dtype}. Допустимые: int, str, bool.")
            return metadata
        columns.append((name, dtype))

    metadata[table_name] = {"columns": columns}
    cols_str = ", ".join([f"{n}:{t}" for n, t in columns])
    print(f'Таблица "{table_name}" успешно создана со столбцами: {cols_str}')
    return metadata


@handle_db_errors
@confirm_action("удаление таблицы")
def drop_table(metadata: dict, table_name: str) -> dict:
    if table_name not in metadata:
        print(f'Ошибка: Таблица "{table_name}" не существует.')
        return metadata
    del metadata[table_name]
    print(f'Таблица "{table_name}" успешно удалена.')
    return metadata


def list_tables(metadata: dict) -> None:
    if not metadata:
        print("Нет созданных таблиц.")
        return
    for table in metadata:
        print(f"- {table}")


@handle_db_errors
@log_time
def insert(metadata: dict, table_name: str, values: List[Any], table_data: List[Dict]):
    if table_name not in metadata:
        print(f'Ошибка: Таблица "{table_name}" не существует.')
        return table_data

    columns = metadata[table_name]["columns"]
    expected_fields = columns[1:]  # исключаем ID
    if len(values) != len(expected_fields):
        print(f"Некорректное значение: ожидается "
              f"{len(expected_fields)} значений, передано {len(values)}.")
        return table_data

    record = {}
    existing_ids = [
        r.get("ID", 0) for r in table_data if isinstance(r.get("ID", None), int)
        ]
    next_id = max(existing_ids, default=0) + 1
    record["ID"] = next_id

    for (col_name, col_type), val in zip(expected_fields, values):
        try:
            casted = _cast_value(val, col_type)
        except ValueError as e:
            print(f"Некорректное значение: {val}. {e}")
            return table_data
        record[col_name] = casted

    table_data.append(record)
    print(f'Запись с ID={record["ID"]} успешно добавлена в таблицу "{table_name}".')
    return table_data


@handle_db_errors
@log_time
def select(metadata, table_name, table_data, where_clause=None):
    key = str(where_clause)

    def retrieve():
        if where_clause is None:
            return table_data

        col, val = list(where_clause.items())[0]
        return [
            row for row in table_data
            if str(row.get(col)) == str(val)
        ]

    return select_cache(key, retrieve)

@handle_db_errors
def update(
    metadata: dict,
    table_name: str,
    table_data: List[Dict[str, Any]],
    set_clause: Dict[str, Any],
    where_clause: Dict[str, Any]
    ):
    if table_name not in metadata:
        print(f'Ошибка: Таблица "{table_name}" не существует.')
        return table_data, 0

    columns = dict(metadata[table_name]["columns"]) 
    updated_count = 0

    for rec in table_data:
        match = True
        for k, v in where_clause.items():
            if rec.get(k) != v:
                match = False
                break
        if not match:
            continue

        for k, v in set_clause.items():
            if k not in columns:
                print(f"Некорректное значение: столбца {k} нет.")
                return table_data, updated_count
            dtype = columns[k]
            try:
                rec[k] = _cast_value(v, dtype)
            except ValueError as e:
                print(f"Некорректное значение: {v}. {e}")
                return table_data, updated_count
        updated_count += 1

    if updated_count > 0:
        print(f"Запись(и) обновлены: {updated_count}")
    else:
        print("Ни одна запись не удовлетворяет условию.")
    return table_data, updated_count


@handle_db_errors
@confirm_action("удаление записей")
def delete(
    metadata: dict,
    table_name: str,
    table_data: List[Dict[str, Any]],
    where_clause: Dict[str, Any]
    ):
    if table_name not in metadata:
        print(f'Ошибка: Таблица "{table_name}" не существует.')
        return table_data, 0

    def match(rec):
        for k, v in where_clause.items():
            if rec.get(k) != v:
                return False
        return True

    new_data = []
    deleted = 0
    for rec in table_data:
        if match(rec):
            deleted += 1
            continue
        new_data.append(rec)

    if deleted > 0:
        print(f"Запись(и) удалены: {deleted}")
    else:
        print("Ни одна запись не удовлетворяет условию.")
    return new_data, deleted


def info(metadata: dict, table_name: str, table_data: List[Dict[str, Any]]):
    if table_name not in metadata:
        print(f'Ошибка: Таблица "{table_name}" не существует.')
        return
    columns = metadata[table_name]["columns"]
    cols_str = ", ".join([f"{n}:{t}" for n, t in columns])
    print(f"Таблица: {table_name}")
    print(f"Столбцы: {cols_str}")
    print(f"Количество записей: {len(table_data)}")
