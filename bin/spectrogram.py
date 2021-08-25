#! /usr/bin/env python3
"""Generate Spectrogram
"""

import argparse
import logging
import matplotlib
matplotlib.use('Agg')
import numpy as np
import scipy.io.wavfile
from matplotlib import pyplot as plt
import lumann.sp
import lumann.utils.file

def main():
    """Generate a spectrogram."""
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('filename',
                        help=('Pointer to a wave file.'))
    parser.add_argument('plotfile',
                        help=('Filename to write spectrogram.'))
    parser.add_argument('-w', '--window-size', default=1024, type=int,
                        help='Window size for the STFT.')
    parser.add_argument('-s', '--step-size', default=512, type=int,
                        help='Step size for the STFT.')

    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG,format='%(asctime)s - %(levelname)s - %(message)s')

    sample_rate, signal = scipy.io.wavfile.read(args.filename)
    logging.debug("Opened file {}, number of samples is {}, sample rate is {}".format(
        args.filename, len(signal), sample_rate))

    signal = np.asarray(signal)
    spec = lumann.sp.stft(signal, args.window_size, args.step_size)
    log_spec = 10 * np.log10(spec)

    plt.imshow(log_spec, interpolation='nearest', aspect='auto', origin='lower')
    plt.colorbar()
    plt.savefig(args.plotfile, bbox_inches='tight')
    plt.clf()


if __name__ == "__main__":
    main()
