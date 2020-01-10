#!/usr/bin/env python3

import sys
import log
import pathlib
from PIL import Image
from PIL import ImageEnhance

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Usage:')
        print('aug INPUT_FILE OUTPUT_PATH')
        exit(1)

    _, input_path_str, output_path = sys.argv
    input_path = pathlib.Path(input_path_str)

    with open(input_path, 'rb') as ifp:
        base = Image.open(ifp)
        imgs = [ base, base.transpose(method=Image.FLIP_LEFT_RIGHT) ]

        lr = 0
        for img in imgs:
            for brightness in [ 0.5, 0.6, 0.7, 0.8, 0.9]:
                opath = '{}/{}.{}.{}.png'.format(output_path, input_path.stem, lr, brightness)
                ImageEnhance.Brightness(img).enhance(brightness).save(opath)
            lr += 1