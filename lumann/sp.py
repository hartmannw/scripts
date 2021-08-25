"""Collection of functions for signal processing

Methods
--------
stft(wav_date, window, step)
    Run the STFT algorithm and return the results.
"""

import logging
import numpy as np

logger = logging.getLogger(__name__)

def stft(wav_data, window, step):
    hann = np.hanning(window)
    
    num_samples = len(wav_data)
    freq_bins = int(window / 2) + 1

    total_frames = int(num_samples/step)

    if total_frames <= 0:
        return np.array([])
    
    spec = np.zeros((freq_bins, total_frames))

    start = 0
    end = window
    frame = 0

    while frame < total_frames:
        tmp_data = wav_data[start:end]

        if len(tmp_data) < window:  # skip this frame
            start += step
            end += step
            frame += 1
            continue

        spec[:,frame] = np.transpose(np.abs(np.fft.fft(np.multiply(tmp_data, hann))[0:freq_bins]))

        start += step
        end += step
        frame += 1

    return spec

