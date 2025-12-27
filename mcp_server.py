"""Depth Pro MCP Server"""
import os
import sys
import base64
from pathlib import Path
from typing import Optional
from fastmcp import FastMCP

# 添加项目路径
sys.path.insert(0, "/app/src")

import torch
import numpy as np
from PIL import Image
from matplotlib import pyplot as plt
import matplotlib
matplotlib.use('Agg')

import depth_pro
from gpu_manager import gpu_manager

mcp = FastMCP("depth-pro")

def get_device():
    return torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

def load_model():
    model, transform = depth_pro.create_model_and_transforms(device=get_device(), precision=torch.half)
    model.eval()
    return model, transform

@mcp.tool()
def estimate_depth(image_path: str, colormap: str = "turbo") -> dict:
    """
    估计图像深度
    
    Args:
        image_path: 图像文件路径
        colormap: 颜色映射 (turbo/viridis/plasma/magma)
    
    Returns:
        深度估计结果，包含深度统计和输出文件路径
    """
    try:
        path = Path(image_path)
        if not path.exists():
            return {"status": "error", "error": f"File not found: {image_path}"}
        
        model, transform = gpu_manager.get_model(load_model)
        image, _, f_px = depth_pro.load_rgb(str(path))
        prediction = model.infer(transform(image), f_px=f_px)
        
        depth = prediction["depth"].detach().cpu().numpy().squeeze()
        focal = prediction["focallength_px"].detach().cpu().item() if prediction["focallength_px"] is not None else None
        
        # 保存结果
        output_dir = Path("/tmp/depth-pro")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        npz_path = output_dir / f"{path.stem}_depth.npz"
        np.savez_compressed(str(npz_path), depth=depth)
        
        # 生成可视化
        inverse_depth = 1 / depth
        max_inv = min(inverse_depth.max(), 1 / 0.1)
        min_inv = max(1 / 250, inverse_depth.min())
        normalized = (inverse_depth - min_inv) / (max_inv - min_inv)
        cmap = plt.get_cmap(colormap)
        color_depth = (cmap(normalized)[..., :3] * 255).astype(np.uint8)
        
        jpg_path = output_dir / f"{path.stem}_depth.jpg"
        Image.fromarray(color_depth).save(str(jpg_path), quality=95)
        
        return {
            "status": "success",
            "min_depth_m": float(depth.min()),
            "max_depth_m": float(depth.max()),
            "mean_depth_m": float(depth.mean()),
            "focal_length_px": focal,
            "depth_npz_path": str(npz_path),
            "depth_image_path": str(jpg_path)
        }
    except Exception as e:
        gpu_manager.force_offload()
        return {"status": "error", "error": str(e)}

@mcp.tool()
def get_gpu_status() -> dict:
    """
    获取 GPU 状态
    
    Returns:
        GPU 状态信息
    """
    return gpu_manager.get_status()

@mcp.tool()
def release_gpu() -> dict:
    """
    释放 GPU 显存
    
    Returns:
        操作结果
    """
    gpu_manager.force_offload()
    return {"status": "success", "message": "GPU memory released"}

@mcp.tool()
def batch_estimate_depth(image_paths: list[str], colormap: str = "turbo") -> dict:
    """
    批量估计多张图像深度
    
    Args:
        image_paths: 图像文件路径列表
        colormap: 颜色映射
    
    Returns:
        批量处理结果
    """
    results = []
    for path in image_paths:
        result = estimate_depth(path, colormap)
        results.append({"path": path, **result})
    return {"status": "success", "results": results, "total": len(results)}

if __name__ == "__main__":
    mcp.run()
