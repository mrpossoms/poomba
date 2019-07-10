import tensorflow as tf
import math


class Layer:
    def __init__(self, weights, biases):
        self.w = weights
        self.b = biases


class ConvLayer(Layer):
    def __init__(self, weights, biases, stride=[1, 1, 1, 1], padding='VALID'):
        super().__init__(weights, biases)
        self.stride = stride
        self.pad = padding

    @property
    def k_width(self):
        return self.w.shape[0]

    @property
    def k_height(self):
        return self.w.shape[1]

    @property
    def s_x(self):
        return self.stride[0]

    @property
    def s_y(self):
        return self.stride[1]


def setup_model(w, h, x):
    p = {
        'c0': ConvLayer(weights=tf.Variable(tf.truncated_normal([5, 5, 3, 16], stddev=0.01)),
                        biases=tf.Variable(tf.constant(0.1, shape=[16]))),
        'c1': ConvLayer(weights=tf.Variable(tf.truncated_normal([7, 7, 16, 32], stddev=0.01)),
                        biases=tf.Variable(tf.constant(0.1, shape=[32]))),
        'c2': ConvLayer(weights=tf.Variable(tf.truncated_normal([7, 7, 32, 64], stddev=0.01)),
                        biases=tf.Variable(tf.constant(0.1, shape=[64]))),
        'c3': ConvLayer(weights=tf.Variable(tf.truncated_normal([7, 7, 64, 128], stddev=0.01)),
                        biases=tf.Variable(tf.constant(0.1, shape=[128])))
    }

    out_w, out_h, out_d = w, h, 3
    for name in ['c0', 'c1', 'c2', 'c3']:
        l = p[name]
        out_w = (out_w - math.floor(int(l.k_width) // 2)) // l.s_x
        out_h = (out_h - math.floor(int(l.k_height) // 2)) // l.s_y

    final_size = out_w * out_h * out_d

    x = tf.reshape(x, shape=[-1, w, h, 3])

    z0 = tf.nn.conv2d(x, p['c0'].w, p['c0'].stride, p['c0'].pad) + p['c0'].b
    a0 = tf.nn.relu(z0)
    # a0 = tf.nn.max_pool(a0, ksize=[1, 2, 2, 1], strides=[1, 2, 2, 1], padding='VALID')
    # 7x7

    z1 = tf.nn.conv2d(a0, p['c1'].w, p['c1'].stride, p['c1'].pad) + p['c1'].b
    a1 = tf.nn.relu(z1)
    # a1 = tf.nn.max_pool(a1, ksize=[1, 2, 2, 1], strides=[1, 2, 2, 1], padding='VALID')

    z2 = tf.nn.conv2d(a1, p['c2'].w, p['c2'].stride, p['c2'].pad) + p['c2'].b

    h = z1

    return p, h


class Classifier:
    def __init__(self, w, h, d):
        self.X = tf.placeholder(tf.float32, [None, w, h, d], name="X")
        self.Y = tf.placeholder(tf.float32, [None, 2], name="Y")

        p, h = setup_model(w, h, self.X)