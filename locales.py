LOCALES = {
    "ru": {
        "app_title": "Заметки",
        "add": "Добавить",
        "edit": "Редактировать",
        "delete": "Удалить",
        "search": "Поиск",
        "sort_asc": "Сортировка ↑",
        "sort_desc": "Сортировка ↓",
        "export": "Экспорт",
        "stats": "Статистика",
        "refresh": "Обновить",
        "confirm_delete": "Удалить выбранную заметку?",
        "empty_note_error": "Текст заметки не может быть пустым.",
        "no_notes": "Заметок нет.",
        "created_at": "Создано",
        "updated_at": "Изменено",
        "deleted_msg": "Заметка перемещена в удалённые.",
        "export_done": "Экспорт завершён",
        "language": "Язык",
        "search_placeholder": "Введите ключевое слово"
    },
    "en": {
        "app_title": "Notes",
        "add": "Add",
        "edit": "Edit",
        "delete": "Delete",
        "search": "Search",
        "sort_asc": "Sort ↑",
        "sort_desc": "Sort ↓",
        "export": "Export",
        "stats": "Statistics",
        "refresh": "Refresh",
        "confirm_delete": "Delete selected note?",
        "empty_note_error": "Note text cannot be empty.",
        "no_notes": "No notes.",
        "created_at": "Created",
        "updated_at": "Updated",
        "deleted_msg": "Note deleted.",
        "export_done": "Export completed",
        "language": "Language",
        "search_placeholder": "Enter keyword"
    }
}


def t(locale, key):
    """Быстрая функция доступа к переводам"""
    return LOCALES.get(locale, LOCALES["ru"]).get(key, key)
