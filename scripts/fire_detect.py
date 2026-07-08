#!/usr/bin/env python3
import cv2, numpy as np, paho.mqtt.client as mqtt, json, time, os
from rknnlite.api import RKNNLite

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
ALERT_TOPIC = "robot/alert"
MODEL_PATH = "/home/rock/Desktop/yolo26_rk3588_-fire/best_rk3588.rknn"
CONF_THRESHOLD = 0.85
CLASS_NAMES = ['fire', 'smoke']
SNAPSHOT_DIR = "/tmp/fire_snapshots"
MAX_SNAPSHOTS = 10
ALERT_INTERVAL = 5


def main():
    if not os.path.exists(MODEL_PATH):
        print(f"模型文件不存在: {MODEL_PATH}")
        return
    rknn = RKNNLite()
    if rknn.load_rknn(MODEL_PATH) != 0 or rknn.init_runtime(core_mask=RKNNLite.NPU_CORE_AUTO) != 0:
        print("RKNN 初始化失败")
        return
    print("RKNN 模型加载成功")

    mqtt_client = mqtt.Client()
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    mqtt_client.loop_start()

    cap = cv2.VideoCapture("http://127.0.0.1:8080/?action=stream")
    if not cap.isOpened():
        print("无法打开视频流")
        return
    print("视频流已连接，开始检测...")

    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    last_time = time.time()
    last_alert_time = 0
    best_conf = 0.0
    best_snapshot = None

    try:
        while True:
            ret, frame = cap.read()
            if not ret: continue
            if time.time() - last_time < 0.3: continue
            last_time = time.time()

            img = cv2.resize(frame, (640, 640))
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            img = np.expand_dims(img, 0)
            outputs = rknn.inference(inputs=[img])
            if not outputs: continue

            preds = outputs[0][0]
            detected_this_frame = False
            frame_max_conf = 0.0

            for pred in preds:
                conf = float(pred[4])
                class_id = int(pred[5])
                if conf > CONF_THRESHOLD:
                    detected_this_frame = True
                    if conf > frame_max_conf:
                        frame_max_conf = conf
                        class_name = CLASS_NAMES[class_id] if class_id < len(CLASS_NAMES) else "unknown"
                        print(f"检测到 {class_name}，置信度 {conf:.2f}")

            if detected_this_frame:
                if frame_max_conf > best_conf:
                    best_conf = frame_max_conf
                    if best_snapshot and os.path.exists(best_snapshot):
                        os.remove(best_snapshot)
                    filename = f"fire_{time.strftime('%Y%m%d_%H%M%S')}.jpg"
                    path = os.path.join(SNAPSHOT_DIR, filename)
                    cv2.imwrite(path, frame)
                    best_snapshot = path
                    print(f"保存最佳截图: {filename}")

                if time.time() - last_alert_time > ALERT_INTERVAL:
                    alert_msg = {
                        "type": "fire",
                        "confidence": round(float(best_conf), 3),
                        "timestamp": time.time(),
                        "snapshot": f"http://10.10.10.31:8082/{os.path.basename(best_snapshot)}" if best_snapshot else ""
                    }
                    mqtt_client.publish(ALERT_TOPIC, json.dumps(alert_msg))
                    last_alert_time = time.time()
                    print(f"告警已推送，置信度: {best_conf:.2f}")
            else:
                if best_conf > 0:
                    print("火情已消失，重置状态")
                    best_conf = 0.0
                    best_snapshot = None

            if os.path.exists(SNAPSHOT_DIR):
                snaps = sorted(os.listdir(SNAPSHOT_DIR))
                while len(snaps) > MAX_SNAPSHOTS:
                    os.remove(os.path.join(SNAPSHOT_DIR, snaps[0]))
                    snaps.pop(0)
    except KeyboardInterrupt:
        print("检测停止")
    finally:
        cap.release()
        rknn.release()
        mqtt_client.loop_stop()


if __name__ == '__main__':
    main()