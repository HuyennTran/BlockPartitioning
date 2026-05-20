#!/bin/bash

# ========================================================
# TASK 1.4 - AUTOMATED VTM ENCODING SCRIPT (DRY RUN)
# ========================================================

# Array containing the target video sequence (Only 'foreman' for testing)
VIDEOS=("foreman")

# Array containing the 4 standard Quantization Parameters (QP)
QPS=(22 27 32 37)

echo "========================================================"
echo "[START] Executing Task 1.4 for Test Sequences..."
echo "========================================================"

# Loop through each video sequence
for VIDEO in "${VIDEOS[@]}"; do
    # Loop through each QP level
    for QP in "${QPS[@]}"; do
        echo "--------------------------------------------------------"
        echo "[PROCESSING] Video: ${VIDEO}.yuv | QP: ${QP}"
        echo "--------------------------------------------------------"
        
        # Clear any residual log file from previous encoder runs
        rm -f partition_log.csv
        
        # Execute VTM EncoderApp
        # Redirect stdout to a text file to capture PSNR, Bitrate, and Time data
        ./bin/umake/gcc-13.3/x86_64/release/EncoderApp \
            -c cfg/encoder_randomaccess_vtm.cfg \
            -i ${VIDEO}.yuv \
            -wdt 416 \
            -hgt 240 \
            -fr 30 \
            -f 30 \
            -q ${QP} \
            -b ${VIDEO}_qp${QP}.vvc > terminal_log_${VIDEO}_qp${QP}.txt
        
        # Verify if the C++ code successfully generated the coordinate log
        if [ -f "partition_log.csv" ]; then
            # Rename the CSV to prevent it from being overwritten in the next loop
            mv partition_log.csv ${VIDEO}_qp${QP}_partition.csv
            echo "[SUCCESS] Generated: ${VIDEO}_qp${QP}_partition.csv"
            echo "[SUCCESS] Captured terminal stats in: terminal_log_${VIDEO}_qp${QP}.txt"
        else
            echo "[ERROR] 'partition_log.csv' was not found! Check C++ injection."
        fi
        
    done
done

echo "========================================================"
echo "[FINISHED] Task 1.4 Dry Run Completed Successfully!"
echo "========================================================"
