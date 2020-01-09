import tensorflow as tf
import numpy as np
import math
from nn_helpers import ConvLayer
from nn_helpers import Layer


def name():
    return 'cnn_12_5_5_f1024_fc'

def setup_model(w, h, x):
    p = {
        'c0': ConvLayer(weights=tf.Variable(tf.truncated_normal([12, 12, 3, 32], stddev=0.01)),
                        biases=tf.Variable(tf.constant(0.1, shape=[32]))),
        'c1': ConvLayer(weights=tf.Variable(tf.truncated_normal([5, 5, 32, 32], stddev=0.01)),
                        biases=tf.Variable(tf.constant(0.1, shape=[32]))),
        'c2': ConvLayer(weights=tf.Variable(tf.truncated_normal([5, 5, 32, 32], stddev=0.01)),
                        biases=tf.Variable(tf.constant(0.1, shape=[32]))),
    }

    x = tf.reshape(x, shape=[-1, w, h, 3])

    # 12x12
    z0 = tf.nn.conv2d(x, p['c0'].w, p['c0'].stride, p['c0'].pad) + p['c0'].b
    a0 = tf.nn.relu(z0)
    a0 = tf.nn.max_pool(a0, ksize=[1, 2, 2, 1], strides=[1, 2, 2, 1], padding='VALID')

    # 5x5
    z1 = tf.nn.conv2d(a0, p['c1'].w, p['c1'].stride, p['c1'].pad) + p['c1'].b
    a1 = tf.nn.relu(z1)
    a1 = tf.nn.max_pool(a1, ksize=[1, 2, 2, 1], strides=[1, 2, 2, 1], padding='VALID')
    # a1 = tf.nn.max_pool(a1, ksize=[1, 2, 2, 1], strides=[1, 2, 2, 1], padding='VALID')

    # 5x5
    z2 = tf.nn.conv2d(a1, p['c2'].w, p['c2'].stride, p['c2'].pad) + p['c2'].b
    a2 = tf.nn.relu(z2)
    # a2 = tf.nn.max_pool(a2, ksize=[1, 2, 2, 1], strides=[1, 2, 2, 1], padding='VALID')
    final_size = int(np.prod(a2.shape[1:]))
    a2 = tf.reshape(a2, shape=[-1, final_size])

    p['fc0'] = Layer(weights=tf.Variable(tf.truncated_normal([final_size, 1024], stddev=0.01)),
                     biases=tf.Variable(tf.constant(0.1, shape=[1024])))

    p['fc1'] = Layer(weights=tf.Variable(tf.truncated_normal([1024, 2], stddev=0.01)),
                     biases=tf.Variable(tf.constant(0.1, shape=[2])))

    z3 = tf.matmul(a2, p['fc0'].w) + p['fc0'].b
    a3 = tf.nn.softmax(z3)

    z4 = tf.matmul(a3, p['fc1'].w) + p['fc1'].b
    h = tf.nn.softmax(z4)

    return p, h
