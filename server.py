"""
Тренажёр олимпиадной информатики — сервер Flask.
Эндпоинты:
  GET  /api/tasks         — список всех задач
  POST /api/generate      — генерация задачи через DeepSeek
  POST /api/submit        — проверка решения на тестах
  GET  /                  — отдача index.html
"""
import json
import os
import sys
import subprocess
import tempfile
import uuid
import re
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory

# Добавляем текущую директорию в путь для импорта task_create
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import task_create

app = Flask(__name__, static_folder='static', static_url_path='/static')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_JSON_PATH = os.path.join(BASE_DIR, 'index.json')
TASKS_JSON_PATH = os.path.join(BASE_DIR, 'tasks.json')


# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

def load_tasks():
def load_tasks():
    """Загружает все задачи (index.json + tasks.json)"""
    all_tasks = []
    seen_ids = set()
    # index.json — полные задачи (с тестами)
    if os.path.exists(INDEX_JSON_PATH):
        with open(INDEX_JSON_PATH, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                if isinstance(data, list):
                    for task in data:
                        task_id = str(task.get('id', ''))
                        if task_id not in seen_ids:
                            seen_ids.add(task_id)
                            all_tasks.append(task)
                elif isinstance(data, dict):
                    task_id = str(data.get('id', ''))
                    if task_id not in seen_ids:
                        seen_ids.add(task_id)
                        all_tasks.append(data)
            except json.JSONDecodeError:
                pass
    # tasks.json — задачи с решениями
    if os.path.exists(TASKS_JSON_PATH):
        with open(TASKS_JSON_PATH, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                if isinstance(data, list):
                    for task in data:
                        task_id = str(task.get('id', ''))
                        if task_id not in seen_ids:
                            seen_ids.add(task_id)
                            all_tasks.append(task)
            except json.JSONDecodeError:
                pass
    return all_tasks
    return all_tasks


def save_generated_task(task_data):
    """Сохраняет сгенерированную задачу в index.json"""
    existing = []
    if os.path.exists(INDEX_JSON_PATH):
        with open(INDEX_JSON_PATH, 'r', encoding='utf-8') as f:
            try:
                existing = json.load(f)
                if not isinstance(existing, list):
                    existing = [existing]
            except json.JSONDecodeError:
                existing = []
    
    # Генерируем уникальный id если нет
    if 'id' not in task_data or task_data['id'] is None:
        task_data['id'] = str(uuid.uuid4())[:8]
    
    task_data['created_at'] = datetime.now().isoformat()
    existing.append(task_data)
    
    with open(INDEX_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)


def run_code_against_tests(code, tests):
    """
def run_code_against_tests(code, tests):
    """ Запускает код пользователя на тестах задачи. Возвращает список результатов по каждому тесту. """
    # Безопасность: запрещаем опасные операции
    forbidden = ['__import__', 'eval', 'exec', 'open', 'file', 'input', 'raw_input']
    for word in forbidden:
        if word in code:
            return [{ 'test_index': 0, 'passed': False, 'input': '', 'expected': '', 'actual': '',
        if word in code:
            return [{
                'test_index': 0,
                'passed': False,
                'input': '',
                'expected': '',
                'actual': '',
                'error': f'Обнаружена запрещённая конструкция: {word}',
                'points': 0,
                'group': 'Основные'
            }]

    results = []
    for i, test in enumerate(tests):
        test_input = test.get('input', '')
        expected = str(test.get('expected_output', '')).strip()
        try:
            # Используем временный файл для изоляции
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_file = f.name

            proc = subprocess.run(
                [sys.executable, temp_file],
                input=test_input,
                capture_output=True,
                text=True,
                timeout=5,
                cwd=tempfile.mkdtemp()  # Изолированная директория
            )
            os.unlink(temp_file)  # Удаляем временный файл
def run_code_against_tests(code, tests):
    """ Запускает код пользователя на тестах задачи. Возвращает список результатов по каждому тесту. """
    # Безопасность: запрещаем опасные операции
    forbidden = ['__import__', 'eval', 'exec', 'open', 'file', 'input', 'raw_input']
    for word in forbidden:
        if word in code:
            return [{
                'test_index': 0,
                'passed': False,
                'input': '',
                'expected': '',
                'actual': '',
                'error': f'Обнаружена запрещённая конструкция: {word}',
                'points': 0,
                'group': 'Основные'
            }]

    results = []
    for i, test in enumerate(tests):
        test_input = test.get('input', '')
        expected = str(test.get('expected_output', '')).strip()
        try:
            # Используем временный файл для изоляции
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_file = f.name

            proc = subprocess.run(
                [sys.executable, temp_file],
                input=test_input,
                capture_output=True,
                text=True,
                timeout=5,
                cwd=tempfile.mkdtemp()
            )
            os.unlink(temp_file)

            actual = proc.stdout.strip()
            stderr = proc.stderr.strip()
            if proc.returncode != 0:
                results.append({
                    'test_index': i,
                    'passed': False,
                    'input': test_input,
                    'expected': expected,
                    'actual': actual,
                    'error': stderr or f'Процесс завершился с кодом {proc.returncode}',
                    'points': test.get('points', 0),
                    'group': test.get('group', 'Основные')
                })
            elif actual == expected:
                results.append({
                    'test_index': i,
                    'passed': True,
                    'input': test_input,
                    'expected': expected,
                    'actual': actual,
                    'error': None,
                    'points': test.get('points', 0),
                    'group': test.get('group', 'Основные')
                })
            else:
                results.append({
                    'test_index': i,
                    'passed': False,
                    'input': test_input,
                    'expected': expected,
                    'actual': actual,
                    'error': f'Ожидалось: {expected!r}, получено: {actual!r}',
                    'points': test.get('points', 0),
                    'group': test.get('group', 'Основные')
                })
        except subprocess.TimeoutExpired:
            results.append({
                'test_index': i,
                'passed': False,
                'input': test_input,
                'expected': expected,
                'actual': '',
                'error': 'Превышен лимит времени (5 секунд)',
                'points': test.get('points', 0),
                'group': test.get('group', 'Основные')
            })
        except Exception as e:
            results.append({
                'test_index': i,
                'passed': False,
                'input': test_input,
                'expected': expected,
                'actual': '',
                'error': str(e),
                'points': test.get('points', 0),
                'group': test.get('group', 'Основные')
            })
    return results

@app.route('/index.json')
def serve_index_json():
    return send_from_directory(BASE_DIR, 'index.json')


@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    """Возвращает список всех задач"""
    tasks = load_tasks()
    return jsonify({'tasks': tasks, 'count': len(tasks)})


@app.route('/api/generate', methods=['POST'])
def generate():
    """Генерация новой задачи через DeepSeek API"""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Пустой запрос'}), 400
    
    topic = data.get('topic', 'Алгоритмы')
    difficulty_num = data.get('difficulty', 50)
    
    # Определяем текстовую метку сложности для модели
    difficulty_text = 'easy' if difficulty_num <= 33 else ('medium' if difficulty_num <= 66 else 'hard')
    difficulty_label = 'простая' if difficulty_num <= 33 else ('средняя' if difficulty_num <= 66 else 'сложная')
    
    # Формируем описание темы для модели
    topic_description = f"{topic} (уровень сложности: {difficulty_num}%, {difficulty_label})"
    
    # Проверяем наличие AI_CONFIG
    config_str = os.environ.get('AI_CONFIG')
    if not config_str:
        # Режим без API — возвращаем тестовую задачу
        return jsonify({
            'error': 'AI_CONFIG не настроен. Использую тестовую заглушку.',
            'task': generate_mock_task(topic, difficulty_num),
            'mock': True
        }), 200
    
    try:
        config = json.loads(config_str)
        raw_response = task_create.generate_task(config, topic_description)
        
        if not raw_response:
            return jsonify({'error': 'Модель не вернула результат'}), 500
        
        task_data = task_create.extract_json(raw_response)
        if not task_data:
            return jsonify({
                'error': 'Не удалось распарсить JSON из ответа модели',
                'raw': raw_response[:500]
            }), 500
        
        # Добавляем тему и сложность
        task_data['main_topic'] = topic
        task_data['difficulty'] = difficulty_num
        
        # Сохраняем задачу
        save_generated_task(task_data)
        
        return jsonify({'task': task_data, 'mock': False})
        
    except ValueError as e:
        return jsonify({'error': f'Ошибка конфигурации: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': f'Ошибка генерации: {str(e)}'}), 500


@app.route('/api/tasks/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    """Удаление задачи по ID из index.json"""
    if not os.path.exists(INDEX_JSON_PATH):
        return jsonify({'error': 'Файл с задачами не найден'}), 404
    
    with open(INDEX_JSON_PATH, 'r', encoding='utf-8') as f:
        tasks = json.load(f)
    
    if not isinstance(tasks, list):
        tasks = [tasks]
    
    # Ищем задачу по ID (поддерживаем и числовые, и строковые id)
    found = False
    new_tasks = []
    for t in tasks:
        if str(t.get('id', '')) == str(task_id):
            found = True
        else:
            new_tasks.append(t)
    
    if not found:
        return jsonify({'error': f'Задача с id={task_id} не найдена'}), 404
    
    with open(INDEX_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(new_tasks, f, ensure_ascii=False, indent=2)
    
    return jsonify({'success': True, 'message': f'Задача {task_id} удалена'})


@app.route('/api/tasks/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    """Удаление задачи по ID"""
    try:
        # Загружаем существующие задачи



@app.route('/api/submit', methods=['POST'])
def submit():
    """Проверка решения пользователя на тестах"""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Пустой запрос'}), 400
    
    code = data.get('code', '')
    task_id = data.get('task_id', '')
    
    if not code.strip():
        return jsonify({'error': 'Код не может быть пустым'}), 400
    
    # Ищем задачу
    tasks = load_tasks()
    task = None
    for t in tasks:
        if str(t.get('id', '')) == str(task_id):
            task = t
            break
    
    if not task:
        return jsonify({'error': f'Задача с id={task_id} не найдена'}), 404
    
    # Проверяем наличие тестов
    tests = task.get('tests', [])
    if not tests:
        # Если нет тестов, проверяем на примерах
        examples = task.get('examples', [])
        if not examples:
            return jsonify({'error': 'В задаче нет тестов и примеров для проверки'}), 400
        
        tests = []
        for ex in examples:
            inp = ex.get('input', '')
            if isinstance(inp, list):
                inp = '\n'.join(str(x) for x in inp)
            tests.append({
                'input': str(inp),
                'expected_output': str(ex.get('output', '')),
                'points': 0,
                'group': 'Примеры'
            })
    
    # Запускаем проверку
    results = run_code_against_tests(code, tests)
    
    # Считаем итоги
    passed = sum(1 for r in results if r['passed'])
    total = len(results)
    total_points = sum(r['points'] for r in results if r['passed'])
    max_points = sum(r['points'] for r in results)
    
    return jsonify({
        'results': results,
        'summary': {
            'passed': passed,
            'total': total,
            'points': total_points,
            'max_points': max_points,
            'percentage': round(passed / total * 100, 1) if total > 0 else 0
        }
    })


# ============================================================
# ЗАГЛУШКА ДЛЯ ГЕНЕРАЦИИ БЕЗ API
# ============================================================

def generate_mock_task(topic, difficulty):
    """Генерирует тестовую задачу-заглушку когда API недоступен""""""
    task_templates = {
        'Алгоритмы сортировки': {
            'title': 'Сортировка по сумме цифр',
            'intro': 'Дан массив целых чисел.',
            'question': 'Отсортируйте числа по возрастанию суммы их цифр. Если суммы равны — по возрастанию самого числа.',
            'inputFormat': 'Первая строка: N. Вторая строка: N чисел через пробел.',
            'outputFormat': 'Выведите отсортированный массив через пробел.',
            'examples': [
                {'input': '5\n12 9 111 20 5', 'output': '12 20 111 5 9'},
                {'input': '3\n1 10 2', 'output': '1 10 2'},
            ],
            'tests': [
                {'input': '4\n51 32 10 100', 'expected_output': '10 100 32 51', 'points': 10, 'group': 'Основные'},
                {'input': '2\n1 2', 'expected_output': '1 2', 'points': 10, 'group': 'Основные'},
            ],
            'solution': 'def sum_digits(n):\n    return sum(int(d) for d in str(n))\n\nn = int(input())\narr = list(map(int, input().split()))\narr.sort(key=lambda x: (sum_digits(x), x))\nprint(" ".join(map(str, arr)))'
        },
        'Жадные алгоритмы': {
            'title': 'Размен монет',
            'intro': 'Требуется выдать сумму минимальным количеством монет.',
            'question': 'Найдите минимальное количество монет номиналом 1, 2, 5, 10 для выдачи суммы S.',
            'inputFormat': 'Одно целое число S.',
            'outputFormat': 'Минимальное количество монет.',
            'examples': [
                {'input': '63', 'output': '8'},
                {'input': '10', 'output': '1'},
            ],
            'tests': [
                {'input': '7', 'expected_output': '2', 'points': 10, 'group': 'Основные'},
                {'input': '99', 'expected_output': '12', 'points': 10, 'group': 'Основные'},
            ],
            'solution': 's = int(input())\ncoins = [10, 5, 2, 1]\ncount = 0\nfor c in coins:\n    count += s // c\n    s %= c\nprint(count)'
        },
    }
    
    template = task_templates.get(topic, {
        'title': f'Задача по теме «{topic}»',
        'intro': f'Олимпиадная задача уровня сложности {difficulty}%.',
        'question': f'Решите задачу по теме «{topic}».',
        'inputFormat': 'Описание формата ввода.',
        'outputFormat': 'Описание формата вывода.',
        'examples': [
            {'input': '1 2 3', 'output': '6'},
            {'input': '4 5 6', 'output': '15'},
        ],
        'tests': [
            {'input': '1 1 1', 'expected_output': '3', 'points': 10, 'group': 'Основные'},
        ],
        'solution': '# Решение на Python\nprint(sum(map(int, input().split())))'
    })
    
    return {
        'id': str(uuid.uuid4())[:8],
        'title': template['title'],
        'difficulty': difficulty,
        'main_topic': topic,
        'maxScore': 100,
        'description': {
            'intro': template['intro'],
            'question': template['question']
        },
        'inputFormat': template['inputFormat'],
        'outputFormat': template['outputFormat'],
        'examples': template['examples'],
        'tests': template['tests'],
        'solution': template['solution'],
        'constraints': {
            'timeLimit': '1 секунда',
            'memoryLimit': '256 MB',
            'language': 'Python 3'
        },
        'generated': True,
        'mock': True
    }


# ============================================================
# ЗАПУСК
# ============================================================

if __name__ == '__main__':
    print('=' * 60)
    print('  Тренажёр олимпиадной информатики')
    print('  Сервер запускается на http://localhost:5000')
    print('=' * 60)
    
    # Проверяем наличие AI_CONFIG
    if os.environ.get('AI_CONFIG'):
        print('  AI_CONFIG найден — генерация через DeepSeek API доступна')
    else:
        print('  AI_CONFIG не задан — будет использоваться заглушка')
        print('  Для реальной генерации задайте переменную окружения:')
        print('  set AI_CONFIG={"apiKey":"...","apiBase":"..."}')
    
    print('=' * 60)
    app.run(host='0.0.0.0', port=5000, debug=True)
