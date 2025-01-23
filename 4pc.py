import time
import threading
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# --- Глобальные переменные ---
pc_data = {}                   # { "pc1": (lobby_id, timestamp), ... }
current_game_state = "waiting" # "waiting", "accept", "reject"
start_time = None
game_history = []              # [{'timestamp': ..., 'lobby_id': ..., 'status': ...}]
REQUIRED_PCS = 4               # Ожидаем 4 ПК

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
            background-color: #f8f9fa;
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

# --- Сброс состояния ---
def reset_state():
    global pc_data, current_game_state, start_time
    pc_data.clear()
    current_game_state = "waiting"
    start_time = None

# --- Поток: через 5 секунд сказать Accept/Reject, ещё через 5 секунд сбросить ---
def check_all_in_5s_and_reset_in_10():
    global current_game_state

    # Ждём 5 секунд, даём время всем ПК прислать лобби
    time.sleep(5)

    # Если меньше REQUIRED_PCS => reject
    if len(pc_data) < REQUIRED_PCS:
        current_game_state = "reject"
    else:
        # Проверяем, совпадают ли все lobby_id
        all_lobby_ids = {data[0] for data in pc_data.values()}
        if len(all_lobby_ids) == 1:
            current_game_state = "accept"
            # Запись в историю (сверху)
            lobby_id = all_lobby_ids.pop()
            game_history.insert(0, {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "lobby_id": lobby_id,
                "status": "Game started"
            })
        else:
            current_game_state = "reject"

    # Дожидаемся полного времени 10 сек с момента первого ID
    if start_time is not None:
        total_elapsed = time.time() - start_time
        remain = 10 - total_elapsed
        if remain > 0:
            time.sleep(remain)

    # После 10 секунд от первого ID - сбрасываем состояние
    reset_state()


# --- Маршрут на главную (рендерим шаблон) ---
@app.route("/")
def index():
    return render_template_string(
        HTML_TEMPLATE,
        state=current_game_state,
        pc_data=pc_data,
        game_history=game_history
    )

# --- Приём лобби-ID (POST) ---
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

    # Если это первый лобби-ID в данном "раунде"
    if start_time is None:
        start_time = time.time()
        # Запускаем поток проверки: 5с -> Accept/Reject, на 10-й секунде сброс
        t = threading.Thread(target=check_all_in_5s_and_reset_in_10)
        t.start()

    return jsonify({"status": "received"})

# --- Проверка статуса (GET) ---
@app.route("/check_status", methods=["GET"])
def check_status():
    return jsonify({"status": current_game_state})

# --- Запуск ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
