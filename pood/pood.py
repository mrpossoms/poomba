#!/usr/bin/env python3

from flask import Flask, escape, request, send_file, redirect
from flask_socketio import SocketIO

import socket
from PIL import Image
import numpy as np
import struct
import sys
import time
import log
import os

from classifier import Classifier
from datastore import DataStore


classifier = Classifier(16, 16, 3)
app = Flask(__name__, static_url_path='')
socketio = SocketIO(app)
ds = DataStore('/var/pood/ds')
last_frame_time = 0
frames_received = 100
positives_last_frame = 0
force_training = False
collecting_negs = False

def has_cli_arg(arg_str):
    return arg_str in sys.argv


def classify_req(sock):
    global last_frame_time, frames_received, positives_last_frame, collecting_negs

    start_time = time.time()
    log.info("got connection")

    # read and decode the header
    read_start = time.time()
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
    log.info('Frame read took %f sec', time.time() - read_start)

    is_poop = False
    frames_received += 1

    # try:
    # do classification here
    collecting_pos = has_cli_arg('collect') and has_cli_arg('positives')

    if collecting_negs:
        ds.store(0).tile(img, tiles=10, size=(16, 16))
    elif collecting_pos:
        ds.store('src')._store(img)
    else:
        classifications, visualization = classifier.classify(img)
        positives = classifications.sum()
        is_poop = positives + positives_last_frame >= 4
        positives_last_frame = positives

        if is_poop:
            # the frame was classified as poop. Save it to confirm later
            DataStore('/tmp/pood/ds').store(1).image(img)

        visualization = np.dstack((visualization, np.ones(visualization.shape[0:2], dtype='uint8') * 255))

        transmit_start = time.time()
        socketio.emit('size', {'w': w, 'h': h})
        socketio.emit('frame', {'data': visualization.flatten().tobytes()})
        log.info('Transmit frame took %f sec', time.time() - start_time)

        # with open('/tmp/pood.classification.png', 'wb') as fp:
        #     Image.fromarray(visualization, mode="RGB").save(fp)

    if not is_poop and np.random.rand() < 0.01:
        ds.store(0).tile(img, tiles=10, size=(16, 16))

    last_frame_time = time.time()
    # except:
    #     pass

    # send result back
    sent = sock.sendall(struct.pack('I', int(not is_poop)))

    log.info('Classification request took %f sec', time.time() - start_time)


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
                #conn.close()


def training_thread():
    global frames_received, classifier, force_training

    while True:
        now = time.time()
        dt = now - last_frame_time

        if (2 < dt < 60 and frames_received >= 100) or force_training:
            frames_received = 0
            force_training = False

            classifier.train(ds, epochs=1)
            classifier.store()

            os.system('rm /var/pood/err/*')

            # create links to incorrectly classified examples
            fetch = ds.fetch(0, 1).all()

            paths = fetch.minibatch_next_paths(batch_size=1000)
            sub_ts_x, sub_ts_y = fetch.minibatch(size=1000, classes=2)

            h = classifier.sess.run(classifier.model['hypothesis'], feed_dict={classifier.X: sub_ts_x, classifier.Y: sub_ts_y})

            for row in h:
                i = row.argmax()
                row *= 0
                row[i] = 1

            for y, h, path in zip(sub_ts_y, h, paths):
                if np.linalg.norm(y - h) > 0.001:
                    parts = path.split('/')
                    last = parts[len(parts) - 1]
                    os.symlink(path, '/var/pood/err/{}'.format(last))

            log.info("Training and testing complete")

        time.sleep(10)


@socketio.on('connect')
def dash_connection():
    log.info('Dashboard connected')


@app.route('/force-train')
def force_train():
    global force_training
    force_training = True
    return redirect('/')

@app.route('/collect-negatives')
def collect_negatives():
    global collecting_negs
    collecting_negs = True
    return redirect('/')

@app.route('/unknown/next')
def unknown_next():
    paths = DataStore('/tmp/pood/ds').fetch(1).all().paths()
    if len(paths) > 0:
        os.unlink(paths[0])
    return redirect('/')


@app.route('/unknown/negative')
def unknown_negative():
    global ds
    _ds = DataStore('/tmp/pood/ds')
    paths = _ds.fetch(1).all().paths()
    if len(paths) > 0:
        path = paths[0]
        ds.store(0).tile(Image.open(open(path, mode='rb')), 100, size=(16, 16))
        os.unlink(path)
    return redirect('/')


@app.route('/unknown')
def unknown():
    paths = DataStore('/tmp/pood/ds').fetch(1).all().paths()

    if len(paths) == 0:
        # return 404
        return 'No images found', 404

    resp =  send_file(paths[0])
    resp.headers['Cache-Control'] = 'no-cache, must-revalidate'
    return resp


@app.route('/')
def index():
    return app.send_static_file(filename='index.html')


if __name__ == '__main__':
    import threading
    HOST, PORT = '', 1337

    if has_cli_arg('collect') and has_cli_arg('negatives'):
        log.info('Collecting only negative examples')
        collecting_negs = True
    try:
        classifier.load()
    except FileNotFoundError:
        log.error('Classifier parameters for model "%s" not found, starting fresh.', classifier.name)

    threading.Thread(target=request_classifier_thread).start()
    threading.Thread(target=training_thread).start()

    if has_cli_arg('train'):
        last_frame_time = time.time()

    socketio.run(app, host='0.0.0.0', port=8080)





