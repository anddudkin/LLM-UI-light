import os
from pathlib import Path


def create_basic_structure():
    """Создает базовую структуру папок"""
    from dotenv import load_dotenv
    load_dotenv()
    base_dir = Path(os.environ["LOCAL_STORAGE"])

    # Создаем основные папки

    users_dir = base_dir / "user_files"
    #audio_dir = base_dir / "user_files" / "audio_files"

    try:
        # Создаем корневую папку и подпапки
        #audio_dir.mkdir(parents=True, exist_ok=True)
        users_dir.mkdir(parents=True, exist_ok=True)

        print("Структура папок создана:")
        print(f"  {base_dir}")
        print(f"  └── user_files")
        print("\nГотово!")

    except Exception as e:
        print(f"Ошибка: {e}")

def add_user_folder(user_id):
    user_path = Path(f"{os.environ["LOCAL_STORAGE"]}/user_files") / str(user_id)
    user_path.mkdir(parents=True, exist_ok=True)
    user_audio_path = user_path / "audio_files"
    user_audio_path.mkdir(parents=True, exist_ok=True)
    return user_path
# Запуск создания структуры
if __name__ == "__main__":
    create_basic_structure()