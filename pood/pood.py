#!/usr/bin/env python3

from flask import Flask, escape, request
import socket
from PIL import Image
import numpy as np
import struct
import sys
import time
import log

from classifier import Classifier
from datastore import DataStore

classifier = Classifier(64, 64, 3)
app = Flask(__name__, static_url_path='')
ds = DataStore('/var/pood/ds')
last_frame_time = 0


def has_cli_arg(arg_str):
    return arg_str in sys.argv


def array_from_file(path):
    from PIL import Image

    img = Image.open(path).convert('RGB')
    w, h = img.size
    return np.array(img)[0:w,0:h,:]


def classify_req(sock):
    global last_frame_time

    log.info("got connection")

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

    img = Image.frombuffer('RGB', (w, h), frame)
    is_poop = False

    # try:
    # do classification here
    collecting_negs = has_cli_arg('learning') and has_cli_arg('negatives')

    if not collecting_negs:
        classifications = classifier.classify(img)
        is_poop = classifications.max() > 0

    if not is_poop:
        ds.store(0).tile(img, tiles=10)

    last_frame_time = time.time()
    # except:
    #     pass

    # send result back
    sock.sendall(struct.pack('I', int(not is_poop)))


def request_classifier_thread():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen()

        while True:
            conn, addr = s.accept()
            with conn:
                log.info('Connected by %s', addr)
                classify_req(conn)
                conn.close()


def training_thread():
    while True:
        now = time.time()
        dt = now - last_frame_time

        if 10 < dt < 60:
            c = Classifier(64, 64, 3)
            c.train(ds, epochs=1000)

        time.sleep(10)


@app.route('/')
def index():
    return app.send_static_file(filename='index.html')

if __name__ == '__main__':
    import threading
    HOST, PORT = '', 1337

    if has_cli_arg('learn') and has_cli_arg('negatives'):
        log.info('Learning only negative examples')

    classifier.load()

    threading.Thread(target=request_classifier_thread).start()
    threading.Thread(target=training_thread).start()

    app.run(host='0.0.0.0', port=8080)





