# Primitive DB — учебная файловая СУБД на Python

Проект представляет собой примитивную файловую базу данных, реализованную в рамках учебного задания.  
Система позволяет выполнять базовые операции с таблицами:  
создание, удаление, вставку данных, выборку, обновление и удаление записей.

Проект создан с использованием инструментов:
- **Poetry** — управление зависимостями
- **Ruff** — автоматическая проверка качества кода
- **asciinema** — запись демонстрации работы проекта
- **Python 3.12**
- **Декораторы** и **замыкания** для повышения качества кода

---

### Установка зависимостей:
```bash
make install
```

### Запуск программы:
```bash
make project
```

### Сборка пакета:
```bash
make build
```

### Тестовая публикация:
```bash
make publish
```

### Линтер:
```bash
make lint
```

***
Поддерживаемые команды:

* create table \<name\> (<columns>)
* drop table <name>
* insert into <table> values (...)
* select * from <table> [where ...]
* update <table> set ... where ...
* delete from <table> where ...
* show tables
* help
* exit

[![asciicast](https://asciinema.org/a/PTx53BUOVtzy1gq8jj0zhFYsM.svg)](https://asciinema.org/a/PTx53BUOVtzy1gq8jj0zhFYsM)