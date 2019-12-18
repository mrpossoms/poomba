import tensorflow as tf
import numpy as np
import math
from datastore import DataStore
import cnn_5_7_fc as architecture
from nn_helpers import serialize_matrix, deserialize_matrix, print_stats
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

    def classify(self, img_arr, stride=32):
        activation = np.array((img_arr[0] // stride, img_arr[1] // stride))

        w, h = self.X.shape[0], self.X.shape[1]
        for r in range(activation.shape[0]):
            for c in range(activation.shape[1]):
                r, c = r * stride, c * stride
                patch = img_arr[r:r+w, c:c+h]

                # classify patch above
                activation[r][c] = self.sess.run(self.model['hypothesis'], feed_dict={x: patch})

    def train(self, datastore, epochs=1):
        last_accuracy = 0
        minibatch_size = 100

        for e in range(0, epochs):
            sub_ts_x, sub_ts_y = datastore.fetch(0, 1).minibatch(size=10, classes=2)

            self.sess.run(self.model['train_step'], feed_dict={self.X: sub_ts_x, self.Y: sub_ts_y})
            if e % 100 == 0:
                train_accuracy = self.sess.run(self.model['accuracy'], feed_dict={self.X: sub_ts_x, self.Y: sub_ts_y})
                print_stats(
                    {
                        'accuracy': last_accuracy
                    }, {
                        'accuracy': train_accuracy,
                        'epoch': e,
                        'epoch_total': epochs
                    })
                last_accuracy = train_accuracy

        # Save the learned parameters
        for key in self.model['parameters']:
            file_name = key.replace('_', '.')

            with open('{}/{}'.format(self.model_path, file_name), mode='wb') as fp:
                self.model['parameters'][key].serialize(fp, self.sess)

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
