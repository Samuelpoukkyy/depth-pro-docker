"""Depth Pro Web 服务 v2 - 增强版 UI + API"""
import os
import io
import uuid
import base64
import numpy as np
from pathlib import Path
from PIL import Image
from flask import Flask, request, jsonify, render_template, send_file, send_from_directory
from flask_cors import CORS
from flasgger import Swagger
import torch
from matplotlib import pyplot as plt
import matplotlib
matplotlib.use('Agg')

from gpu_manager import gpu_manager
import depth_pro

app = Flask(__name__)
CORS(app)
swagger = Swagger(app, template={
    "info": {"title": "Depth Pro API", "version": "2.0", "description": "单目深度估计 API - 增强版"},
    "basePath": "/"
})

UPLOAD_DIR = Path("/tmp/depth-pro")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

def get_device():
    if torch.cuda.is_available():
        return torch.device("cuda:0")
    return torch.device("cpu")

def load_model():
    model, transform = depth_pro.create_model_and_transforms(device=get_device(), precision=torch.half)
    model.eval()
    return model, transform

def process_image(image_path, colormap="turbo", focal_length=None):
    model, transform = gpu_manager.get_model(load_model)
    image, _, f_px = depth_pro.load_rgb(image_path)
    
    # 使用手动焦距或自动估计
    input_f_px = float(focal_length) if focal_length else f_px
    
    prediction = model.infer(transform(image), f_px=input_f_px)
    
    depth = prediction["depth"].detach().cpu().numpy().squeeze()
    focal = prediction["focallength_px"].detach().cpu().item() if prediction["focallength_px"] is not None else None
    
    # 生成可视化 (inverse depth for better visualization)
    inverse_depth = 1 / np.clip(depth, 0.1, 250)
    max_inv = inverse_depth.max()
    min_inv = inverse_depth.min()
    normalized = (inverse_depth - min_inv) / (max_inv - min_inv + 1e-8)
    
    cmap = plt.get_cmap(colormap)
    color_depth = (cmap(normalized)[..., :3] * 255).astype(np.uint8)
    
    # 16-bit PNG (normalized depth)
    depth_normalized = (depth - depth.min()) / (depth.max() - depth.min() + 1e-8)
    depth_16bit = (depth_normalized * 65535).astype(np.uint16)
    
    return {
        "depth": depth,
        "depth_16bit": depth_16bit,
        "focal_length_px": focal,
        "color_image": color_depth,
        "min_depth": float(depth.min()),
        "max_depth": float(depth.max()),
        "mean_depth": float(depth.mean()),
        "image_size": f"{image.shape[1]}x{image.shape[0]}"
    }

@app.route("/")
def index():
    return render_template("index_v2.html")

@app.route("/v1")
def index_v1():
    """旧版 UI"""
    return render_template("index.html")

@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory("static", filename)

@app.route("/health")
def health():
    """健康检查
    ---
    responses:
      200:
        description: 服务正常
    """
    return jsonify({"status": "ok", "gpu": gpu_manager.get_status()})

@app.route("/api/predict", methods=["POST"])
def predict():
    """深度估计
    ---
    tags: [API]
    consumes: [multipart/form-data]
    parameters:
      - name: file
        in: formData
        type: file
        required: true
        description: 输入图像
      - name: colormap
        in: formData
        type: string
        default: turbo
        description: 颜色映射 (turbo/viridis/plasma/magma/inferno/gray)
      - name: focal_length
        in: formData
        type: number
        description: 手动指定焦距(像素)，留空则自动估计
    responses:
      200:
        description: 深度估计结果
    """
    if "file" not in request.files:
        return jsonify({"error": "No file"}), 400
    
    file = request.files["file"]
    colormap = request.form.get("colormap", "turbo")
    focal_length = request.form.get("focal_length")
    
    task_id = str(uuid.uuid4())[:8]
    input_path = UPLOAD_DIR / f"{task_id}_input.jpg"
    file.save(str(input_path))
    
    try:
        result = process_image(str(input_path), colormap, focal_length)
        
        # 保存结果
        depth_path = UPLOAD_DIR / f"{task_id}_depth.npz"
        color_path = UPLOAD_DIR / f"{task_id}_color.jpg"
        depth16_path = UPLOAD_DIR / f"{task_id}_depth16.png"
        
        np.savez_compressed(str(depth_path), depth=result["depth"])
        Image.fromarray(result["color_image"]).save(str(color_path), quality=95)
        Image.fromarray(result["depth_16bit"]).save(str(depth16_path))
        
        # Base64 编码
        buf = io.BytesIO()
        Image.fromarray(result["color_image"]).save(buf, format="JPEG", quality=90)
        color_b64 = base64.b64encode(buf.getvalue()).decode()
        
        return jsonify({
            "task_id": task_id,
            "focal_length_px": result["focal_length_px"],
            "min_depth_m": result["min_depth"],
            "max_depth_m": result["max_depth"],
            "mean_depth_m": result["mean_depth"],
            "image_size": result["image_size"],
            "depth_image_base64": color_b64,
            "download_npz": f"/api/download/{task_id}/depth.npz",
            "download_jpg": f"/api/download/{task_id}/color.jpg",
            "download_16bit": f"/api/download/{task_id}/depth16.png"
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/api/download/<task_id>/<filename>")
def download(task_id, filename):
    """下载结果文件
    ---
    tags: [API]
    parameters:
      - name: task_id
        in: path
        type: string
        required: true
      - name: filename
        in: path
        type: string
        required: true
    responses:
      200:
        description: 文件下载
    """
    file_map = {
        "depth.npz": f"{task_id}_depth.npz",
        "color.jpg": f"{task_id}_color.jpg",
        "depth16.png": f"{task_id}_depth16.png"
    }
    
    if filename not in file_map:
        return jsonify({"error": "Invalid file"}), 400
    
    path = UPLOAD_DIR / file_map[filename]
    if not path.exists():
        return jsonify({"error": "Not found"}), 404
    return send_file(str(path), as_attachment=True)

@app.route("/api/gpu/status")
def gpu_status():
    """GPU 状态
    ---
    tags: [GPU]
    responses:
      200:
        description: GPU 状态信息
    """
    return jsonify(gpu_manager.get_status())

@app.route("/api/gpu/offload", methods=["POST"])
def gpu_offload():
    """释放 GPU 显存
    ---
    tags: [GPU]
    responses:
      200:
        description: 显存已释放
    """
    gpu_manager.force_offload()
    return jsonify({"status": "offloaded"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8500)), debug=False)
