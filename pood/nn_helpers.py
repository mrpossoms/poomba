import numpy as np


class Layer:
    def __init__(self, weights, biases):
        self.w = weights
        self.b = biases

    def serialize(self, fp, sess):
        serialize_matrix(sess.run(self.w), fp)
        serialize_matrix(sess.run(self.b), fp)

    def deserialize(self, fp, sess):
        w, b = deserialize_matrices(fp)
        sess.run(self.w.assign(w))
        sess.run(self.b.assign(b))


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


def serialize_matrix(m, fp):
    """
    Writes a numpy array into fp in the simple format that
    libnn's nn_mat_load() function understands
    :param m: numpy matrix
    :param fp: file stream
    :return: void
    """
    import struct

    # write the header
    fp.write(struct.pack('b', len(m.shape)))
    for d in m.shape:
        fp.write(struct.pack('i', d))

    # followed by each element
    for e in m.flatten():
        fp.write(struct.pack('f', e))


def deserialize_matrices(fp):
    """
    Reads a numpy array from fp in the simple format that
    libnn's nn_mat_load() function understands
    :param fp: file stream
    :return: numpy matrix
    """
    import struct

    matrices = []

    while True:
        try:
            # read header
            hdr_dims_size = struct.calcsize('b')
            dims = struct.unpack_from('b', fp.read(hdr_dims_size))

            shape = []
            dim_size = struct.calcsize('i')
            for _ in range(dims[0]):
                shape += [struct.unpack_from('i', fp.read(dim_size))[0]]

            # followed by each element
            elements = []
            el_size = struct.calcsize('f')
            for _ in range(np.prod(shape)):
                elements += [struct.unpack_from('f', fp.read(el_size))[0]]

            matrices += [(np.array(elements, dtype=np.float32).reshape(shape))]
        except struct.error:
            break

    return matrices


def print_stats(t_1, t):
    width = 20
    display_bar = [' '] * width

    acc_t_1, acc_t = t_1['accuracy'], t['accuracy']
    epoch, total = t['epoch'], t['epoch_total']
    acc_delta = acc_t - acc_t_1

    slope_i = int((width - 1) * acc_t)

    if acc_delta > 0.01:
        display_bar[slope_i] = '\\'
    elif acc_delta < -0.01:
        display_bar[slope_i] = '/'
    else:
        display_bar[slope_i] = '|'

    line = '%03d%% |' % (acc_t * 100) + ''.join(display_bar) + '| ep: %d/%d' % (epoch, total)
    print(line)

if __name__ == '__main__':
    t = np.random.random((200,200,2))

    with open('/tmp/t', mode='wb') as fp:
        serialize_matrix(t, fp)

    with open('/tmp/t', mode='rb') as fp:
        t1 = deserialize_matrix(fp)
        assert(abs((t - t1).max()) < 0.0001)

    print('ALL PASS')