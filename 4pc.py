import time
import threading
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# --- Глобальные переменные для логики ---
pc_data = {}            # Словарь: { "pc1": (lobby_id, timestamp), "pc2": (lobby_id, timestamp), ... }
current_game_state = "waiting"  # Может быть: "waiting", "accept", "reject"
start_time = None
game_history = []       # Список словарей с историей
REQUIRED_PCS = 4        # Сколько ПК должно отправить ID

# --- Встроенный HTML-шаблон ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Lobby Server</title>
    <!-- Bootstrap 5 -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    <style>
        body {
            background-color: #f8f9fa; /* Светлый фон для контраста */
            color: #212529;
            margin-bottom: 3rem;
        }
        .navbar-dark.bg-dark {
            margin-bottom: 2rem;
        }
        .status {
            font-size: 1.2rem;
            font-weight: 600;
        }
        .accept { color: green; }
        .reject { color: red; }
        .waiting { color: orange; }
        .card {
            margin-bottom: 1rem;
        }
        .table thead th {
            background-color: #343a40;
            color: #fff;
        }
    </style>
</head>
<body>

<nav class="navbar navbar-expand-lg navbar-dark bg-dark">
  <div class="container-fluid">
    <a class="navbar-brand" href="#">Lobby Server</a>
  </div>
</nav>

<div class="container">

    <!-- Карточка со статусом -->
    <div class="card">
        <div class="card-header">
            Текущий статус
        </div>
        <div class="card-body">
            <p class="status {{ state }}">
                {{ state }}
            </p>
        </div>
    </div>

    <!-- Карточка с данными от ПК -->
    <div class="card">
        <div class="card-header">
            Данные от ПК
        </div>
        <div class="card-body">
            <table class="table table-bordered table-sm align-middle">
                <thead>
                    <tr>
                        <th>PC name</th>
                        <th>Lobby ID</th>
                        <th>Time</th>
                    </tr>
                </thead>
                <tbody>
                {% for pc, (lobby, ts) in pc_data.items() %}
                    <tr>
                        <td>{{ pc }}</td>
                        <td>{{ lobby }}</td>
                        <td>{{ ts }}</td>
                    </tr>
                {% endfor %}
                </tbody>
            </table>
        </div>
    </div>

    <!-- Карточка с историей игр -->
    <div class="card">
        <div class="card-header">
            История игр
        </div>
        <div class="card-body">
            <table class="table table-striped table-sm align-middle">
                <thead>
                    <tr>
                        <th>Время</th>
                        <th>Lobby ID</th>
                        <th>Статус</th>
                    </tr>
                </thead>
                <tbody>
                {% for item in game_history %}
                    <tr>
                        <td>{{ item.timestamp }}</td>
                        <td>{{ item.lobby_id }}</td>
                        <td>{{ item.status }}</td>
                    </tr>
                {% endfor %}
                </tbody>
            </table>
        </div>
    </div>

</div> <!-- /container -->

</body>
</html>
"""

# --- Логика сброса состояния ---
def reset_state():
    """Сброс всех глобальных переменных в начальное состояние."""
    global pc_data, current_game_state, start_time
    pc_data.clear()
    current_game_state = "waiting"
    start_time = None

# --- Поток, который через 6 секунд решает, Accept или Reject ---
def check_all_after_6_seconds():
    global current_game_state
    time.sleep(6)

    # Проверяем, успели ли все 4 ПК отправить ID
    if len(pc_data) < REQUIRED_PCS:
        current_game_state = "reject"
        reset_state()
        return

    # Проверяем, совпадают ли все lobby_id
    all_lobby_ids = {data[0] for data in pc_data.values()}
    if len(all_lobby_ids) == 1:
        # Все 4 совпали
        current_game_state = "accept"
        lobby_id = all_lobby_ids.pop()
        # Добавляем запись в историю
        game_history.append({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "lobby_id": lobby_id,
            "status": "Game started"
        })
        # Ждём 5 сек, чтобы статус "accept" был виден
        time.sleep(5)
        reset_state()
    else:
        # IDs оказались разными
        current_game_state = "reject"
        reset_state()

# --- Маршрут на главную (рендерим HTML_TEMPLATE) ---
@app.route("/")
def index():
    return render_template_string(
        HTML_TEMPLATE,
        state=current_game_state,
        pc_data=pc_data,
        game_history=game_history
    )

# --- Приём лобби-ID от ПК (POST) ---
@app.route("/send_lobby_id", methods=["POST"])
def send_lobby_id():
    global current_game_state, start_time

    data = request.json
    if not data or "lobby_id" not in data or "pc" not in data:
        return jsonify({"error": "Invalid data"}), 400

    lobby_id = data["lobby_id"]
    pc_name = data["pc"]

    # Запоминаем
    pc_data[pc_name] = (lobby_id, time.time())

    # Если это первый ID в раунде, запоминаем время и запускаем поток проверки
    if start_time is None:
        start_time = time.time()
        t = threading.Thread(target=check_all_after_6_seconds)
        t.start()

    # Возвращаем простой ответ
    return jsonify({"status": "received"})

# --- Проверка статуса (GET) ---
@app.route("/check_status", methods=["GET"])
def check_status():
    return jsonify({"status": current_game_state})

# --- Точка входа ---
if __name__ == "__main__":
    # Запускаем сервер. debug=True — чтобы удобно было отлаживать.
    app.run(host="0.0.0.0", port=5000, debug=True)
