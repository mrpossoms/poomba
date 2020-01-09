import tensorflow as tf
import numpy as np
import math
import log
from datastore import DataStore
import cnn_5_7_fc as architecture
# import cnn_12_5_5_f1024_fc as architecture
from nn_helpers import print_stats
from pathlib import Path
from PIL import Image


class Classifier:
    def __init__(self, w, h, d, model_path="/etc/pood/model"):
        self.X = tf.placeholder(tf.float32, [None, h, w, d])
        self.Y = tf.placeholder(tf.float32, [None, 2])

        p, h = architecture.setup_model(w, h, self.X)
        self.model_path = '{}/{}'.format(model_path, architecture.name())

        cross_entropy = tf.nn.softmax_cross_entropy_with_logits_v2(labels=self.Y, logits=h)
        loss = tf.reduce_mean(cross_entropy)  # + tf.nn.l2_loss(p['fc1_w']) + tf.nn.l2_loss(p['fc0_w'])
        train_step = tf.train.AdamOptimizer().minimize(loss)

        correct_prediction = tf.equal(tf.argmax(h, 1), tf.argmax(self.Y, 1))
        accuracy = tf.reduce_mean(tf.cast(correct_prediction, tf.float32))

        self.model = {
            'parameters': p,
            'hypothesis': h,
            'train_step': train_step,
            'accuracy': accuracy,
        }

        self.sess = tf.Session()
        self.sess.run(tf.global_variables_initializer())

    @property
    def name(self):
        return architecture.name()

    def classify(self, img, stride=8):
        img_arr = np.array(img.getdata()).reshape(img.width, img.height, 3)
        img_arr = (img_arr - img_arr.min()) / (img_arr.max() - img_arr.min())
        img_arr = (img_arr - 0.5) * 2

        w, h = self.X.shape[1], self.X.shape[2]
        _w, _h = img.width - w, img.height - h
        activation = np.zeros((_w // stride, _h // stride))
        visual = np.zeros((_h // stride, _w // stride, 3))

        for r in range(activation.shape[1]):
            for c in range(activation.shape[0]):
                _r, _c = r * stride, c * stride
                patch = img_arr[_c:_c+w, _r:_r+h].reshape([1, w, h, 3])

                # classify patch above
                a = self.sess.run(self.model['hypothesis'], feed_dict={self.X: patch})[0]
                activation[c][r] = a.argmax()
                if activation[c][r] > 0:
                    visual[r][c] = np.array([255, 0, 0])
                else:
                    visual[r][c] = np.array([0, 255, 0])

        return activation, visual.astype('uint8')

    def train(self, datastore, epochs=1):
        last_accuracy = 0
        minibatch_size = 200

        for e in range(0, epochs):
            fetched = datastore.fetch(0, 1).all().shuffle()
            for _ in range(0, fetched.minibatch_count(batch_size=minibatch_size)):
                sub_ts_x, sub_ts_y = fetched.minibatch(size=minibatch_size, classes=2)

                self.sess.run(self.model['train_step'], feed_dict={self.X: sub_ts_x, self.Y: sub_ts_y})

                if _ % 10 == 0:
                    train_accuracy = self.sess.run(self.model['accuracy'], feed_dict={self.X: sub_ts_x, self.Y: sub_ts_y})
                    print_stats(
                        {
                            'accuracy': last_accuracy
                        }, {
                            'accuracy': train_accuracy,
                            'epoch': _,
                            'epoch_total': fetched.minibatch_count(batch_size=minibatch_size)
                        })
                    last_accuracy = train_accuracy

    def store(self):
        def mkdir_p(path):
            import os
            import errno
            try:
                os.makedirs(path)
            except OSError as exc:  # Python >2.5
                if exc.errno == errno.EEXIST and os.path.isdir(path):
                    pass
                else:
                    raise
	    # make sure this directory exists
        mkdir_p(self.model_path)

        # Save the learned parameters
        for key in self.model['parameters']:
            file_name = key.replace('_', '.')
            log.info('storing model parameter %s', key)

            with open('{}/{}'.format(self.model_path, file_name), mode='wb') as fp:
                self.model['parameters'][key].serialize(fp, self.sess)

    def load(self):
        # Save the learned parameters
        for key in self.model['parameters']:
            file_name = key.replace('_', '.')
            log.info('loading model parameter %s', key)

            with open('{}/{}'.format(self.model_path, file_name), mode='rb') as fp:
                self.model['parameters'][key].deserialize(fp, self.sess)


if __name__ == '__main__':
    def rm_tree(pth):
        pth = Path(pth)
        for child in pth.glob('*'):
            if child.is_file():
                child.unlink()
            else:
                rm_tree(child)
        pth.rmdir()

    try:
        rm_tree(Path('/tmp/classifier/ds'))
    except:
        pass
    ds = DataStore('/tmp/classifier/ds')

    # create some examples
    for _ in range(10):
        red_arr = (np.random.random((480, 640, 3)) * [1, 0.1, 0.1] * 255).astype(np.uint8)
        red_img = Image.fromarray(red_arr)
        ds.store(0).tile(red_img, tiles=10)

        blue_arr = (np.random.random((480, 640, 3)) * [0.1, 0.1, 1] * 255).astype(np.uint8)
        blue_img = Image.fromarray(blue_arr)
        ds.store(1).tile(blue_img, tiles=10)

    # train on examples
    c = Classifier(64, 64, 3)
    c.train(ds, epochs=1000)

    # verify classification
