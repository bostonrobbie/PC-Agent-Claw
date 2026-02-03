# Test Ollama in CPU-only mode
$env:OLLAMA_NUM_GPU = "0"
$env:CUDA_VISIBLE_DEVICES = "-1"

Write-Host "Starting Ollama in CPU-only mode..."
Write-Host "OLLAMA_NUM_GPU = $env:OLLAMA_NUM_GPU"
Write-Host "CUDA_VISIBLE_DEVICES = $env:CUDA_VISIBLE_DEVICES"
Write-Host ""

# Start Ollama in background
Start-Process -FilePath "C:\Users\User\AppData\Local\Programs\Ollama\ollama.exe" -ArgumentList "serve" -WindowStyle Hidden

Write-Host "Waiting 5 seconds for Ollama to start..."
Start-Sleep -Seconds 5

Write-Host ""
Write-Host "Testing with qwen2.5:0.5b..."
& "C:\Users\User\AppData\Local\Programs\Ollama\ollama.exe" run qwen2.5:0.5b "Hello, test message"

Write-Host ""
Write-Host "Test complete."
