#!/usr/bin/env python3

import socket
from PIL import Image
import numpy as np
import struct
import time
from classifier import Classifier

classifier = Classifier(1024, 768, 3)

def array_from_file(path):
    from PIL import Image

    img = Image.open(path).convert('RGB')
    w, h = img.size
    return np.array(img)[0:w,0:h,:]


def save_img_buffer(path, size, buf):
    Image.frombuffer('RGB', size, buf).save(path, 'PNG')


# class ClassifyReqHandler(StreamRequestHandler):
#     def __init__(self, request, client_address, server):
#         print('__init__')
#
#     def setup(self):
#         print('setup')
#
#     def handle(self):
#         req = self.request # this is a socket object
#
#         print("got connection")
#
#         # read and decode the header
#         hdr_fmt = 'ccccIII'
#         hdr_buf = req.recv(struct.calcsize(hdr_fmt))
#         m0, m1, m2, m3, w, h, d = struct.unpack(hdr_fmt, hdr_buf)
#
#         # make sure this message starts with the expected magic
#         if (m0 + m1 + m2 + m3) is not 'POOP':
#             req.close()
#             return
#
#         # the request is good, read the frame
#         frame = req.recv(w * h * d)
#         save_img_buffer('/var/poomba/ds/{}.png'.format(time.time()), (w, h), frame)
#
#         # do classification here
#
#         # send result back
#         is_ok = 1
#         req.sendall(struct.pack('I', is_ok))
#
#     def finish(self):
#         print('finish')


def classify_req(sock):
    print("got connection")

    # read and decode the header
    hdr_fmt = 'ccccIII'
    hdr_buf = sock.recv(struct.calcsize(hdr_fmt))
    m0, m1, m2, m3, w, h, d = struct.unpack(hdr_fmt, hdr_buf)

    # make sure this message starts with the expected magic
    if (str(m0 + m1 + m2 + m3, 'utf8')) != 'POOP':
        sock.close()
        return

    # the request is good, read the frame
    frame = b''
    while True:
        chunk = sock.recv(w * h * d - len(frame))

        if len(chunk) == 0:
            break

        frame += chunk

    save_img_buffer('/var/poomba/ds/{}.png'.format(time.time()), (w, h), frame)

    # do classification here

    # send result back
    is_ok = 1
    sock.sendall(struct.pack('I', is_ok))


if __name__ == '__main__':
    HOST, PORT = '', 1337

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()

        while True:
            conn, addr = s.accept()
            with conn:
                print('Connected by', addr)
                classify_req(conn)
                conn.close()