# NVIDIA Driver Update Guide - Fix CUDA 13.1 Support

## Problem Summary
- **Current Driver:** 566.14 (supports CUDA 12.7 max)
- **Installed CUDA:** 13.1
- **Required Driver:** 570.65+ (for CUDA 13.1 support)
- **Latest Available:** 572.70 WHQL

## Solution: Update NVIDIA Driver to 572.70

### Step 1: Download Latest Driver

**Option A: NVIDIA Official Website (Recommended)**
1. Visit: https://www.nvidia.com/en-us/geforce/drivers/
2. Select:
   - Product Type: GeForce
   - Product Series: GeForce RTX 30 Series
   - Product: GeForce RTX 3060
   - Operating System: Windows 11 64-bit (or your OS)
   - Download Type: Game Ready Driver
3. Click "Search"
4. Download the latest driver (should be 572.70 or newer)

**Option B: Direct Download Links**
- Guru3D: https://www.guru3d.com/download/nvidia-geforce-57270-whql-driver-download/
- Softpedia: https://drivers.softpedia.com/get/GRAPHICS-BOARD/NVIDIA/

### Step 2: Prepare for Installation

**Before Installing:**
1. Close all GPU-intensive applications
2. Close Ollama (if running)
3. Save all work

**Clean Installation (Recommended):**
- During driver installation, select "Custom (Advanced)" installation
- Check "Perform a clean installation" option
- This removes old driver files and prevents conflicts

### Step 3: Install Driver

1. Run the downloaded installer (.exe file)
2. Choose "Custom (Advanced)" installation
3. Select "Perform a clean installation"
4. Follow the installation wizard
5. Restart your computer when prompted

### Step 4: Verify Installation

After restart, check the driver version:
```bash
nvidia-smi
```

Should show: **Driver Version: 572.70** (or newer)

### Step 5: Test Ollama with GPU

```bash
# Start Ollama service
ollama serve

# Test with small model (in new terminal)
ollama run qwen2.5:0.5b "Hello world"
```

Should now work without "CUDA error"!

---

## Expected Results After Update

✅ **Driver:** 572.70 (supports CUDA 13.1)
✅ **CUDA:** 13.1 (now compatible)
✅ **Ollama:** GPU acceleration working
✅ **Performance:** Fast LLM inference

---

## Alternative: Downgrade CUDA (Not Recommended)

If driver update doesn't work, you could uninstall CUDA 13.1 and install CUDA 12.7:
- Download CUDA 12.7: https://developer.nvidia.com/cuda-12-7-0-download-archive
- Uninstall CUDA 13.1 first
- Install CUDA 12.7
- More complex and risky

**Recommendation:** Update driver first (easier and safer)

---

## Troubleshooting

### Issue: Driver won't install
**Solution:** Uninstall old driver using DDU (Display Driver Uninstaller) in Safe Mode

### Issue: Still getting CUDA error after update
**Solution:**
1. Verify driver version with `nvidia-smi`
2. Check CUDA version with `nvcc --version`
3. Restart Ollama service completely
4. Test with smallest model first

### Issue: System instability after update
**Solution:** Roll back to previous driver in Device Manager

---

## Links & References

- [NVIDIA GeForce Drivers](https://www.nvidia.com/en-us/geforce/drivers/)
- [CUDA Compatibility Documentation](https://docs.nvidia.com/deploy/cuda-compatibility/)
- [GeForce 572.70 Driver Download - Guru3D](https://www.guru3d.com/download/nvidia-geforce-57270-whql-driver-download/)
- [NVIDIA RTX Driver Release 570](https://www.nvidia.com/en-us/drivers/details/240596/)

---

**Estimated Time:** 10-15 minutes (plus restart)
**Difficulty:** Easy
**Risk:** Low (can roll back if needed)
