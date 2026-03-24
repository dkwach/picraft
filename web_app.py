import json
import time
import math
import random
import threading

from flask import Flask, Response, render_template

try:
    from mpu import MPU9150
except ImportError:

    class FakeMPU9150:
        def get_accel(self):
            return [random.uniform(-30, 30) for _ in range(3)]

    MPU9150 = FakeMPU9150

start_time = time.time()
app = Flask(__name__)

ACC_SAMPLE_INTERVAL = 0.1
HIT_THRESHOLD = 20
acc_state = {
    "value": {axis: 0.0 for axis in "xyz"},
    "version": 0,
}
acc_condition = threading.Condition()


def sensor_loop():
    acc_api = MPU9150()
    print(id(acc_api))
    while True:
        try:
            acceleration = acc_api.get_accel()
        except Exception as exc:  # keep the loop alive on flaky wiring
            print(f"MPU read failed: {exc}")
            time.sleep(ACC_SAMPLE_INTERVAL)
            continue

        with acc_condition:
            acc_state["value"] = {
                axis: value for axis, value in zip("xyz", acceleration)
            }
            acc_state["version"] += 1
            acc_condition.notify_all()
        time.sleep(ACC_SAMPLE_INTERVAL)


sensor_thread = threading.Thread(target=sensor_loop, daemon=True)
sensor_thread.start()


def make_data(data):
    json_data = json.dumps(data)
    return f"data:{json_data}\n\n"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/acceleration")
def chart_data():
    def obtain_data():
        last_version = acc_state["version"]
        while True:
            with acc_condition:
                acc_condition.wait_for(lambda: acc_state["version"] != last_version)
                payload = dict(acc_state["value"])
                last_version = acc_state["version"]
            yield make_data({"acc": payload, "time": f"{time.time() - start_time:.2f}"})

    return Response(obtain_data(), mimetype="text/event-stream")


@app.route("/hit")
def hit_data():
    def obtain_data():
        last_version = acc_state["version"]
        last_hit = None
        yield make_data({"hit": False})
        while True:
            with acc_condition:
                acc_condition.wait_for(lambda: acc_state["version"] != last_version)
                payload = dict(acc_state["value"])
                last_version = acc_state["version"]
            current_hit = math.sqrt(sum(a**2 for a in payload.values())) > HIT_THRESHOLD
            if current_hit != last_hit:
                last_hit = current_hit
                yield make_data({"hit": current_hit})

    return Response(obtain_data(), mimetype="text/event-stream")


if __name__ == "__main__":
    app.run(debug=True, threaded=True, host="0.0.0.0")
