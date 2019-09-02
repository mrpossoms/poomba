#!/usr/bin/env python3

import socket
from PIL import Image
import numpy as np
import struct
import time
import pylab
from classifier import Classifier

classifier = Classifier(640, 480, 3)

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

        if len(chunk) == 0 and len(frame) > 0:
            break

        frame += chunk

    try:
	# run a DFT on the image to check for blurryness


	# store the image for training later
        img = Image.frombuffer('RGB', (w, h), frame)

        g_w, g_h = img.width // 2, img.height // 2
        grey_img = np.asarray(img.convert(mode='L').resize((g_w, g_h)).getdata()).astype(np.int8).reshape((g_h, g_w))

        K = np.array([
            [ 0, 1, 0 ],
            [ 1,-4, 1 ],
            [ 0, 1, 0 ]
        ])
        k_r, k_c = K.shape[0], K.shape[1]
        K = K.flatten()

        mu, n, var = np.average(grey_img), 0, 0

        # for r in range(0, g_h - k_r):
        #     for c in range(0, g_w - k_c):
        #         window = grey_img[r:r + k_r, c:c + k_c].flatten()
        #         s = np.inner(K, window)
        #         mu += s
        #         n += 1
        # mu /= n

        laplacian = np.ndarray(shape=(g_h-k_r, g_w-k_c))

        for r in range(0, g_h - k_r):
            for c in range(0, g_w - k_c):
                window = grey_img[r:r + k_r, c:c + k_c].flatten()
                laplacian[r][c] = np.inner(K, window)
        var = np.var(laplacian)

        print('Variance: {}'.format(var))

        if var >= 30000:
            save_img_buffer('/var/poomba/ds/{}-{}.png'.format(time.time(), var), (w, h), frame)
    except:
        pass

    # do classification here

    # send result back
    is_ok = 1
    sock.sendall(struct.pack('I', is_ok))


if __name__ == '__main__':
    HOST, PORT = '', 1337

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen()

        while True:
            conn, addr = s.accept()
            with conn:
                print('Connected by', addr)
                classify_req(conn)
                conn.close()
