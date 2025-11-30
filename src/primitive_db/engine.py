import re
import shlex

from prettytable import PrettyTable

from .core import (
    create_table,
    delete,
    drop_table,
    info,
    insert,
    list_tables,
    select,
    update,
)
from .utils import (
    load_metadata,
    load_table_data,
    save_metadata,
    save_table_data,
)

META_FILE = "db_meta.json"


def print_help():
    print("\n***Операции с данными***")
    print("Функции:")
    print("insert into <имя_таблицы> values (<val1>, <val2>, ...)")
    print("select from <имя_таблицы> [where <col> = <value>]")
    print("update <имя_таблицы> set <col>=<val> [ , ... ] where <col>=<val>")
    print("delete from <имя_таблицы> where <col> = <value>")
    print("info <имя_таблицы>")
    print("\nОбщие команды:")
    print("create_table <имя> <col:type> ...")
    print("drop_table <имя>")
    print("list_tables")
    print("help")
    print("exit\n")


def _split_values_list(values_str: str):
    tokens = re.findall(r'"[^"]*"|\'[^\']*\'|[^,\s]+', values_str)
    parsed = []
    for t in tokens:
        t = t.strip()
        if (
            t.startswith('"') and 
            t.endswith('"')) or (t.startswith("'") and t.endswith("'")):
            parsed.append(t[1:-1])
        else:
            parsed.append(t.strip().rstrip(","))
    return parsed


def _parse_assignment(expr: str):
    if "=" not in expr:
        raise ValueError(f"Некорректное выражение: {expr}")
    left, right = expr.split("=", 1)
    key = left.strip()
    val = right.strip()
    if (
        val.startswith('"') and
        val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
        val = val[1:-1]
    low = val.lower()
    if low == "true":
        return key, True
    if low == "false":
        return key, False
    if re.fullmatch(r"-?\d+", val):
        return key, int(val)
    return key, val


def _parse_where(expr: str):
    expr = expr.strip()
    if not expr:
        return {}
    try:
        k, v = _parse_assignment(expr)
        return {k: v}
    except ValueError:
        raise


def _parse_set(expr: str):
    parts = re.split(r",\s*(?![^()]*\))", expr)
    out = {}
    for p in parts:
        if not p.strip():
            continue
        k, v = _parse_assignment(p)
        out[k] = v
    return out


def run():
    print("***База данных (CRUD)***")
    print_help()

    while True:
        user_input = input("Введите команду: ").strip()
        if not user_input:
            continue

        try:
            args = shlex.split(user_input)
        except ValueError:
            print("Некорректная команда. Попробуйте снова.")
            continue

        metadata = load_metadata(META_FILE)

        cmd = args[0].lower()

        if cmd == "exit":
            print("Выход...")
            break

        if cmd == "help":
            print_help()
            continue

        if cmd == "create_table":
            if len(args) < 3:
                print("Некорректное значение." 
                      "Формат: create_table <имя> <col:type> ...")
                continue
            name = args[1]
            cols = args[2:]
            metadata = create_table(metadata, name, cols)
            save_metadata(META_FILE, metadata)
            continue

        if cmd == "drop_table":
            if len(args) != 2:
                print("Некорректное значение: требуется имя таблицы.")
                continue
            name = args[1]
            metadata = drop_table(metadata, name)
            save_metadata(META_FILE, metadata)
            continue

        if cmd == "list_tables":
            list_tables(metadata)
            continue

        m = re.match(
            r'^insert\s+into\s+(\w+)\s+values\s*\((.*)\)\s*$',
            user_input, 
            flags=re.IGNORECASE | re.DOTALL
            )
        if m:
            table_name = m.group(1)
            values_str = m.group(2)
            try:
                tokens = _split_values_list(values_str)
            except Exception:
                print("Некорректное значение: неверный синтаксис списка значений.")
                continue
            table_data = load_table_data(table_name)
            updated = insert(metadata, table_name, tokens, table_data)
            save_table_data(table_name, updated)
            continue

        m = re.match(
            r'^select\s+from\s+(\w+)(?:\s+where\s+(.*))?$', 
            user_input,
            flags=re.IGNORECASE | re.DOTALL
            )
        if m:
            table_name = m.group(1)
            where_expr = m.group(2)
            table_data = load_table_data(table_name)
            where_clause = None
            if where_expr:
                try:
                    where_clause = _parse_where(where_expr)
                except Exception:
                    print(f"Некорректное значение: {where_expr}. Попробуйте снова.")
                    continue
            results = select(metadata, table_name, table_data, where_clause)
            if not results:
                print("Ничего не найдено.")
                continue
            cols = [c[0] for c in metadata[table_name]["columns"]]
            pt = PrettyTable()
            pt.field_names = cols
            for r in results:
                row = [r.get(col, "") for col in cols]
                pt.add_row(row)
            print(pt)
            continue

        m = re.match(
            r'^update\s+(\w+)\s+set\s+(.*?)\s+where\s+(.*)$', 
            user_input,
            flags=re.IGNORECASE | re.DOTALL
            )
        if m:
            table_name = m.group(1)
            set_expr = m.group(2)
            where_expr = m.group(3)
            try:
                set_clause = _parse_set(set_expr)
                where_clause = _parse_where(where_expr)
            except Exception:
                print("Некорректное значение в SET или WHERE. Попробуйте снова.")
                continue
            table_data = load_table_data(table_name)
            updated_data, count = update(
                metadata,
                table_name,
                table_data,
                set_clause,
                where_clause
                )
            if count > 0:
                save_table_data(table_name, updated_data)
            continue

        m = re.match(
            r'^delete\s+from\s+(\w+)\s+where\s+(.*)$', 
            user_input,
            flags=re.IGNORECASE | re.DOTALL
            )
        if m:
            table_name = m.group(1)
            where_expr = m.group(2)
            try:
                where_clause = _parse_where(where_expr)
            except Exception:
                print("Некорректное значение в WHERE. Попробуйте снова.")
                continue
            table_data = load_table_data(table_name)
            new_data, deleted = delete(metadata, table_name, table_data, where_clause)
            if deleted > 0:
                save_table_data(table_name, new_data)
            continue

        m = re.match(r'^info\s+(\w+)$', user_input, flags=re.IGNORECASE)
        if m:
            table_name = m.group(1)
            table_data = load_table_data(table_name)
            info(metadata, table_name, table_data)
            continue

        print(f"Функции {args[0]} нет. Попробуйте снова.")
