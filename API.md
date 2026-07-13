# API Документация

## GET /files/<storage_name>
Получить список файлов в хранилище

**Параметры**: `path` - путь внутри хранилища

**Ответ**:
```json
{
  "files": [
    {"name": "file.txt", "is_dir": false, "size": "1.2 KB", "date": "01.01.2024 12:00"}
  ],
  "current_path": "folder",
  "full_path": "/path/to/storage/folder"
}