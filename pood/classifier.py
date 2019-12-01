import tensorflow as tf
import math
from datastore import DataStore
import cnn_5_7_fc as architecture
from nn_helpers import serialize_matrix, deserialize_matrix, print_stats


class Classifier:
    def __init__(self, w, h, d):
        self.ds = DataStore('/var/pood/ds')
        self.X = tf.placeholder(tf.float32, [None, w, h, d], name="X")
        self.Y = tf.placeholder(tf.float32, [None, 2], name="Y")

        p, h = architecture.setup_model(w, h, self.X)

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

    def train(self):
        import random
        last_accuracy = 0
        minibatch_size = 100
        epochs = (len(full_set) // minibatch_size) * 20

        for e in range(0, epochs):
            # sub_ts_x, sub_ts_y = minibatch(full_set, random.randint(0, len(full_set) // 100), size=100)
            sub_ts_x, sub_ts_y = minibatch(full_set, e % (len(full_set) // minibatch_size), size=100)

            self.sess.run(self.model['train_step'], feed_dict={x: sub_ts_x, y: sub_ts_y})
            if e % 100 == 0:
                train_accuracy = self.sess.run(self.model['accuracy'], feed_dict={x: sub_ts_x, y: sub_ts_y})
                print_stats(
                    {
                        'accuracy': last_accuracy
                    }, {
                        'accuracy': train_accuracy,
                        'epoch': e,
                        'epoch_total': epochs
                    })
                last_accuracy = train_accuracy

            if not IS_TRAINING:
                break

        # Save the learned parameters
        for key in p:
            file_name = key.replace('_', '.')

            with open(MODEL_STORAGE_PATH + file_name, mode='wb') as fp:
                serialize_matrix(sess.run(p[key]), fp)