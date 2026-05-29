#!/bin/bash

# ========================================================
# TASK 1.4 - AUTOMATED VTM ENCODING SCRIPT
# Run this script from the ROOT directory!
# Command: bash backend/run_task_1_4.sh
# ========================================================

OUTPUT_DIR="samples/sample2"

# Array containing the target video sequence
VIDEOS=("akiyo_cif")

# Array containing the 4 standard Quantization Parameters (QP)
QPS=(22 27 32 37)

echo "========================================================"
echo "[START] Executing Task 1.4 for Test Sequences..."
echo "========================================================"

mkdir -p ${OUTPUT_DIR}

# Loop through each video sequence
for VIDEO in "${VIDEOS[@]}"; do
    # Loop through each QP level
    for QP in "${QPS[@]}"; do
        echo "--------------------------------------------------------"
        echo "[PROCESSING] Video: ${VIDEO}.yuv | QP: ${QP}"
        echo "--------------------------------------------------------"
        
        # Clear any residual log file from previous encoder runs in root
        rm -f partition_log.csv
        
        # Execute VTM EncoderApp
        ./backend/bin/EncoderApp \
            -c ./backend/cfg/encoder_randomaccess_vtm.cfg \
            -i ./${VIDEO}.yuv \
            -wdt 352 \
            -hgt 288\
            -fr 30 \
            -f 30 \
            -q ${QP} \
            -b ${OUTPUT_DIR}/${VIDEO}_qp${QP}.vvc > ${OUTPUT_DIR}/terminal_log_${VIDEO}_qp${QP}.txt
        
        # Verify if the C++ code successfully generated the coordinate log
        if [ -f "partition_log.csv" ]; then
            mv partition_log.csv ${OUTPUT_DIR}/${VIDEO}_qp${QP}_partition.csv
            
            echo "[SUCCESS] Generated: ${OUTPUT_DIR}/${VIDEO}_qp${QP}_partition.csv"
            echo "[SUCCESS] Captured terminal stats in: ${OUTPUT_DIR}/terminal_log_${VIDEO}_qp${QP}.txt"
        else
            echo "[ERROR] 'partition_log.csv' was not found! Check C++ injection."
        fi
        
    done
done

echo "========================================================"
echo "[FINISHED] Task 1.4 Encoding Completed!"
echo "========================================================"