import os
import json
import subprocess
import sys
import re
import time
import openai
import ast

# ============================================================
# КОНСТАНТЫ
# ============================================================

MODEL = "deepseek-v4-pro"  # Модель фиксирована, не зависит от конфигурации

# ============================================================
# КОНФИГУРАЦИЯ API
# ============================================================

def get_ai_config():
    """Получение конфигурации AI из переменной окружения AI_CONFIG"""
    config_str = os.environ.get("AI_CONFIG")
    if not config_str:
        raise ValueError("Переменная окружения AI_CONFIG не установлена")
    
    try:
        config = json.loads(config_str)
        required = ["apiKey", "apiBase"]  # model не требуется, используется константа
        for key in required:
            if key not in config:
                raise ValueError(f"Отсутствует ключ '{key}' в AI_CONFIG")
        return config
    except json.JSONDecodeError as e:
        raise ValueError(f"Ошибка парсинга AI_CONFIG: {e}")

# ============================================================
# ГЕНЕРАЦИЯ И КОРРЕКЦИЯ ЗАДАЧ (DeepSeek)
# ============================================================

def generate_task_with_deepseek(topic_description, config):
    """Генерация задачи через DeepSeek API"""
    prompt = f"""Создай задачу по олимпиадному программированию на тему: {topic_description}

Верни ТОЛЬКО чистый JSON без markdown-разметки. Не используй ```json```.

СТРУКТУРА:
{{
  "id": <уникальный номер от 1000 до 9999>,
  "title": "Название задачи",
  "difficulty": "easy",
  "maxScore": 100,
  "description": {{
    "intro": "Введение в задачу",
    "rules": ["Правило 1", "Правило 2", "Правило 3"],
    "question": "Конкретный вопрос задачи"
  }},
  "inputFormat": "Описание формата ввода (одна строка)",
  "outputFormat": "Описание формата вывода (одна строка)",
  "examples": [
    {{ "input": "1 2 3", "output": "" }},
    {{ "input": "4 5 6", "output": "" }},
    {{ "input": "7 8 9", "output": "" }},
    {{ "input": "10 11 12", "output": "" }}
  ],
  "constraints": {{
    "timeLimit": "1 секунда",
    "memoryLimit": "256 MB",
    "language": "Python 3"
  }},
  "scoring": [
    {{ "condition": "Примеры", "points": 0 }},
    {{ "condition": "Основные тесты", "points": 60 }},
    {{ "condition": "Граничные случаи", "points": 40 }}
  ],
  "tests": [
    {{ "input": "тест1", "points": 10, "group": "Основные", "expected_output": "" }},
    {{ "input": "тест2", "points": 10, "group": "Основные", "expected_output": "" }},
    {{ "input": "тест3", "points": 10, "group": "Основные", "expected_output": "" }},
    {{ "input": "тест4", "points": 10, "group": "Основные", "expected_output": "" }},
    {{ "input": "тест5", "points": 10, "group": "Основные", "expected_output": "" }},
    {{ "input": "тест6", "points": 10, "group": "Основные", "expected_output": "" }},
    {{ "input": "тест7", "points": 10, "group": "Граничные", "expected_output": "" }},
    {{ "input": "тест8", "points": 10, "group": "Граничные", "expected_output": "" }},
    {{ "input": "тест9", "points": 10, "group": "Граничные", "expected_output": "" }},
    {{ "input": "тест10", "points": 10, "group": "Граничные", "expected_output": "" }}
  ],
  "solution": "КОД НА PYTHON 3",
  "hint": {{
    "short": "Краткая подсказка",
    "full": {{
      "keyIdea": "Ключевая идея",
      "steps": ["Шаг 1", "Шаг 2"],
      "warning": "Предупреждение"
    }}
  }},
  "solutionExplanation": {{
    "idea": "Идея решения",
    "why": "Почему работает",
    "complexity": "O(n)",
    "examples": []
  }}
}}

ТРЕБОВАНИЯ:
1. Создай ПРОСТУЮ задачу (для начинающих)
2. Решение должно быть КОРОТКИМ (до 30 строк)
3. РОВНО 4 примера в массиве examples
4. РОВНО 10 тестов в массиве tests (6 основных + 4 граничных)
5. Все expected_output и output - ПУСТЫЕ строки ""
6. Тесты должны быть РАЗНООБРАЗНЫМИ (разные значения, граничные случаи)
7. Код решения читает через input().split() и выводит через print()
8. НЕ ИСПОЛЬЗУЙ специальные символы внутри JSON кроме экранированных \\n и \\"

Верни ТОЛЬКО JSON без дополнительного текста."""

    client = openai.Client(
        api_key=config["apiKey"],
        base_url=config["apiBase"]
    )
    
    response = client.chat.completions.create(
        model=MODEL,  # Используем константу
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8,
        max_tokens=8192
    )
    
    return response.choices[0].message.content

def correct_task_with_deepseek(task, errors_info, topic_description, config):
    """Исправление задачи через DeepSeek"""
    prompt = f"""ИСПРАВЬ ТОЛЬКО КОД РЕШЕНИЯ в задаче на тему "{topic_description}".

ОШИБКИ:
{json.dumps(errors_info, ensure_ascii=False, indent=2)[:2000]}

ТЕКУЩАЯ ЗАДАЧА (фрагмент):
{json.dumps(task, ensure_ascii=False, indent=2)[:4000]}

Верни ПОЛНЫЙ JSON задачи с исправленным решением.
НЕ меняй тесты и примеры.
Верни ТОЛЬКО JSON."""

    client = openai.Client(
        api_key=config["apiKey"],
        base_url=config["apiBase"]
    )
    
    response = client.chat.completions.create(
        model=MODEL,  # Используем константу
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=8192
    )
    
    return response.choices[0].message.content

def generate_task(config, topic_description):
    """
    Генерация задачи через DeepSeek
    """
    print(" Генерация через DeepSeek API...")
    try:
        result = generate_task_with_deepseek(topic_description, config)
        if result:
            return result
    except Exception as e:
        print(f"⚠️ Ошибка DeepSeek: {e}")
    return None

def correct_task(config, task, errors_info, topic_description):
    """Коррекция задачи через DeepSeek"""
    print(" Запрос коррекции через DeepSeek...")
    try:
        result = correct_task_with_deepseek(task, errors_info, topic_description, config)
        if result:
            return result
    except Exception as e:
        print(f"⚠️ Ошибка коррекции DeepSeek: {e}")
    return None

# ============================================================
# ОБРАБОТКА JSON
# ============================================================

def _safe_eval_join(expr):
    """Безопасное вычисление выражений вида " ".join(["1"] * N)"""
    try:
        tree = ast.parse(expr, mode='eval')
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if not (isinstance(node.func, ast.Attribute) and node.func.attr == 'join'):
                    raise ValueError(f"Forbidden call: {ast.dump(node)}")
            elif isinstance(node, (ast.BinOp, ast.Str, ast.List, ast.Tuple, ast.Num, ast.Load, ast.Constant)):
                continue
            else:
                raise ValueError(f"Forbidden node: {type(node).__name__}")
        return eval(compile(tree, '<safe_join>', 'eval'))
    except Exception as e:
        print(f"⚠️ safe_eval_join failed for '{expr[:80]}...': {e}")
        return None

def extract_json(text):
    """Извлечение JSON с поддержкой вычисления .join() выражений"""
    if not text:
        return None
    
    # Сохраняем для отладки
    with open('debug_last_response.txt', 'w', encoding='utf-8') as f:
        f.write(text)
    
    # Очищаем от markdown
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    text = text.strip()
    
    # Находим JSON
    start = text.find('{')
    end = text.rfind('}') + 1
    if start == -1 or end == 0:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            json_str = match.group()
        else:
            print("❌ Не удалось найти JSON")
            return None
    else:
        json_str = text[start:end]
    
    # Безопасно заменяем выражения .join()
    # Ищем шаблоны вида "...".join([...])
    def replace_join_expr(match):
        expr = match.group(0)
        value = _safe_eval_join(expr)
        if value is not None:
            # Экранируем кавычки и обратные слеши
            escaped_value = value.replace('\\', '\\\\').replace('"', '\\"')
            return f'"{escaped_value}"'
        return match.group(0)  # Возвращаем как есть при ошибке
    
    # Применяем ко всем вхождениям .join()
    while True:
        new_json_str = re.sub(r'"[^"]+"\.join\([^)]+\)', replace_join_expr, json_str)
        if new_json_str == json_str:
            break
        json_str = new_json_str
    
    # Теперь пытаемся распарсить
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"⚠️ Ошибка JSON после обработки .join(): {e}")
    
    # Стратегия 2: минимальная очистка
    try:
        json_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', json_str)
        json_str = json_str.replace('\\', '\\\\').replace('\\\\"', '\\"')
        return json.loads(json_str)
    except:
        pass
    
    print("❌ Не удалось распарсить JSON после всех попыток")
    return None

def validate_task_structure(task):
    """Проверка структуры задачи с учётом требований по количеству"""
    required_fields = {
        'id': (int, float),
        'title': str,
        'difficulty': str,
        'maxScore': (int, float),
        'description': dict,
        'inputFormat': str,
        'outputFormat': str,
        'examples': list,
        'constraints': dict,
        'scoring': list,
        'tests': list,
        'solution': str,
        'hint': dict,
        'solutionExplanation': dict
    }
    
    errors = []
    
    for field, expected_type in required_fields.items():
        if field not in task:
            errors.append(f"Отсутствует поле: {field}")
        elif not isinstance(task[field], expected_type):
            errors.append(f"Неверный тип поля {field}")
    
    # Проверка количества примеров и тестов
    if 'examples' in task and isinstance(task['examples'], list):
        count = len(task['examples'])
        if count < 4:
            errors.append(f"Мало примеров: {count} (нужно минимум 4)")
    else:
        errors.append("Отсутствуют примеры")
    
    if 'tests' in task and isinstance(task['tests'], list):
        count = len(task['tests'])
        if count < 10:
            errors.append(f"Мало тестов: {count} (нужно минимум 10)")
        
        # Проверяем, что у всех тестов есть input
        for i, test in enumerate(task['tests']):
            if not isinstance(test, dict):
                errors.append(f"Тест {i+1} не является объектом")
            elif 'input' not in test:
                errors.append(f"Тест {i+1}: отсутствует input")
    else:
        errors.append("Отсутствуют тесты")
    
    return len(errors) == 0, errors

# ============================================================
# ЗАПУСК И ТЕСТИРОВАНИЕ
# ============================================================

def normalize_solution_input(code):
    """
    Приводит код решения к форме, совместимой с subprocess.run(input=...).
    - Добавляет import sys, если его нет.
    - Заменяет input() на sys.stdin.readline().rstrip('\\n'),
      чтобы избежать EOFError и проблем с буферизацией.
    """
    # Сохраняем import sys, если есть
    has_import_sys = bool(re.search(r'^import sys\s*$|^from sys\s+import', code, re.MULTILINE))
    
    # Добавляем import sys в начало, если отсутствует
    if not has_import_sys:
        code = 'import sys\n' + code
    
    # Заменяем input() на sys.stdin.readline().rstrip('\\n')
    # (только если это не внутри строки; для простоты пропускаем проверку)
    code = re.sub(r'\binput\(\)', r"sys.stdin.readline().rstrip('\\n')", code)
    
    return code

def run_solution_and_generate_outputs(solution_code, test_inputs, timeout=3):
    """Запускает решение на списке входных данных"""
    results = []
    
    # Нормализуем код, чтобы он работал с subprocess.run
    solution_code = normalize_solution_input(solution_code)
    
    temp_file = 'temp_solution.py'
    with open(temp_file, 'w', encoding='utf-8') as f:
        f.write(solution_code)
    
    for input_data in test_inputs:
        start_time = time.time()
        try:
            process = subprocess.run(
                [sys.executable, temp_file],
                input=input_data,
                text=True,
                capture_output=True,
                timeout=timeout
            )
            elapsed = time.time() - start_time
            
            if process.returncode != 0:
                error_msg = process.stderr.strip()[:200]
                results.append((False, f"Runtime Error: {error_msg}", elapsed))
            else:
                output = process.stdout.strip()
                results.append((True, output, elapsed))
                
        except subprocess.TimeoutExpired:
            elapsed = time.time() - start_time
            results.append((False, f"Timeout (> {timeout}s)", elapsed))
        except Exception as e:
            elapsed = time.time() - start_time
            results.append((False, f"Exception: {str(e)[:100]}", elapsed))
    
    if os.path.exists(temp_file):
        os.remove(temp_file)
        
    return results

def populate_outputs(task):
    """Запускает решение на всех примерах и тестах для получения expected_output"""
    solution_code = task.get('solution')
    if not solution_code:
        return task, False, "Отсутствует решение"
    
    # Собираем все входные данные
    all_inputs = []
    input_sources = []
    
    for i, ex in enumerate(task.get('examples', [])):
        inp = ex.get('input', '')
        if inp:
            all_inputs.append(inp)
            input_sources.append(('example', i))
    
    for i, test in enumerate(task.get('tests', [])):
        inp = test.get('input', '')
        if inp:
            all_inputs.append(inp)
            input_sources.append(('test', i))
    
    if not all_inputs:
        return task, False, "Нет входных данных"
    
    print(f"    Запуск решения на {len(all_inputs)} тестах...")
    outputs = run_solution_and_generate_outputs(solution_code, all_inputs)
    
    # Проверяем успешность
    for i, (success, output, elapsed) in enumerate(outputs):
        source_type, source_idx = input_sources[i]
        if not success:
            location = f"{source_type} #{source_idx + 1}"
            return task, False, f"Ошибка на {location}: {output}"
        if elapsed > 2.0:
            print(f"   ⚠️ {source_type} #{source_idx + 1}: {elapsed:.1f}с")
    
    # Распределяем выводы обратно
    for i, (success, output, _) in enumerate(outputs):
        source_type, source_idx = input_sources[i]
        if source_type == 'example':
            task['examples'][source_idx]['output'] = output
        else:
            task['tests'][source_idx]['expected_output'] = output
    
    print(f"   ✅ Все тесты выполнены успешно")
    return task, True, "OK"

def test_solution(task):
    """Финальная проверка решения на тестах"""
    solution_code = task['solution']
    
    all_tests = []
    
    for i, ex in enumerate(task.get('examples', [])):
        if ex.get('input'):
            all_tests.append({
                'input': ex['input'],
                'expected_output': ex.get('output', ''),
                'test_num': f"Example_{i+1}",
                'group': 'Примеры',
                'points': 0
            })
    
    for i, test in enumerate(task.get('tests', [])):
        if test.get('input'):
            all_tests.append({
                'input': test['input'],
                'expected_output': test.get('expected_output', ''),
                'test_num': f"Test_{i+1}",
                'group': test.get('group', 'Основные'),
                'points': test.get('points', 0)
            })
    
    if not all_tests:
        return False, [], 0, 0
    
    test_inputs = [t['input'] for t in all_tests]
    outputs = run_solution_and_generate_outputs(solution_code, test_inputs, timeout=3)
    
    results = []
    all_passed = True
    total_points = 0
    max_points = 0
    
    for i, (success, actual_output, _) in enumerate(outputs):
        test = all_tests[i]
        
        if not success:
            all_passed = False
            results.append({
                'test_num': test['test_num'],
                'input': test['input'][:80],
                'passed': False,
                'group': test['group'],
                'points': test['points'],
                'error_type': 'runtime_error',
                'error': actual_output
            })
            continue
        
        expected_output = str(test['expected_output']).strip()
        actual_clean = ' '.join(actual_output.split())
        expected_clean = ' '.join(expected_output.split())
        
        passed = actual_clean == expected_clean
        
        if passed:
            total_points += test['points']
        else:
            all_passed = False
            
        max_points += test['points']
        
        results.append({
            'test_num': test['test_num'],
            'input': test['input'][:80] + ('...' if len(test['input']) > 80 else ''),
            'expected': expected_output,
            'actual': actual_output,
            'passed': passed,
            'group': test['group'],
            'points': test['points'],
            'error_type': None if passed else 'wrong_answer'
        })
    
    return all_passed, results, total_points, max_points

# ============================================================
# ВЫВОД РЕЗУЛЬТАТОВ
# ============================================================

def print_test_results(results, total_points, max_points):
    """Вывод результатов тестирования"""
    print("\n" + "="*70)
    print(" РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
    print("="*70)
    
    groups = {}
    for result in results:
        group = result.get('group', 'Без группы')
        if group not in groups:
            groups[group] = []
        groups[group].append(result)
    
    for group_name, group_results in groups.items():
        print(f"\n {group_name}")
        print("-"*50)
        
        for result in group_results:
            status = "✅" if result['passed'] else "❌"
            print(f"{status} {result['test_num']}: {result['input']}")
            if not result['passed']:
                if 'expected' in result:
                    print(f"   Ожидалось: {result['expected']}")
                    print(f"   Получено: {result.get('actual', '')}")
                if 'error' in result:
                    print(f"   Ошибка: {result['error']}")
    
    passed = sum(1 for r in results if r['passed'])
    total = len(results)
    
    print("\n" + "="*70)
    print(f"✅ Пройдено: {passed}/{total}")
    print(f"⭐ Баллы: {total_points}/{max_points}")
    if total > 0:
        print(f" Процент: {passed/total*100:.1f}%")
    print("="*70)

def save_task(task, filename=None):
    """Сохранение задачи"""
    if filename is None:
        task_id = task.get('id', 'unknown')
        task_title = task.get('title', 'untitled')
        safe_title = re.sub(r'[<>:"/\\|?*]', '_', task_title)
        filename = f"task_{task_id}_{safe_title}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(task, f, ensure_ascii=False, indent=2)
    
    return filename

# ============================================================
# ГЛАВНАЯ ФУНКЦИЯ
# ============================================================

def main():
    print(" Генератор олимпиадных задач (DeepSeek)")
    print("="*70)
    print(f"• Модель: {MODEL}")
    print("• Конфигурация из переменной окружения AI_CONFIG")
    print("• Минимум 4 примера и 10 тестов")
    print("="*70)
    
    # Ввод темы
    topic_description = input("\n Введите тему задачи: ").strip()
    if not topic_description:
        print("❌ Тема не может быть пустой")
        return
    
    # Загрузка конфигурации
    print("\n Загрузка конфигурации AI...")
    try:
        config = get_ai_config()
        print(f"✅ API Base: {config['apiBase']}")
        print(f"✅ Модель: {MODEL}")
    except Exception as e:
        print(f"❌ Ошибка загрузки конфигурации: {e}")
        return
    
    # Основной цикл генерации
    task_number = 0
    total_attempts = 0
    max_attempts = 15
    
    while total_attempts < max_attempts:
        task_number += 1
        correction_attempts = 0
        max_corrections = 3
        
        print(f"\n{'='*70}")
        print(f" Генерация задачи #{task_number}")
        print(f"{'='*70}")
        
        total_attempts += 1
        
        # Генерация задачи
        response_text = generate_task(config, topic_description)
        
        if not response_text:
            print("❌ Не удалось сгенерировать задачу")
            continue
        
        current_task = extract_json(response_text)
        if not current_task:
            print("❌ Ошибка парсинга JSON")
            continue
        
        print(f"✅ Задача: '{current_task.get('title', 'Без названия')}'")
        
        # Проверка структуры
        is_valid, errors = validate_task_structure(current_task)
        if not is_valid:
            print("❌ Структурные ошибки:")
            for error in errors[:8]:
                print(f"   - {error}")
            continue
        
        print(f"✅ Структура: OK (примеров: {len(current_task.get('examples', []))}, тестов: {len(current_task.get('tests', []))})")
        
        # Генерация expected_output
        print("\n Вычисление expected_output...")
        current_task, success, message = populate_outputs(current_task)
        
        if not success:
            print(f"❌ Ошибка выполнения: {message}")
            
            # Цикл коррекции
            while correction_attempts < max_corrections:
                correction_attempts += 1
                total_attempts += 1
                
                print(f"\n Попытка коррекции #{correction_attempts}")
                
                errors_info = [{'error': message, 'type': 'runtime'}]
                response_text = correct_task(
                    config, current_task, errors_info, topic_description
                )
                
                if not response_text:
                    print("❌ Не получен ответ при коррекции")
                    continue
                
                corrected_task = extract_json(response_text)
                if not corrected_task:
                    continue
                
                current_task = corrected_task
                current_task, success, message = populate_outputs(current_task)
                
                if success:
                    print("✅ Решение исправлено!")
                    break
                else:
                    print(f"❌ Всё ещё ошибка: {message}")
            
            if not success:
                print(" Генерирую новую задачу...")
                continue
        
        # Финальная проверка
        print("\n Финальное тестирование...")
        all_passed, test_results, total_points, max_points = test_solution(current_task)
        print_test_results(test_results, total_points, max_points)
        
        if all_passed:
            print(f"\n УСПЕХ! Все тесты пройдены!")
            print(f"   Сгенерировано задач: {task_number}")
            print(f"   Всего попыток: {total_attempts}")
            
            filename = save_task(current_task)
            print(f" Сохранено: '{filename}'")
            
            # Статистика
            print(f"\n Статистика задачи:")
            print(f"   ID: {current_task.get('id')}")
            print(f"   Название: {current_task.get('title')}")
            print(f"   Сложность: {current_task.get('difficulty')}")
            print(f"   Примеров: {len(current_task.get('examples', []))}")
            print(f"   Тестов: {len(current_task.get('tests', []))}")
            print(f"   Баллов: {max_points}")
            
            break
        else:
            print("\n Есть ошибки, генерирую новую задачу...")
    
    if total_attempts >= max_attempts:
        print(f"\n❌ Достигнут лимит попыток ({max_attempts}). Попробуйте позже.")

if __name__ == "__main__":
    main()


# ============================================================
# ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ ТРЕНАЖЁРА
# ============================================================

def load_tasks():
    """Загрузка задач из tasks.json"""
    with open('tasks.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def save_tasks(tasks):
    """Сохранение задач в tasks.json"""
    with open('tasks.json', 'w', encoding='utf-8') as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)

def find_task(topic, difficulty):
    """Поиск задачи по теме и сложности"""
    tasks = load_tasks()
    candidates = [t for t in tasks if t.get('main_topic', '').lower() == topic.lower()]
    if not candidates:
        candidates = [t for t in tasks if topic.lower() in t.get('main_topic', '').lower()]
    if not candidates:
        return None
    best = min(candidates, key=lambda t: abs(t.get('difficulty', 50) - difficulty))
    return best

def get_or_generate_task(topic, difficulty, config):
    """Получить задачу из базы или сгенерировать новую"""
    task = find_task(topic, difficulty)
    if task:
        return task
    raw = generate_task(config, topic)
    if not raw:
        return None
    task = extract_json(raw)
    task['difficulty'] = difficulty
    task['main_topic'] = topic
    tasks = load_tasks()
    tasks.append(task)
    save_tasks(tasks)
    return task

def run_code_with_input(code, input_str, timeout=5):
    """Запуск пользовательского кода с заданным вводом"""
    import subprocess, tempfile, os
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        f.write(code)
        tmp_path = f.name
    try:
        proc = subprocess.run(
            ['python', tmp_path],
            input=input_str,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=os.environ.copy()
        )
        return proc.stdout, proc.stderr, proc.returncode
    except subprocess.TimeoutExpired:
        return '', 'Timeout', -1
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

def check_solution(task, user_code):
    """Проверка решения на примерах и тестах"""
    results = []
    all_passed = True
    for ex in task.get('examples', []):
        inp = ex.get('input', '')
        expected = ex.get('output', '')
        out, err, rc = run_code_with_input(user_code, inp)
        if rc != 0:
            results.append({'input': inp, 'expected': expected, 'got': out, 'error': err, 'passed': False})
            all_passed = False
        else:
            out_clean = out.strip()
            expected_clean = expected.strip()
            passed = (out_clean == expected_clean)
            results.append({'input': inp, 'expected': expected, 'got': out_clean, 'passed': passed})
            if not passed:
                all_passed = False
    for test in task.get('tests', []):
        inp = test.get('input', '')
        expected = test.get('expected_output', '')
        out, err, rc = run_code_with_input(user_code, inp)
        if rc != 0:
            results.append({'input': inp, 'expected': expected, 'got': out, 'error': err, 'passed': False})
            all_passed = False
        else:
            out_clean = out.strip()
            expected_clean = expected.strip()
            passed = (out_clean == expected_clean)
            results.append({'input': inp, 'expected': expected, 'got': out_clean, 'passed': passed})
            if not passed:
                all_passed = False
    return all_passed, results
