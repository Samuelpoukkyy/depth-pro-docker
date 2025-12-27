// Depth Pro v2 - App Logic
const i18n = {
    'zh-CN': {
        subtitle: '零样本单目深度估计 · 0.3秒生成2.25MP高精度深度图',
        'stat-speed': '推理速度', 'stat-res': '输出分辨率',
        params: '参数设置', colormap: '颜色映射',
        'focal-input': '焦距设置', 'focal-auto': '自动估计', 'focal-manual': '手动输入',
        'focal-hint': '留空则自动估计',
        'output-format': '输出格式', 'model-status': '模型状态:',
        'release-gpu': '释放显存', 'tips-title': '使用技巧',
        tip1: '✓ 室内/近距离场景效果最佳', tip2: '✓ 高分辨率图像细节更丰富',
        tip3: '⚠ 远景(>20m)深度值仅供参考', tip4: '✓ 支持 JPG/PNG/WebP/HEIC',
        'drop-hint': '拖拽图像到此处，或点击选择', process: '开始处理',
        results: '处理结果', original: '原图', 'depth-map': '深度图',
        near: '近', far: '远',
        'min-depth': '最近距离', 'max-depth': '最远距离', 'mean-depth': '平均深度',
        focal: '焦距', 'infer-time': '推理耗时', 'img-size': '图像尺寸',
        processing: '处理中...', uploading: '上传中...', inferring: '推理中...',
        done: '处理完成!', error: '处理失败'
    },
    'en': {
        subtitle: 'Zero-shot Monocular Depth · 2.25MP depth map in 0.3s',
        'stat-speed': 'Inference', 'stat-res': 'Resolution',
        params: 'Parameters', colormap: 'Colormap',
        'focal-input': 'Focal Length', 'focal-auto': 'Auto', 'focal-manual': 'Manual',
        'focal-hint': 'Leave empty for auto estimation',
        'output-format': 'Output Format', 'model-status': 'Model:',
        'release-gpu': 'Release GPU', 'tips-title': 'Tips',
        tip1: '✓ Best for indoor/close-range', tip2: '✓ Higher resolution = more details',
        tip3: '⚠ Far scenes (>20m) depth is approximate', tip4: '✓ Supports JPG/PNG/WebP/HEIC',
        'drop-hint': 'Drop image here or click to select', process: 'Process',
        results: 'Results', original: 'Original', 'depth-map': 'Depth Map',
        near: 'Near', far: 'Far',
        'min-depth': 'Min Depth', 'max-depth': 'Max Depth', 'mean-depth': 'Mean Depth',
        focal: 'Focal', 'infer-time': 'Inference', 'img-size': 'Image Size',
        processing: 'Processing...', uploading: 'Uploading...', inferring: 'Inferring...',
        done: 'Done!', error: 'Failed'
    }
};

let currentLang = localStorage.getItem('lang') || 'zh-CN';
let selectedFile = null;
let selectedColormap = 'turbo';

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    changeLang(currentLang);
    setupEventListeners();
    updateGPU();
    setInterval(updateGPU, 5000);
});

function setupEventListeners() {
    // File input
    const zone = document.getElementById('uploadZone');
    const fileInput = document.getElementById('fileInput');
    
    zone.onclick = () => fileInput.click();
    zone.ondragover = e => { e.preventDefault(); zone.classList.add('dragover'); };
    zone.ondragleave = () => zone.classList.remove('dragover');
    zone.ondrop = e => { e.preventDefault(); zone.classList.remove('dragover'); handleFile(e.dataTransfer.files[0]); };
    fileInput.onchange = e => handleFile(e.target.files[0]);

    // Colormap buttons
    document.querySelectorAll('.colormap-btn').forEach(btn => {
        btn.onclick = () => {
            document.querySelectorAll('.colormap-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            selectedColormap = btn.dataset.value;
            updateLegend();
        };
    });

    // Focal toggle
    document.querySelectorAll('[data-focal]').forEach(btn => {
        btn.onclick = () => {
            document.querySelectorAll('[data-focal]').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            document.querySelector('.focal-manual-input').style.display = 
                btn.dataset.focal === 'manual' ? 'block' : 'none';
        };
    });

    // View toggle
    document.querySelectorAll('.view-btn').forEach(btn => {
        btn.onclick = () => {
            document.querySelectorAll('.view-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const container = document.getElementById('comparisonContainer');
            container.className = 'comparison-container';
            if (btn.dataset.view === 'slider') container.classList.add('slider-view');
            if (btn.dataset.view === 'depth') container.classList.add('depth-only');
        };
    });
}

function changeLang(lang) {
    currentLang = lang;
    localStorage.setItem('lang', lang);
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (i18n[lang] && i18n[lang][key]) el.textContent = i18n[lang][key];
    });
    document.getElementById('langSelect').value = lang;
}

function handleFile(file) {
    if (!file || !file.type.startsWith('image/')) return;
    selectedFile = file;
    
    const reader = new FileReader();
    reader.onload = e => {
        const preview = document.getElementById('previewImg');
        preview.src = e.target.result;
        preview.style.display = 'block';
        document.getElementById('uploadContent').style.display = 'none';
        document.getElementById('clearBtn').style.display = 'block';
        document.getElementById('processBtn').disabled = false;
        
        // Show file info
        const size = (file.size / 1024 / 1024).toFixed(2);
        document.getElementById('fileInfo').textContent = `${file.name} (${size} MB)`;
    };
    reader.readAsDataURL(file);
}

function clearImage() {
    selectedFile = null;
    document.getElementById('previewImg').style.display = 'none';
    document.getElementById('uploadContent').style.display = 'block';
    document.getElementById('clearBtn').style.display = 'none';
    document.getElementById('processBtn').disabled = true;
    document.getElementById('fileInfo').textContent = '';
    document.getElementById('fileInput').value = '';
}

async function process() {
    if (!selectedFile) return;
    
    const btn = document.getElementById('processBtn');
    const progressContainer = document.getElementById('progressContainer');
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');
    
    btn.disabled = true;
    progressContainer.style.display = 'block';
    progressText.textContent = i18n[currentLang].uploading;
    progressFill.style.width = '20%';
    
    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('colormap', selectedColormap);
    
    // Check for manual focal length
    const focalInput = document.getElementById('focalInput');
    if (focalInput.value && document.querySelector('[data-focal="manual"]').classList.contains('active')) {
        formData.append('focal_length', focalInput.value);
    }
    
    const startTime = performance.now();
    
    try {
        progressText.textContent = i18n[currentLang].inferring;
        progressFill.style.width = '50%';
        
        const res = await fetch('/api/predict', { method: 'POST', body: formData });
        const data = await res.json();
        
        progressFill.style.width = '100%';
        
        if (data.error) throw new Error(data.error);
        
        const inferTime = ((performance.now() - startTime) / 1000).toFixed(2);
        
        // Display results
        document.getElementById('origImg').src = document.getElementById('previewImg').src;
        document.getElementById('depthImg').src = 'data:image/jpeg;base64,' + data.depth_image_base64;
        
        document.getElementById('minDepth').textContent = data.min_depth_m.toFixed(2);
        document.getElementById('maxDepth').textContent = data.max_depth_m.toFixed(2);
        document.getElementById('meanDepth').textContent = data.mean_depth_m.toFixed(2);
        document.getElementById('focalLen').textContent = data.focal_length_px ? data.focal_length_px.toFixed(0) : 'N/A';
        document.getElementById('inferTime').textContent = inferTime;
        document.getElementById('imgSize').textContent = data.image_size || '-';
        
        document.getElementById('dlJpg').href = data.download_jpg;
        document.getElementById('dlNpz').href = data.download_npz;
        
        if (data.download_16bit) {
            document.getElementById('dl16bit').href = data.download_16bit;
            document.getElementById('dl16bit').style.display = 'flex';
        }
        
        document.getElementById('resultsSection').style.display = 'block';
        progressText.textContent = i18n[currentLang].done;
        
        // Scroll to results
        document.getElementById('resultsSection').scrollIntoView({ behavior: 'smooth' });
        
    } catch (e) {
        progressText.textContent = i18n[currentLang].error + ': ' + e.message;
        progressFill.style.background = 'var(--error)';
    }
    
    btn.disabled = false;
    setTimeout(() => {
        progressFill.style.width = '0%';
        progressFill.style.background = '';
    }, 2000);
}

async function updateGPU() {
    try {
        const res = await fetch('/api/gpu/status');
        const data = await res.json();
        
        const indicator = document.getElementById('gpuIndicator');
        const nameEl = document.getElementById('gpuName');
        const memFill = document.getElementById('memoryFill');
        const memText = document.getElementById('memoryText');
        const modelStatus = document.getElementById('modelStatus');
        const statNum = document.getElementById('gpuStatNum');
        
        if (data.gpu && data.gpu.name) {
            indicator.classList.remove('offline');
            nameEl.textContent = data.gpu.name;
            
            const usedPct = (data.gpu.memory_used / data.gpu.memory_total * 100).toFixed(0);
            memFill.style.width = usedPct + '%';
            memText.textContent = `${data.gpu.memory_used.toFixed(1)} / ${data.gpu.memory_total.toFixed(1)} GB`;
            
            statNum.textContent = data.gpu.name.replace('NVIDIA ', '').split(' ')[0];
        } else {
            indicator.classList.add('offline');
            nameEl.textContent = 'No GPU';
            statNum.textContent = 'CPU';
        }
        
        modelStatus.textContent = data.model_loaded ? '已加载' : '未加载';
        modelStatus.className = 'status-badge ' + (data.model_loaded ? 'loaded' : 'unloaded');
        
    } catch (e) {
        console.error('GPU status error:', e);
    }
}

async function offloadGPU() {
    await fetch('/api/gpu/offload', { method: 'POST' });
    updateGPU();
}

function updateLegend() {
    const gradients = {
        turbo: 'linear-gradient(90deg, #30123b, #7a0403, #d93806, #f1b32c, #a5fc4e, #28bbec, #4662d7)',
        viridis: 'linear-gradient(90deg, #440154, #414487, #2a788e, #22a884, #7ad151, #fde725)',
        plasma: 'linear-gradient(90deg, #0d0887, #6a00a8, #b12a90, #e16462, #fca636, #f0f921)',
        magma: 'linear-gradient(90deg, #000004, #3b0f70, #8c2981, #de4968, #fe9f6d, #fcfdbf)',
        inferno: 'linear-gradient(90deg, #000004, #420a68, #932667, #dd513a, #fca50a, #fcffa4)',
        gray: 'linear-gradient(90deg, #000, #fff)'
    };
    document.getElementById('legendBar').style.background = gradients[selectedColormap] || gradients.turbo;
}
