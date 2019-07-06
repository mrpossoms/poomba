#!/usr/bin/env python3

from socketserver import TCPServer
from socketserver import BaseRequestHandler
from PIL import Image
import numpy as np
import struct


def array_from_file(path):
    from PIL import Image

    img = Image.open(path).convert('RGB')
    w, h = img.size
    return np.array(img)[0:w,0:h,:]


def save_img_buffer(path, size, buf):
    Image.frombuffer('RGB', size, buf).save(path, 'PNG')

class ClassifyReqHandler(BaseRequestHandler):
    def __init__(self):
        pass

    def handle(self):
        req = self.request # this is a socket object

        # read and decode the header
        hdr_fmt = 'ccccIII'
        hdr_buf = req.recv(struct.calcsize(hdr_fmt))
        m0, m1, m2, m3, w, h, d = struct.unpack(hdr_fmt, hdr_buf)

        if (m0 + m1 + m2 + m3) is not 'POOP':
            req.close()
            return

        # the request is good, read the frame
        frame = req.recv(w * h * d)
        save_img_buffer('/var/poomba/ds/')

        # do classification here

        # send result back
        is_ok = 1
        req.sendall(struct.pack('I', is_ok))


if __name__ == '__main__':
    HOST, PORT = "localhost", 31337

    server = TCPServer((HOST, PORT), ClassifyReqHandler)

    # Activate the server; this will keep running until you
    # interrupt the program with Ctrl-C
    server.serve_forever()