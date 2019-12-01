import tensorflow as tf
import math
from nn_base import ConvLayer
from nn_base import Layer


def setup_model(w, h, x):
    p = {
        'c0': ConvLayer(weights=tf.Variable(tf.truncated_normal([5, 5, 3, 16], stddev=0.01)),
                        biases=tf.Variable(tf.constant(0.1, shape=[16]))),
        'c1': ConvLayer(weights=tf.Variable(tf.truncated_normal([7, 7, 16, 32], stddev=0.01)),
                        biases=tf.Variable(tf.constant(0.1, shape=[32]))),
    }

    out_w, out_h, out_d = w, h, 3
    for name, layer in p:
        out_w = (out_w - math.floor(int(layer.k_width) // 2)) // layer.s_x
        out_h = (out_h - math.floor(int(layer.k_height) // 2)) // layer.s_y

    final_size = out_w * out_h * out_d

    p['fc0'] = Layer(weights=tf.Variable(tf.truncated_normal([final_size, 2])),
                     biases=tf.Variable(tf.constant(0.1, shape=[2])))

    x = tf.reshape(x, shape=[-1, w, h, 3])

    z0 = tf.nn.conv2d(x, p['c0'].w, p['c0'].stride, p['c0'].pad) + p['c0'].b
    a0 = tf.nn.relu(z0)
    # a0 = tf.nn.max_pool(a0, ksize=[1, 2, 2, 1], strides=[1, 2, 2, 1], padding='VALID')
    # 7x7

    z1 = tf.nn.conv2d(a0, p['c1'].w, p['c1'].stride, p['c1'].pad) + p['c1'].b
    a1 = tf.nn.relu(z1)
    # a1 = tf.nn.max_pool(a1, ksize=[1, 2, 2, 1], strides=[1, 2, 2, 1], padding='VALID')

    z2 = tf.nn.conv2d(a1, p['c2'].w, p['c2'].stride, p['c2'].pad) + p['c2'].b
    a2 = tf.nn.relu(z2)
    a2 = tf.reshape(a2, shape=[-1, final_size])

    z3 = tf.matmul(a2, p['fc0'].w) + p['fc0'].b

    h = z3

    return p, h