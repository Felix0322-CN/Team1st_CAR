#!/usr/bin/env python3
"""Run the end-to-end YOLO26 RKNN model on an RK3588 board."""
"""python3 infer_rk3588_yolo26.py \
  --model best_rk3588.rknn \
  --image 1.jpg \
  --output result_rk3588.jpg"""
import argparse
import time
from pathlib import Path

import cv2
import numpy as np


CLASS_NAMES = ("fire",)


def letterbox(image: np.ndarray, size: int = 640, color=(114, 114, 114)):
    h, w = image.shape[:2]
    ratio = min(size / h, size / w)
    nw, nh = int(round(w * ratio)), int(round(h * ratio))
    resized = cv2.resize(image, (nw, nh), interpolation=cv2.INTER_LINEAR)
    dw, dh = size - nw, size - nh
    left, top = dw // 2, dh // 2
    output = cv2.copyMakeBorder(
        resized, top, dh - top, left, dw - left,
        cv2.BORDER_CONSTANT, value=color,
    )
    return output, ratio, (left, top)


def parse_end2end(output, confidence: float, ratio: float, pad, original_shape):
    pred = np.asarray(output).squeeze()
    if pred.ndim == 1 and pred.size % 6 == 0:
        pred = pred.reshape(-1, 6)
    if pred.ndim != 2 or pred.shape[-1] != 6:
        raise RuntimeError(f"Expected RKNN output [1, 300, 6], got {np.asarray(output).shape}")

    pred = pred[np.isfinite(pred).all(axis=1) & (pred[:, 4] >= confidence)]
    if not len(pred):
        return pred

    pred = pred.copy()
    pred[:, [0, 2]] = (pred[:, [0, 2]] - pad[0]) / ratio
    pred[:, [1, 3]] = (pred[:, [1, 3]] - pad[1]) / ratio
    h, w = original_shape[:2]
    pred[:, [0, 2]] = pred[:, [0, 2]].clip(0, w - 1)
    pred[:, [1, 3]] = pred[:, [1, 3]].clip(0, h - 1)
    return pred


def draw(image: np.ndarray, detections: np.ndarray) -> None:
    for x1, y1, x2, y2, score, class_id in detections:
        class_id = int(class_id)
        name = CLASS_NAMES[class_id] if 0 <= class_id < len(CLASS_NAMES) else str(class_id)
        p1, p2 = (int(x1), int(y1)), (int(x2), int(y2))
        cv2.rectangle(image, p1, p2, (0, 0, 255), 2)
        cv2.putText(
            image, f"{name} {score:.2f}", (p1[0], max(20, p1[1] - 6)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2, cv2.LINE_AA,
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="best_rk3588.rknn")
    parser.add_argument("--image", default="1.jpg")
    parser.add_argument("--output", default="result_rk3588.jpg")
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--loops", type=int, default=1, help="Inference count for timing")
    parser.add_argument(
        "--core", choices=("auto", "0", "1", "2", "012"), default="012",
        help="RK3588 NPU core selection",
    )
    args = parser.parse_args()

    from rknnlite.api import RKNNLite

    model, image_path = Path(args.model), Path(args.image)
    if not model.is_file():
        raise FileNotFoundError(model)
    image = cv2.imread(str(image_path))
    if image is None:
        raise FileNotFoundError(f"Cannot read image: {image_path}")

    padded, ratio, pad = letterbox(image, args.imgsz)
    rgb = cv2.cvtColor(padded, cv2.COLOR_BGR2RGB)
    core_masks = {
        "auto": RKNNLite.NPU_CORE_AUTO,
        "0": RKNNLite.NPU_CORE_0,
        "1": RKNNLite.NPU_CORE_1,
        "2": RKNNLite.NPU_CORE_2,
        "012": RKNNLite.NPU_CORE_0_1_2,
    }

    rknn = RKNNLite(verbose=False)
    try:
        ret = rknn.load_rknn(str(model))
        if ret != 0:
            raise RuntimeError(f"load_rknn failed: {ret}")
        ret = rknn.init_runtime(core_mask=core_masks[args.core])
        if ret != 0:
            raise RuntimeError(f"init_runtime failed: {ret}")

        # One warm-up run, excluded from timing.
        model_input = np.expand_dims(rgb, axis=0)
        outputs = rknn.inference(inputs=[model_input], data_format=["nhwc"])
        start = time.perf_counter()
        for _ in range(max(1, args.loops)):
            outputs = rknn.inference(inputs=[model_input], data_format=["nhwc"])
        elapsed = (time.perf_counter() - start) * 1000 / max(1, args.loops)
    finally:
        rknn.release()

    detections = parse_end2end(outputs[0], args.conf, ratio, pad, image.shape)
    draw(image, detections)
    if not cv2.imwrite(args.output, image):
        raise RuntimeError(f"Failed to write {args.output}")
    print(f"detections={len(detections)}, inference={elapsed:.2f} ms, saved={args.output}")


if __name__ == "__main__":
    main()
