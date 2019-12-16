#!/usr/bin/env python3

from flask import Flask, escape, request
import socket
from PIL import Image
import numpy as np
import struct
import time
from classifier import Classifier
from datastore import DataStore

classifier = Classifier(640, 480, 3)
app = Flask(__name__, static_url_path='')


def array_from_file(path):
    from PIL import Image

    img = Image.open(path).convert('RGB')
    w, h = img.size
    return np.array(img)[0:w,0:h,:]


def save_img_buffer(path, size, buf):
    Image.frombuffer('RGB', size, buf).save(path, 'PNG')


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

	    # store the image for training later
        save_img_buffer('/var/poomba/ds/{}.png'.format(time.time()), (w, h), frame)
    except:
        pass

    # do classification here

    # send result back
    is_ok = 1
    sock.sendall(struct.pack('I', is_ok))


def request_classifier_thread():
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


@app.route('/')
def index():
    return app.send_static_file(filename='index.html')

if __name__ == '__main__':
    import threading
    HOST, PORT = '', 1337

    threading.Thread(target=request_classifier_thread).start()

    app.run(host='0.0.0.0', port=8080)





