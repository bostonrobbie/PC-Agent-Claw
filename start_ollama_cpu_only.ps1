# Start Ollama in CPU-only mode to avoid CUDA errors
$env:OLLAMA_NUM_GPU = "0"
$env:CUDA_VISIBLE_DEVICES = ""

Write-Host "Starting Ollama in CPU-only mode..."
Write-Host "OLLAMA_NUM_GPU = $env:OLLAMA_NUM_GPU"

& "C:\Users\User\AppData\Local\Programs\Ollama\ollama.exe" serve
